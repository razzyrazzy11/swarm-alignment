"""Isolated unit tests for experiments/hf_stateful.py.

Standard library only (unittest + unittest.mock). No network, no credentials,
no repo or runs/ writes: ROOT/FREEZE and every I/O collaborator are patched
into a temp directory, and request_json is fully mocked.
"""
import json
import shutil
import tempfile
import threading
import unittest
from contextlib import ExitStack
from decimal import Decimal
from pathlib import Path
from unittest import mock

from experiments import hf_stateful

MODEL = "org/hf-model"
PROVIDER_ROW = {"provider": "prov-a", "status": "live", "pricing": {"input": 2, "output": 3}}
CATALOG_DATA = {"data": [{"id": MODEL, "providers": [PROVIDER_ROW]}]}
CATALOG_CONFIG = {"model": MODEL + ":prov-a", "catalog_model": MODEL, "provider": "prov-a",
                  "input_usd_per_million": 2, "output_usd_per_million": 3}
STOP_RESPONSE = {"choices": [{"message": {"content": "answer"}, "finish_reason": "stop"}],
                 "model": MODEL}
# Default harness config: (input_byte_cap*2 + max_output_tokens*3)/1e6
RESERVE = Decimal("0.00203")


def make_config(**over):
    cfg = dict(study_id="stateful-hf-v1", model=MODEL + ":prov-a", provider="prov-a", catalog_model=MODEL,
               allowed_returned_models=[MODEL], input_usd_per_million=2,
               output_usd_per_million=3, input_byte_cap=1000, max_output_tokens=10,
               nominal_usd_cap="100", concurrency=2, request_order_seed=1,
               source_indices_per_family=list(range(8)))
    cfg.update(over)
    return cfg


def task(tid):
    return {"task_id": tid, "packet": {"q": tid}, "compatible_labels": []}


class HfStatefulTest(unittest.TestCase):
    def harness(self, tasks, chat_results, config_over=None):
        """Patch hf_stateful into a temp ROOT with mocked transport and journal."""
        stack = ExitStack()
        self.addCleanup(stack.close)
        tmp = Path(tempfile.mkdtemp(prefix="hf-stateful-test-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        freeze_path = tmp / "freeze.json"
        freeze_path.write_text(json.dumps({"source_sha256": {}, "config": {},
                                           "core_freeze_sha256": "core"}), encoding="utf-8")
        freeze_data = {"source_sha256": {}, "config": {}, "core_freeze_sha256": "core",
                       "base_commit": "base"}
        cfg = make_config(**(config_over or {}))
        journal = []
        state = {"chat_calls": 0}
        lock = threading.Lock()

        def dispatcher(url, key, *args, **kwargs):
            with lock:
                if url.endswith("/models"):
                    return {"http_status": 200}, CATALOG_DATA
                index = state["chat_calls"]
                state["chat_calls"] += 1
            result = chat_results[index]
            if isinstance(result, Exception):
                raise result
            return {"http_status": 200}, result

        replacements = (("ROOT", tmp), ("FREEZE", freeze_path), ("config", lambda: cfg),
                        ("verify_freeze", lambda: freeze_data),
                        ("credentials", lambda: {"HF_TOKEN": "test-key"}),
                        ("PROMPT", "P"), ("prepare", lambda: ([{"episode": "e"}], tasks)),
                        ("scrub", lambda row, secrets: row),
                        ("score_stateful", lambda normalized, labels: dict(
                            status="VALID", grounded_correct=False, supported_definite=False,
                            unsupported_executor=False, unsupported_none=False,
                            strict_schema_valid=False)),
                        ("durable", lambda handle, obj: journal.append(obj)))
        for name, replacement in replacements:
            stack.enter_context(mock.patch.object(hf_stateful, name, replacement))
        chat_mock = stack.enter_context(mock.patch.object(hf_stateful, "request_json",
                                                          side_effect=dispatcher))
        return tmp, journal, chat_mock, state

    def test_normalize_valid_stop_response(self):
        result = hf_stateful.normalize(
            {"choices": [{"message": {"content": "answer"}, "finish_reason": "stop"}]})
        self.assertEqual(result, {"status": "completed", "output_text": "answer"})

    def test_normalize_non_dict_payload_is_failed_empty(self):
        for bad in (None, "text", 42, []):
            self.assertEqual(hf_stateful.normalize(bad),
                             {"status": "failed", "output_text": ""})

    def test_normalize_multiple_choices_is_failed(self):
        result = hf_stateful.normalize(
            {"choices": [{"message": {"content": "a"}, "finish_reason": "stop"},
                         {"message": {"content": "b"}, "finish_reason": "stop"}]})
        self.assertEqual(result, {"status": "failed", "output_text": ""})

    def test_normalize_missing_or_malformed_choices_is_failed(self):
        for bad in ({}, {"choices": []}, {"choices": "no"}, {"choices": [None]}):
            self.assertEqual(hf_stateful.normalize(bad),
                             {"status": "failed", "output_text": ""})

    def test_normalize_truncated_finish_reason_is_incomplete(self):
        result = hf_stateful.normalize(
            {"choices": [{"message": {"content": "partial"}, "finish_reason": "length"}]})
        self.assertEqual(result, {"status": "incomplete", "output_text": "partial"})

    def test_normalize_non_string_content_becomes_empty_text(self):
        result = hf_stateful.normalize(
            {"choices": [{"message": {"content": None}, "finish_reason": "stop"}]})
        self.assertEqual(result, {"status": "failed", "output_text": ""})

    def test_selected_catalog_returns_pinned_live_provider(self):
        self.assertEqual(hf_stateful.selected_catalog(CATALOG_DATA, CATALOG_CONFIG),
                         PROVIDER_ROW)

    def test_selected_catalog_rejects_live_price_drift(self):
        drifted = {"data": [{"id": MODEL, "providers":
                   [dict(PROVIDER_ROW, pricing={"input": 2.5, "output": 3})]}]}
        with self.assertRaises(ValueError) as ctx:
            hf_stateful.selected_catalog(drifted, CATALOG_CONFIG)
        self.assertIn("pricing", str(ctx.exception))

    def test_selected_catalog_rejects_non_live_provider(self):
        sleeping = {"data": [{"id": MODEL, "providers": [dict(PROVIDER_ROW, status="sleep")]}]}
        with self.assertRaises(ValueError) as ctx:
            hf_stateful.selected_catalog(sleeping, CATALOG_CONFIG)
        self.assertIn("unavailable", str(ctx.exception))

    def test_selected_catalog_rejects_missing_provider(self):
        with self.assertRaises(ValueError):
            hf_stateful.selected_catalog({"data": [{"id": MODEL, "providers": []}]},
                                         CATALOG_CONFIG)

    def test_selected_catalog_rejects_ambiguous_duplicate_providers(self):
        duplicated = {"data": [{"id": MODEL, "providers": [PROVIDER_ROW, dict(PROVIDER_ROW)]}]}
        with self.assertRaises(ValueError):
            hf_stateful.selected_catalog(duplicated, CATALOG_CONFIG)

    def test_selected_catalog_rejects_empty_or_absent_catalog(self):
        for data in (None, {}, {"data": []}):
            with self.assertRaises(ValueError):
                hf_stateful.selected_catalog(data, CATALOG_CONFIG)

    def test_prepare_builds_family_seeds_and_flattens_tasks(self):
        cfg = make_config()
        families = ["sequential", "deferred", "approval_join"]
        core = {"stages": {"main": {"families": families, "seed_start": 7, "episodes_per_family": 64}}}
        with mock.patch.object(hf_stateful, "config", lambda: cfg), \
             mock.patch.object(hf_stateful, "core_config", lambda: core), \
             mock.patch.object(hf_stateful, "FAMILIES", families), \
             mock.patch.object(hf_stateful, "episode",
                               side_effect=lambda seed, family, j:
                               {"seed": seed, "family": family, "index": j}) as episode, \
             mock.patch.object(hf_stateful, "tasks_for",
                               side_effect=lambda e: [{"task_id": "t%d-%d" % (e["seed"], k)} for k in range(10)]):
            sources, tasks = hf_stateful.prepare()
        expected_seeds = [7 + 10000 * f + j for f in range(3) for j in range(8)]
        self.assertEqual([s["seed"] for s in sources], expected_seeds)
        self.assertEqual([s["family"] for s in sources], [f for f in families for _ in range(8)])
        self.assertEqual([s["index"] for s in sources], list(range(8)) * 3)
        self.assertEqual([t["task_id"] for t in tasks], ["t%d-%d" % (s, k) for s in expected_seeds for k in range(10)])
        self.assertEqual(episode.call_count, 24)
        self.assertEqual(len(tasks), 240)

    def test_run_unknown_usage_bills_reserve_and_halts(self):
        tmp, journal, chat_mock, state = self.harness([task("t1")], [dict(STOP_RESPONSE)])
        summary = hf_stateful.run()
        self.assertFalse(summary["complete"])
        self.assertEqual(summary["planned_calls"], 1)
        self.assertEqual(summary["attempted_calls"], 1)
        self.assertEqual(summary["retained_responses"], 1)
        self.assertEqual(Decimal(summary["estimated_usd"]), RESERVE)
        attempts = [row for row in journal if "reserved_usd" in row]
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0]["reserved_usd"], str(RESERVE))
        responses = [row for row in journal if "task" in row]
        self.assertEqual(len(responses), 1)
        self.assertFalse(responses[0]["known_usage"])
        self.assertEqual(responses[0]["normalized"]["status"], "completed")
        self.assertTrue((tmp / "runs/stateful-hf-v1/summary.json").exists())

    def test_run_request_error_drains_batch_and_preserves_rows(self):
        tmp, journal, chat_mock, state = self.harness(
            [task("t1"), task("t2")], [RuntimeError("boom"), dict(STOP_RESPONSE)])
        summary = hf_stateful.run()
        self.assertFalse(summary["complete"])
        self.assertEqual(summary["planned_calls"], 2)
        self.assertEqual(summary["attempted_calls"], 2)
        self.assertEqual(summary["retained_responses"], 2)
        self.assertEqual(Decimal(summary["estimated_usd"]), 2 * RESERVE)
        attempts = [row for row in journal if "reserved_usd" in row]
        self.assertEqual({row["task_id"] for row in attempts}, {"t1", "t2"})
        responses = [row for row in journal if "task" in row]
        self.assertEqual(sorted(row["normalized"]["status"] for row in responses),
                         ["completed", "failed"])

    def test_run_halts_before_dispatch_when_budget_cap_below_reserve(self):
        tmp, journal, chat_mock, state = self.harness(
            [task("t1"), task("t2")], [], config_over={"nominal_usd_cap": "0.001"})
        summary = hf_stateful.run()
        self.assertFalse(summary["complete"])
        self.assertEqual(summary["attempted_calls"], 0)
        self.assertEqual(summary["estimated_usd"], "0")
        self.assertEqual(state["chat_calls"], 0)
        self.assertEqual([row for row in journal if "reserved_usd" in row], [])

    def test_run_refuses_existing_output_directory(self):
        tmp, journal, chat_mock, state = self.harness([], [])
        (tmp / "runs/stateful-hf-v1").mkdir(parents=True)
        with self.assertRaises(ValueError) as ctx:
            hf_stateful.run()
        self.assertIn("output exists", str(ctx.exception))
        self.assertEqual(state["chat_calls"], 0)


if __name__ == "__main__":
    unittest.main()
