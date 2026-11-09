"""Synthetic-only regression tests: no value is copied from the private tree."""
import dataclasses
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
import zipfile

spec = importlib.util.spec_from_file_location("private_preparation_privacy_policy", Path(__file__).with_name("privacy_policy.py"))
policy = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = policy
spec.loader.exec_module(policy)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def rule_for(raw, indices=(0,), line=1, path="research/example.md"):
    text_line = raw.decode().splitlines(keepends=True)[line - 1]
    count = len(list(policy._EXPRESSION.finditer(text_line)))
    return policy.FileRule(path, sha(raw), tuple(policy.SpanRule(
        line=line, line_sha256=sha(text_line.encode()), expression_index=i,
        expected_expression_count=count, category="provider_account_credit",
        semantic_role="initial_credit_observed",
    ) for i in indices))


class PrivacyPolicyTests(unittest.TestCase):
    def test_only_reviewed_account_span_changes(self):
        raw = ("Observed initial balance: 1234.567 credits; 1 credit=$1; "
               "planned cap $77; reported experiment cost 0.01234 credits.\r\n"
               "Résumé and C:\\Users\\Example\\runtime\\python.exe stay unchanged.\r\n").encode()
        rule = rule_for(raw)
        sanitized, manifest = policy.redact_document(raw, rule)
        self.assertEqual(sanitized, raw.replace(b"1234.567", policy.MARKER.encode(), 1))
        self.assertEqual(manifest["sanitized_sha256"], sha(sanitized))
        self.assertEqual(set(manifest), {"path", "sanitized_sha256", "redactions"})
        self.assertNotIn("original_sha256", manifest)
        self.assertNotIn("line_sha256", json.dumps(manifest))
        self.assertNotIn("1234.567", json.dumps(manifest))
        self.assertEqual(set(manifest["redactions"][0]), {"line", "category", "semantic_role"})

    def test_multiple_spans_preserve_all_intervening_bytes(self):
        raw = b"Available provider A $987.654, provider B $876.543; unit $1.\n"
        rule = rule_for(raw, (0, 1))
        sanitized, _ = policy.redact_document(raw, rule)
        expected = raw.replace(b"987.654", policy.MARKER.encode()).replace(b"876.543", policy.MARKER.encode())
        self.assertEqual(sanitized, expected)
        self.assertTrue(sanitized.endswith(b"unit $1.\n"))

    def test_hash_line_index_count_and_role_drift_fail_closed(self):
        raw = b"Initial balance 1234.567 credits; cap $77.\n"
        rule = rule_for(raw)
        bad_span = dataclasses.replace(rule.spans[0], expression_index=99)
        variants = [
            dataclasses.replace(rule, source_sha256="0" * 64),
            dataclasses.replace(rule, spans=(dataclasses.replace(rule.spans[0], line_sha256="0" * 64),)),
            dataclasses.replace(rule, spans=(bad_span,)),
            dataclasses.replace(rule, spans=(dataclasses.replace(rule.spans[0], expected_expression_count=99),)),
            dataclasses.replace(rule, spans=(dataclasses.replace(rule.spans[0], semantic_role="unreviewed"),)),
            dataclasses.replace(rule, path="../outside.md"),
        ]
        for variant in variants:
            with self.subTest(variant=variant):
                with self.assertRaises(policy.PrivacyPolicyError):
                    policy.redact_document(raw, variant)

    def test_duplicate_span_fails_closed(self):
        raw = b"Initial balance 1234.567 credits.\n"
        rule = rule_for(raw, (0, 0))
        with self.assertRaises(policy.PrivacyPolicyError):
            policy.redact_document(raw, rule)

    def test_plan_does_not_produce_redacted_content(self):
        raw = b"Initial balance 1234.567 credits.\n"
        plan = policy.plan_document(raw, rule_for(raw))
        self.assertNotIn("sanitized_sha256", plan)
        self.assertNotIn("1234.567", json.dumps(plan))
        self.assertNotIn(policy.MARKER, json.dumps(plan))

    def test_private_plan_is_explicit_and_inventory_bound(self):
        raw = b"Initial balance 1234.567 credits.\n"
        rule = rule_for(raw)
        plan = {"source_commit": "a" * 40, "file_count": 1, "span_count": 1,
                "rules": [dataclasses.asdict(rule)]}
        self.assertEqual(policy.load_private_rule_metadata(plan), (rule,))
        for bad in ({}, {**plan, "file_count": 2}, {**plan, "span_count": 2},
                    {**plan, "source_commit": "not-a-commit"}):
            with self.assertRaises(policy.PrivacyPolicyError):
                policy.load_private_rule_metadata(bad)

    def test_known_private_literals_fail_without_echoing_values(self):
        for category in ("credential", "private_header_value", "native_response_id", "private_answer"):
            secret = ("synthetic-" + category + "-canary").encode()
            with self.assertRaises(policy.PrivacyPolicyError) as caught:
                policy.audit_forbidden_values("research/example.md", b"prefix " + secret, {category: [secret]})
            self.assertNotIn(secret.decode(), str(caught.exception))
        with self.assertRaises(policy.PrivacyPolicyError):
            policy.audit_forbidden_values("example.md", b"safe", {"unreviewed": [b"canary"]})

    def test_sensitive_fields_and_synthetic_boolean_are_distinct(self):
        for key in ("headers", "native_response_id", "raw_answer", "api_key"):
            with self.assertRaises(policy.PrivacyPolicyError):
                policy.audit_forbidden_values("data/example.json", json.dumps({key: "synthetic-canary"}).encode(), {})
        policy.audit_forbidden_values("data/stateful_influence_cases.jsonl", b'{"packet":{"authorization":false}}\n', {})
        policy.audit_forbidden_values("data/stateful_influence_cases.jsonl", b'{"packet":{"authorization":true}}\n', {})
        with self.assertRaises(policy.PrivacyPolicyError):
            policy.audit_forbidden_values("data/stateful_influence_cases.jsonl", b'{"packet":{"authorization":"synthetic-canary"}}\n', {})
        for value in (False, 0):
            with self.assertRaises(policy.PrivacyPolicyError):
                policy.audit_forbidden_values("data/example.json", json.dumps({"raw_answer": value}).encode(), {})
        policy.audit_forbidden_values("module.py", b"SENSITIVE_FIELD_NAMES = ('headers', 'raw_answer')", {})

    def test_shapes_and_invalid_json_fail_closed(self):
        for value in (("hf_" + "A" * 30), ("resp_" + "B" * 30)):
            with self.assertRaises(policy.PrivacyPolicyError):
                policy.audit_forbidden_values("example.md", value.encode(), {})
        with self.assertRaises(policy.PrivacyPolicyError):
            policy.audit_forbidden_values("bad.json", b"{", {})

    def test_duplicate_keys_cannot_hide_private_fields(self):
        raw = b'{"nested":{"raw_answer":"synthetic-canary","raw_answer":null}}'
        for path in ("example.json", "example.jsonl"):
            with self.subTest(path=path):
                with self.assertRaises(policy.PrivacyPolicyError):
                    policy.audit_forbidden_values(path, raw, {})

    def test_nonfinite_and_overflow_numbers_fail_closed(self):
        for token in (b"NaN", b"Infinity", b"-Infinity", b"1e999"):
            for path in ("example.json", "example.jsonl"):
                with self.subTest(token=token, path=path):
                    with self.assertRaises(policy.PrivacyPolicyError):
                        policy.audit_forbidden_values(path, b'{"numeric":' + token + b'}', {})

    def test_strict_rule_metadata_types_paths_and_keys(self):
        raw = b"Initial balance 1234.567 credits.\n"
        rule = rule_for(raw)
        for variant in (
            dataclasses.replace(rule, path=""),
            dataclasses.replace(rule, path="research//example.md"),
            dataclasses.replace(rule, spans=(dataclasses.replace(rule.spans[0], expected_expression_count=True),)),
            dataclasses.replace(rule, spans=(dataclasses.replace(rule.spans[0], expression_index=-1),)),
        ):
            with self.assertRaises(policy.PrivacyPolicyError):
                policy.redact_document(raw, variant)
        row = dataclasses.asdict(rule)
        row["spans"][0]["extra"] = "synthetic-extra"
        with self.assertRaises(policy.PrivacyPolicyError):
            policy.rules_from_metadata([row])

    def test_decoded_and_nested_escaped_private_values_are_scanned(self):
        canary = b"synthetic-private-canary"
        escaped = "".join("\\u%04x" % byte for byte in canary)
        direct = ('{"payload":"' + escaped + '"}').encode()
        nested = json.dumps({"payload": direct.decode()}).encode()
        for raw in (direct, nested):
            for category in ("credential", "private_header_value", "native_response_id", "private_answer"):
                with self.subTest(category=category):
                    with self.assertRaises(policy.PrivacyPolicyError) as caught:
                        policy.audit_forbidden_values("example.json", raw, {category: iter([canary])})
                    self.assertNotIn(canary.decode(), str(caught.exception))
        shaped = "resp_" + "Q" * 30
        escaped_id = "".join("\\u%04x" % ord(char) for char in shaped)
        with self.assertRaises(policy.PrivacyPolicyError):
            policy.audit_forbidden_values("example.json", ('{"payload":"' + escaped_id + '"}').encode(), {})

    def test_hidden_provider_reasoning_and_public_controls_are_distinct(self):
        for key in ("reasoning_content", "thinking", "hidden_reasoning", "analysis"):
            raw = json.dumps({"provider": {key: "synthetic hidden content"}}).encode()
            with self.subTest(key=key):
                with self.assertRaises(policy.PrivacyPolicyError):
                    policy.audit_forbidden_values("example.json", raw, {})
        controls = {"request": {"thinking_control": "off", "effort": "low", "think": False,
                                "thinking": False, "reasoning": {"effort": "low", "enabled": True}}}
        policy.audit_forbidden_values("example.json", json.dumps(controls).encode(), {})
        policy.audit_forbidden_values("example.json", b'{"analysis":{"effect":0.25}}', {})

    def test_contextual_account_fields_not_scientific_costs(self):
        examples = (
            {"provider": {"balance_usd": 1234.567}},
            {"provider": {"available": 1234.567}},
            {"provider": {"available": "1234.567"}},
            {"credits": {"available": "1234.567 credits"}},
            {"credit_reconciliation": "Initial credit 1234.567; final credit 987.654."},
            {"credit_reconciliation": "Initial credit .75; final credit .5."},
        )
        for example in examples:
            with self.assertRaises(policy.PrivacyPolicyError):
                policy.audit_forbidden_values("example.json", json.dumps(example).encode(), {})
        safe = {"credit_reconciliation": "Final balance not captured after v1.",
                "known_provider_reported_cost": "0.01234", "cap_usd": 77,
                "estimated_usage": 0.01234, "unit_conversion": "1 credit=$1",
                "provider": {"available": True}}
        policy.audit_forbidden_values("example.json", json.dumps(safe).encode(), {})
        safe["credit_reconciliation"] = "Reported cost 0.01234 credits, not a reconciled account balance."
        policy.audit_forbidden_values("example.json", json.dumps(safe).encode(), {})

    def test_final_delivery_requires_exact_path_field_admission(self):
        path = "data/synthetic-study.jsonl"
        # This is visible final delivery, not a captured provider envelope.
        final = '{"analysis":"visible final explanation","balance_usd":77}'
        raw = json.dumps({"final_output": final, "score_flag": False}).encode() + b"\n"
        with self.assertRaises(policy.PrivacyPolicyError):
            policy.audit_forbidden_values(path, raw, {})
        approved = {path: {("final_output",)}}
        policy.audit_forbidden_values(path, raw, {}, approved_final_output_fields=approved)
        self.assertEqual(json.loads(raw)["final_output"], final)
        with self.assertRaises(policy.PrivacyPolicyError):
            policy.audit_forbidden_values("data/unregistered.jsonl", raw, {}, approved_final_output_fields=approved)
        bad_envelope = json.dumps({"final_output": final, "reasoning_content": "synthetic private reasoning"}).encode()
        with self.assertRaises(policy.PrivacyPolicyError):
            policy.audit_forbidden_values(path, bad_envelope, {}, approved_final_output_fields=approved)
        malformed_final = json.dumps({"final_output": '{"verdict":broken JSON'}).encode()
        policy.audit_forbidden_values(path, malformed_final, {}, approved_final_output_fields=approved)
        legacy = json.dumps({"response": {"output_text": final}}).encode()
        with self.assertRaises(policy.PrivacyPolicyError):
            policy.audit_forbidden_values(path, legacy, {})
        policy.audit_forbidden_values(path, legacy, {},
                                      approved_final_output_fields={path: {("response", "output_text")}})
        actual = json.dumps({"actual_output": '{"reasoning":"visible final",broken', "score_flag": False}).encode()
        with self.assertRaises(policy.PrivacyPolicyError):
            policy.audit_forbidden_values(path, actual, {})
        policy.audit_forbidden_values(path, actual, {}, approved_final_output_fields={path: {("actual_output",)}})
        self.assertIs(json.loads(actual)["score_flag"], False)
        with self.assertRaises(policy.PrivacyPolicyError):
            policy.audit_forbidden_values("data/unregistered.jsonl", actual, {}, approved_final_output_fields={path: {("actual_output",)}})
        for invalid in ({"final_output": {"verdict": "synthetic"}}, {"final_output": False}):
            with self.assertRaises(policy.PrivacyPolicyError):
                policy.audit_forbidden_values(path, json.dumps(invalid).encode(), {}, approved_final_output_fields=approved)

    def test_frozen_scientific_thinking_report_exact_path_and_schema(self):
        path = "data/synthetic-main/report.json"
        row = dict(estimate=0.25, lower=-0.25, upper=0.5, blocks=8, strata=2, draws=10,
                   seed=17, unit="assigned base block; all arms retained",
                   interval="stratified percentile bootstrap 95%")
        raw = json.dumps({"thinking_control": {"direct": row, "procedure": row}}).encode()
        allowed = {path: {("thinking_control",)}}
        policy.audit_forbidden_values(path, raw, {}, approved_scientific_report_fields=allowed)
        with self.assertRaises(policy.PrivacyPolicyError):
            policy.audit_forbidden_values("data/unregistered/report.json", raw, {}, approved_scientific_report_fields=allowed)
        bad_row = {**row, "blocks": True}
        with self.assertRaises(policy.PrivacyPolicyError):
            policy.audit_forbidden_values(path, json.dumps({"thinking_control": {"direct": bad_row, "procedure": row}}).encode(), {},
                                          approved_scientific_report_fields=allowed)

    def test_reasoning_envelopes_and_camelcase_private_headers(self):
        examples = (
            {"type": "reasoning", "content": [{"type": "reasoning_text", "text": "synthetic hidden content"}]},
            {"Type": "Reasoning", "Content": [{"Type": "ReasoningText", "text": "synthetic hidden content"}]},
            {"ResponseHeaders": {"Authorization": "synthetic header"}},
            {"provider": {"CurrentBalanceUSD": 1234.567}},
        )
        for example in examples:
            with self.assertRaises(policy.PrivacyPolicyError):
                policy.audit_forbidden_values("example.json", json.dumps(example).encode(), {})

    def test_visible_malformed_final_keys_preserved_but_escaped_secrets_blocked(self):
        path = "data/synthetic-study.jsonl"
        approved = {path: {("final_output",)}}
        final = '{"reasoning":"visible explanation","headers":["visible"],"api_key":"fabricated-key",broken'
        for _ in range(10):
            final = json.dumps(final)
        raw = json.dumps({"final_output": final, "score_flag": False}).encode()
        policy.audit_forbidden_values(path, raw, {}, approved_final_output_fields=approved)
        self.assertEqual(json.loads(raw)["final_output"], final)
        self.assertIs(json.loads(raw)["score_flag"], False)
        canary = b"synthetic-only-real-secret-canary"
        encoded = "".join("\\u%04x" % byte for byte in canary)
        bad_final = '{"api_key":"' + encoded + '",broken'
        for _ in range(10):
            bad_final = json.dumps(bad_final)
        bad_raw = json.dumps({"final_output": bad_final}).encode()
        with self.assertRaises(policy.PrivacyPolicyError) as caught:
            policy.audit_forbidden_values(path, bad_raw, {"credential": [canary]}, approved_final_output_fields=approved)
        self.assertNotIn(canary.decode(), str(caught.exception))

    def test_retired_commitments_have_distinct_case_insensitive_literal_rule(self):
        retired = ("aB" * 32).encode()
        escaped = "".join("\\u%04x" % byte for byte in retired.upper())
        for raw in (retired.upper(), ('{"value":"' + escaped + '"}').encode()):
            path = "example.json" if raw.startswith(b"{") else "example.md"
            with self.assertRaises(policy.PrivacyPolicyError) as caught:
                policy.audit_forbidden_values(path, raw, {"private_source_commitment": [retired]})
            self.assertNotIn(retired.decode(), str(caught.exception))
        credential = b"SyntheticCaseSensitiveCredential"
        policy.audit_forbidden_values("example.md", credential.lower(), {"credential": [credential]})
        with self.assertRaises(policy.PrivacyPolicyError):
            policy.audit_forbidden_values("example.md", b"safe", {"private_source_commitment": [b"not-a-digest"]})

    def test_actual_output_container_never_borrows_root_permission(self):
        path = "data/synthetic-study.jsonl"
        raw = json.dumps({"actual_output": '{"reasoning":"visible",broken', "score_flag": False}).encode()
        approved = {path: {("actual_output",)}}
        policy.audit_forbidden_values(path, raw, {}, approved_final_output_fields=approved)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(path, raw)
        with self.assertRaises(policy.PrivacyPolicyError):
            policy.audit_archive("publication.zip", buffer.getvalue(), {}, approved_final_output_fields=approved)


if __name__ == "__main__":
    unittest.main()
