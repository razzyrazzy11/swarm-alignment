# Offline release recovery: private diagnostics are not scientific verdict fields

This amendment is registered after collection ended and the first offline release
failed, before recovered scoring or public output. It introduces no inference,
retry, training, endpoint change, model change, or selection based on results.
All frozen collection, analysis, plotting, sensitivity and numerical sources stay
unchanged. This is an operational public-serialization correction, not a new
scientific preregistration.

## Failure and narrowly scoped correction

The original seven-stage postprocessor stopped in `hf_export` with zero completed
stages. The frozen raw HF union includes the connectivity collector's operational
`connection_fault`, optional `capture_failed`, and `diagnostics` transport fields.
A shallow eight-field row projection left those nested private diagnostics in
`transport`. The frozen public validator correctly rejected the extra fields.
The validator is retained unchanged.

The new `offline_release_recovery` adapter first invokes the unchanged
`hf_completion_v3.private_completed()`. That function verifies the immutable
9 + 1,732 + 157 disjoint union, native normalization, request bodies, identifiers,
error-receipt hashes, original checkpoint bytes, full unknown reservations,
final costs and all 1,898 terminal records. Only after that admission does the
adapter deep-copy the original eight scientific fields and request commitment.
Its public transport is exactly the original subset of `http_status`,
`latency_seconds`, and `error`; their values are unchanged. No record, failed
terminal, cost, label, response, usage counter, original public transport value or
body identity is dropped or replaced. Private diagnostic timestamps are excluded
from the public transport and remain unchanged in the immutable raw archive.

Recognized private transport extras are limited to `connection_fault`,
`capture_failed` and `diagnostics`. Diagnostic keys and types must match the frozen
connectivity source: safe exception class names, numeric OS errors, known stages,
UTC timestamps, bounded byte counts, SHA256 commitments and sanitized media/length
fields. Unknown fields, headers, response bodies, URLs or exception messages fail
closed. The private raw files are never rewritten, and all original batch hashes
remain in the existing HF report.

## Prospective source and failed-owner binding

The new registration is `research/offline-release-recovery-v1-freeze.json`, tagged
`offline-release-recovery-v1`. It binds this adapter, its tests and protocol, the
new one-shot offline supervisor and its tests, and the frozen paced-analysis/HF-V3
registrations. Freeze and verification also bind the exact old failed waiter
state plus stdout/stderr file hashes. That waiter must be actually terminated,
`stopped` in `hf_export`, with no completed stages, exit1, ValueError, and the
original no-retry failure reason. No state or log is edited. Parent/child process
proof retains the existing creation-time-aware PID-reuse checks.

Before registration and launch all seven-stage output targets must be unused.
Existing outputs, even partial ones, block the workflow. The new supervisor uses
`runs/offline-release-recovery-driver/state.json`; it refuses an existing driver
directory and never restarts an ambiguous stage. Its ordered completed-stage list
is exactly the original seven stages. Source verification occurs before private
admission and source/tag/ancestry checks remain authoritative after publication.

## Seven offline stages and unchanged scientific authority

1. `hf_export`: the new admitted private-to-public projection, followed by the
   frozen `paced_resume_analysis.verify_hf()` scientific reconstruction.
2. `main_export`: unchanged frozen paced MAIN union admission and public export.
3. `continuation_provenance`: unchanged paced MAIN public/provenance verification.
4. `figure_input`: unchanged full scientific verification, with a new receipt at
   `runs/offline-release-recovery-driver/verified-public-input.json`.
5. `figures`: unchanged plotting under its recorded Matplotlib interpreter.
6. `figure_provenance`: unchanged plot/input/source/provenance verification.
7. `generator_sensitivity`: unchanged registered offline sensitivity analysis.

The HF report/supplement retain their original V3 paths, strict field schemas and
paced registration identity. Mathematical reasoning, evidence oracle, monitor
parsing, all-assigned denominators, clustering, bootstrap and original primary
invariance checks are unchanged. The new registration never impersonates the old
scientific tag.

A separate `research/hf-offline-release-recovery-proof.json` commits to the new
registration and projection rule, old paced registration, unchanged raw batch
hashes, actual driver state hashes, public report/supplement hashes, and successful
frozen verifier result. It adds no field to the frozen scientific report schema.
`verify_projection(replay=False)` performs source and metadata/hash checks and
cross-matches its batch/driver provenance to the hash-bound report, without using
aggregate values. `verify_hf()` additionally runs the frozen scientific verifier.
The paper gate must verify these source/proof bindings before reading aggregates,
then require the actual new supervisor complete and terminated, all seven stages
completed, and the current receipt and figure provenance. Paper authorship and
visual QA remain separate tasks; these stages never claim either was completed.

Synthetic tests cover scientific equivalence after diagnostic projection,
unknown/private-field rejection, unchanged failed-record/full-reservation handling,
body/native-admission failures before projection, complete identity preservation,
source/parent/failed-waiter binding, unused output/no-overwrite gates, and public
proof/report drift. Production execution is authorized only after source commit,
freeze, recorded tag and push; tests never read actual model answers or infer new
results. Native authenticity continues to require the retained private archive.
