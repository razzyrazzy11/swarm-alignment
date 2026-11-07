# Prospective PID-safe MAIN release wrapper

This operational wrapper addresses Windows PID reuse without changing scientific
sources, original driver states, native journals, scoring, estimands or bootstrap.
Register its three files in the V2 operational source set before the operational
freeze. No result is inspected or inferred by this protocol.

The frozen analysis checks only whether a recorded PID exists. Windows can
assign an exited driver's PID to another process, falsely blocking later private
admission/export. Do not edit a terminal state, supply another PID, patch frozen
globals or terminate an unrelated process to get past that check.

`analysis/ledger_release.py` accepts only the actual MAIN state at
`runs/swarm-ledger-v1-main-driver/state.json`, derived from the scientific study
ID rather than the pilot dispatcher ID, with status stopped or
complete, distinct positive parent/child PIDs and a nonfuture aware UTC final
timestamp. It calls the existing V2 `process_dead(pid, updated)` for both:
an absent process passes; on Windows an existing PID passes only when its current
creation time is later than the original final-state timestamp, proving reuse.
An original live process, older/equal creation time, permission/lookup failure
or missing timestamp fails closed. Non-Windows handling remains conservative.

Raw state bytes must remain unchanged during these checks. Private admission
binds their SHA, the scientific MAIN registration SHA, V2 MAIN operational
registration SHA and frozen data commitment. The global scientific collector
guard is held across admission and release, and every other collector lock under
project `runs` blocks release. Existing locks are never removed or overridden.

The wrapper copies only orchestration and serialization needed to replace the
PID-only preflight. Frozen `admit_phase` still requires exact planned identities,
request-body commitments, full graph coverage, no unresolved starts, native
receipt hashes, normalization, host-action replay and cost reconciliation.
Frozen scoring, analysis, baselines, uncertainty, public-record allowlists,
sharding limits and public metadata schema are reused unchanged. Both scientific
and operational registrations must verify before admission and again at release.

The actual driver/data/registration commitments and process/lock checks are
repeated before export, after writing public output, and after the unchanged
frozen `verify_public` succeeds. The output directory has exactly the original
public inventory, with no operational receipt inserted into it. Extra private
admission proof is not an extra scientific datum or a public artifact.

Commands require an explicit real driver state and, for export, a new explicit
project-local destination:

```
python -m analysis.ledger_release validate --driver-state runs/swarm-ledger-v1-main-driver/state.json
python -m analysis.ledger_release export --driver-state runs/swarm-ledger-v1-main-driver/state.json --output data/new-ledger-release
```

An output directory is not authorized for publication until the wrapper returns
success and the frozen public verifier has passed. A failed check may leave an
unverified output directory for diagnosis; do not publish, overwrite or silently
delete it. The offline verifier remains authoritative for public statistical
reconstruction, while private HTTP authenticity still requires the private
archive. This wrapper does not strengthen that provenance assumption.

Synthetic tests must cover absent/reused versus live/unknown process identities,
unchanged state bytes, wrong state paths/timestamps, hash drift, unrelated locks,
incomplete/unresolved admission and exact frozen serialization parity. Test
patches and toy fixtures are confined to tests; production never replaces a
frozen function or invents a process-termination attestation.
