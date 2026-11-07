"""Descriptive post-unblinding calibration breakdown of frozen public scores.

No hypothesis test, CI, model call, rescoring, or primary-analysis change. Only
structured metadata, truth supports and already-published score fields are used;
response text and native/provider artifacts are never inspected.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "analysis/calibration_breakdown.py"
INPUTS = ("research/factorial-report.json", "data/factorial_report_cases.jsonl",
          "data/factorial_report_manifest.json")
CONDITIONS = ("original_g26", "original_g31", "original_hf", "ds_off", "ds_low", "gemma_bridge")
PROCEDURES = ("direct", "procedure")
TYPES = ("closed_read", "permitted_write", "unauthorized_write", "revoked_write", "expired_write")
NEGATIVE = {"closed_read", "permitted_write"}
COUNTS = ("planned", "observed", "missing", "raw_correct_definite", "invalid", "abstain",
          "false_executor", "false_none", "strict_schema_valid", "strict_schema_invalid")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def combine(records):
    total = {key: sum(row[key] for row in records) for key in COUNTS}
    encodings = Counter()
    for row in records:
        encodings.update(row["encoding_counts"])
    total["encoding_counts"] = dict(sorted(encodings.items()))
    return total


def build():
    raw = {name: (ROOT / name).read_bytes() for name in INPUTS}
    report = json.loads(raw[INPUTS[0]])
    cases = [json.loads(line) for line in raw[INPUTS[1]].splitlines()]
    manifest = json.loads(raw[INPUTS[2]])
    for name in INPUTS[1:]:
        require(report["artifacts"][name] == sha(raw[name]), "Frozen report input hash mismatch: " + name)
    require(report["primary_complete"] is True and report["original_plan_complete"] is False,
            "Expected amended, primary-complete public report")
    registry = {row["id"]: row for row in manifest["conditions"]}
    require(set(registry) == set(CONDITIONS) and len(registry) == len(manifest["conditions"]),
            "Expected six distinct registered conditions")
    jobs = {row["id"]: row for row in manifest["jobs"]}
    observed = {row["id"]: row for row in cases}
    require(len(jobs) == len(manifest["jobs"]) and len(observed) == len(cases), "Duplicate public identity")
    require(set(observed) <= set(jobs), "Unplanned public response")
    for ident, job in jobs.items():
        require(job["state"] == ("TERMINAL" if ident in observed else "UNSTARTED"),
                "Manifest terminal/unstarted mismatch")
    packets = {(p["source_seed"], p["view"]): p for p in manifest["packets"]}
    require(len(packets) == len(manifest["packets"]), "Duplicate authentic packet")
    for row in cases:
        job = jobs[row["id"]]
        require(row["condition_id"] == job["condition_id"] and row["metadata"] == job["metadata"]
                and row["provider"] == job["provider"] and row["model"] == job["model"],
                "Observed case differs from planned condition/source")

    cells = []
    for condition in CONDITIONS:
        for procedure in PROCEDURES:
            for kind in TYPES:
                view = "calibration_" + kind
                planned = [j for j in jobs.values() if j["condition_id"] == condition
                           and j["metadata"]["procedure"] == procedure and j["metadata"]["view"] == view]
                require(len(planned) == 4 and len({j["metadata"]["source_seed"] for j in planned}) == 4,
                        "Each registered calibration type requires four distinct planned sources")
                expected_class = "negative_NONE" if kind in NEGATIVE else "positive_EXECUTOR"
                cell = dict(condition_id=condition, procedure=procedure, calibration_type=kind,
                            truth_class=expected_class, **{key: 0 for key in COUNTS}, encoding_counts={})
                cell["planned"] = len(planned)
                encoding = Counter()
                for job in planned:
                    meta = job["metadata"]
                    packet = packets[meta["source_seed"], meta["view"]]
                    truth = packet["compatible_labels"]
                    require(len(truth) == 1 and (truth == ["NONE"]) == (kind in NEGATIVE),
                            "Calibration singleton truth/class mismatch")
                    require(meta["packet_sha256"] == packet["packet_sha256"], "Packet commitment mismatch")
                    if job["id"] not in observed:
                        cell["missing"] += 1
                        continue  # Unstarted outcomes have no score and are never scored zero.
                    row = observed[job["id"]]
                    require(row["compatible_labels"] == truth, "Published calibration truth mismatch")
                    score = row["scored"]
                    require(score["status"] in ("NONE", "EXECUTOR", "ABSTAIN", "INVALID"), "Unknown verdict status")
                    for field in ("supported_definite", "grounded_correct", "unsupported_executor", "unsupported_none"):
                        require(type(score[field]) is int and score[field] in (0, 1), "Frozen score must be binary")
                    require(type(score["strict_schema_valid"]) is bool and type(score["encoding"]) is str,
                            "Frozen encoding metadata types")
                    cell["observed"] += 1
                    cell["raw_correct_definite"] += score["supported_definite"]
                    require(score["grounded_correct"] == score["supported_definite"], "Singleton score consistency")
                    cell["invalid"] += int(score["status"] == "INVALID")
                    cell["abstain"] += int(score["status"] == "ABSTAIN")
                    cell["false_executor"] += score["unsupported_executor"]
                    cell["false_none"] += score["unsupported_none"]
                    cell["strict_schema_valid"] += int(score["strict_schema_valid"])
                    cell["strict_schema_invalid"] += int(not score["strict_schema_valid"])
                    encoding[score["encoding"]] += 1
                cell["encoding_counts"] = dict(sorted(encoding.items()))
                require(cell["observed"] + cell["missing"] == 4, "Observed/missing denominator mismatch")
                require(sum(cell[k] for k in ("raw_correct_definite", "invalid", "abstain", "false_executor", "false_none"))
                        == cell["observed"], "Verdict categories fail to partition observed calibration")
                require(cell["strict_schema_valid"] + cell["strict_schema_invalid"] == cell["observed"]
                        == sum(encoding.values()), "Encoding counts do not partition observed responses")
                cells.append(cell)
    calibration_jobs = [j for j in jobs.values() if j["metadata"]["view"].startswith("calibration_")]
    require(len(calibration_jobs) == sum(c["planned"] for c in cells) == 240,
            "Calibration type inventory omits or adds planned jobs")
    summaries = []
    for condition in CONDITIONS:
        descriptor = registry[condition]
        frozen = (report["analysis"]["calibration"][descriptor["model"]] if descriptor["origin"] == "original"
                  else report["analysis"]["extensions"]["conditions"][condition]["calibration"])
        for procedure in PROCEDURES:
            selected = [c for c in cells if c["condition_id"] == condition and c["procedure"] == procedure]
            total = combine(selected)
            positive = combine([c for c in selected if c["truth_class"] == "positive_EXECUTOR"])
            negative = combine([c for c in selected if c["truth_class"] == "negative_NONE"])
            require(total["planned"] == 20 and positive["planned"] == 12 and negative["planned"] == 8,
                    "Preassigned calibration class denominator mismatch")
            mapping = {"observed": "calls", "raw_correct_definite": "supported_definite", "invalid": "invalid",
                       "abstain": "abstain", "false_executor": "unsupported_executor", "false_none": "unsupported_none",
                       "strict_schema_invalid": "strict_invalid"}
            for here, there in mapping.items():
                require(total[here] == frozen[procedure][there], "Frozen calibration aggregate mismatch: " + condition + "/" + procedure + "/" + here)
            summaries.append(dict(condition_id=condition, procedure=procedure, total=total,
                                  positive_executor=positive, negative_none=negative))
    return dict(schema_version=1, status="DESCRIPTIVE_POSTHOC_AFTER_UNBLINDING",
                scope="Preassigned scripted calibration types; observed frozen scores only. No hypothesis test, CI, new primary, rescoring, or generalization to main-sample incident detection.",
                missingness="UNSTARTED remains missing; observed INVALID contributes zero correct within observed denominators only.",
                score_contract="Frozen normalized/extracted verdict accuracy; strict schema and encoding counts are reported separately.",
                error_labels="false_executor is the frozen unsupported_executor count (including wrong executor attribution); false_none is unsupported_none. These are not main-sample sensitivity estimates.",
                source_sha256={SOURCE: sha((ROOT / SOURCE).read_bytes())},
                input_sha256={name: sha(raw[name]) for name in INPUTS},
                registered_conditions=[registry[c] for c in CONDITIONS], cells=cells, summaries=summaries)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path)
    mode.add_argument("--check", type=Path)
    args = parser.parse_args()
    text = canonical(build())
    if args.output is not None:
        require(args.output.resolve() not in {(ROOT / name).resolve() for name in (*INPUTS, SOURCE)},
                "Output must not overwrite public inputs or diagnostic source")
        args.output.write_text(text, encoding="utf-8", newline="\n")
        print("Wrote descriptive posthoc calibration diagnostic")
    else:
        require(args.check.read_bytes() == text.encode("utf-8"), "Posthoc diagnostic differs from source/input replay")
        print("Verified descriptive posthoc calibration diagnostic")


if __name__ == "__main__":
    main()
