# Offline release recovery V2: recorded scheduler metadata

This is a separate prospective operational amendment after the registered V1
release adapter stopped in its first offline HF stage. V1 source, registration,
failed state and logs remain unchanged. It adds no inference, training, delivery
retry, outcome selection or numerical-method change. Collection is already
complete. New V2 sources must be committed, registered, tagged and pushed before
recovered scoring or public output.

## Exact diagnosis and minimal correction

The frozen collectors append the top-level `next_delay_seconds` field after
constructing each private terminal row: `hf_completion.py`, `hf_completion_v2.py`
and `hf_completion_v3.py` all retain it in their raw journals. The unchanged
private-ledger functions return that field. It is present in all1,898 terminal
records (9 +1,732 +157); it is not an added scientific response or a newly
inferred value. V1's strict top-level projection whitelist omitted this recorded
scheduler field and correctly stopped before producing either public HF output.
The earlier synthetic fixtures lacked this source-shaped field; V2 adds an
end-to-end admitted-boundary regression fixture that includes it.

V2 invokes the unchanged `hf_completion_v3.private_completed()` before any
projection. It requires `next_delay_seconds` to be an integer or float (not a
Boolean), finite and nonnegative. There is no invented universal upper bound:
a frozen collector can record a large Retry-After delay in a terminal row while
also halting because that delay exceeds its live wait envelope. The recorded
value is never changed. V2 deep-copies each row, removes only this recognized
private scheduler field from the candidate public projection, then delegates to
frozen V1 `project_admitted()` unchanged. Every other unknown top-level field or
private transport/diagnostic field still fails the same strict whitelist.

The frozen V1 transport boundary retains original public `http_status`,
`latency_seconds`, and `error` values. Private diagnostic timestamps, connectivity
flags and `next_delay_seconds` remain unchanged in the retained raw archive.
They do not become evidence labels or scientific results. No response, failed
terminal, identity, cost, usage counter, body commitment, original public timing
or numerical statistic is dropped, replaced, imputed or selected.

## Registration and two failed-owner commitments

New sources are `experiments/offline_release_recovery_v2.py`, its test and this
protocol, plus `offline_release_supervisor_v2.py` and its test. The new tag is
`offline-release-recovery-v2`; registration is
`research/offline-release-recovery-v2-freeze.json`. Parent commitments include the
frozen V1 recovery registration and original paced/HF-V3 registrations. Source,
tag, ancestry, closed schema and parent checks remain mandatory.

The new registration commits to both old failed waiters' actual final state and
stdout/stderr hashes. Each must be actually terminated, stopped in `hf_export`,
with zero completed stages and the original no-retry ValueError/exit1 attestation.
Creation-time-aware PID-reuse checks remain unchanged. No old state, log, freeze
or source is edited or replaced. The new driver uses
`runs/offline-release-recovery-v2-driver/state.json`, refuses an existing driver
directory, and executes exactly the original seven offline stages. The only
command-routing changes are the new adapter/supervisor names and its own fresh
figure-input receipt path.

All stage output targets must be unused before registration and launch. A
pre-freeze metadata-only preflight must invoke the exact V2 `project_admitted()`
on the rows returned by unchanged `private_completed()`, not merely inspect the
raw transport subdictionary. The preflight must not call `build_completed`,
`analyze`, export, plotting, or any inference service; it may report only schema
validity and counts. This check verifies the actual admission/projection boundary
without using monitor accuracy or changing data.

## Scientific output and paper gate

HF report and supplement paths, strict schemas, paced scientific identity and
frozen numerical calculation remain unchanged. Frozen
`paced_resume_analysis.verify_hf()` remains final scientific authority. The V2
companion is `research/hf-offline-release-recovery-v2-proof.json`; it binds the
new registration/projection rule, original paced registration, all three raw
batch hash inventories, actual driver hashes, public report/supplement hashes
and successful frozen verification. It is separate from the scientific report.

APIs remain `verify()`, `verify_projection(replay=False)` and `verify_hf()`.
Metadata verification binds the V2 source and proof before aggregate use and
cross-matches proof batch/driver hashes to the hash-bound HF report.
`verify_hf()` also invokes the unchanged frozen scientific reconstruction.
The paper gate must require the actual V2 supervisor successful and terminated,
all seven stages complete, both failed predecessors stopped/terminated, and the
current V2 receipt/figure provenance. The paper itself and visual QA remain
separate deliverables; a completed data pipeline does not claim either is done.

Synthetic tests cover the recorded scheduler field at the private-completed
boundary, accepted finite nonnegative values without an invented cap, rejected
Booleans/nonfinite/negative/missing values, closed unknown-field rejection,
scientific equivalence, failed/full-reservation preservation, raw admission/body
failures, no-overwrite gates, source/parent/failed-state bindings and proof drift.
Tests do not open actual answer journals, score actual results or call providers.
