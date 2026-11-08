# Prospective provider-availability continuation (v3)

This operational amendment is registered before fresh inference. It preserves
all six reader conditions, 640 independent blocks, original bodies/identities,
model routes, decoding, scoring and scientific estimands. No serving failure is
converted to a reasoning result. The main question remains whether oversight
needs evidence acquisition, usable verdict delivery, or use of sufficient evidence.

## Observed stop and exact remaining work

Continuation v2 stopped after 4,901 terminal reader requests: 4,897 HTTP200,
two HF-schema HTTP504 and two HF-schema HTTP429 failures. Local examination of
only the private failed envelopes found JSON error objects with
`type=invalid_request_error`, `code=engine_overloaded`, `param=null` and a message
indicating overload. This identifies observed serving availability, not quota
exhaustion or a verified account balance. Raw messages, native IDs and headers
remain private. Existing rows are never rewritten to add classifications.

Original, v1 and v2 archives/states remain immutable and hash-bound. V3 uses
`runs/swarm-ledger-resume-v3-main`. All starts across four batches must be disjoint,
unique and terminal, with original full plans, receipt hashes, host actions and
costs replayed. The complement contains 33,834 never-started MAIN reader jobs,
240 calibration and 240 influence jobs (34,314 total). A terminal failed request
never becomes unstarted and is never retried or replaced. Unknown usage retains
its full pre-send reservation. No POST canary or SDK retry is introduced.

## Precise fail-closed classification

A new HF429 is recoverable availability only if its bounded JSON error envelope
has exactly the observed keys/type/code, null param, and a bounded overload
message with no funding, quota, credit, billing, rate-limit or authentication
markers. Duplicate JSON keys at any level are rejected. Other429s, funding,
authentication, unknown response types, malformed successful responses, capture
failures, model/route/price drift and unresolved requests remain fatal.
New rows record only safe `provider_failure_class=hf_engine_overloaded` metadata.
Old failed429s are classified read-only from hash-verified private receipts for
inherited guard accounting, without changing their terminal rows or outcomes.
Existing known gateway classes and HTTP500 handling remain, including the total
32 HTTP500 ceiling across prior continuations and v3. All server/availability
failures count toward the original 1,024-per-phase gateway allowance.

## Bounded live recovery, never a repeated scientific request

On recognized availability failures, drain already-started work and pause new
dispatch. Per-provider consecutive recognized failures use waits 60,120,240,480
seconds (480 thereafter), or valid larger Retry-After up to the original bound
and at most900 seconds. More than eight consecutive recognized failures stops
the collector; valid HTTP200/known-usage/non-anomalous transport completions reset
that provider's counter. These are transport counters, not answer-quality checks.
Counters include retained historical serving failures; a new batch does not
reset financial or failure allowances. All eight requests already in flight may
finish and remain accounted for when a failure is detected.

A provider's live-v3 unavailability episode starts at its first newly recognized
v3 failure, never at a historical receipt timestamp. It has a cumulative
900-second monotonic elapsed limit until a clean HTTP200 with known usage and no
normalization anomaly resets it. Historical consecutive failure counts still
carry forward. If a required cooldown cannot fit in the remaining episode, or
the episode expires, stop rather than silently extend it. Check the episode
before every POST and again after health checks; passing a catalog probe cannot
override an exhausted episode. Read-only metadata checks have their own bounded
900-second budget as well, not permission to extend an active inference episode.
This is a deadline for admission of another POST, not a promise that draining
already-started calls or a blocking read-only health check finishes within exactly
900seconds. Those operations can finish later; after they return, an expired
episode cannot authorize a new POST.

Two healthy authenticated read-only catalog cycles at least15seconds apart are
required after draining and before new dispatch. The catalog gate treats only
recognized availability or classified connectivity as unavailable; auth/funding,
model and malformed success remain fatal. Read-only GETs may repeat within a
900second elapsed budget and the unchanged cutoff; late successful catalog
responses cannot grant admission. Frozen route, capability, digest and pricing
checks run again after recovery and before dispatch reopens. `readonly_readiness()` exposes only these GET checks and never
an inference request.

`availability-state.json` provides safe waiting/recovered state, failure class,
consecutive count, next-dispatch timestamp and update time. It contains no request
IDs, native IDs, keys, headers, outputs or balances. Its presence is operational
metadata, not proof of scientific correctness. Heartbeats observe this state;
they do not restart a dead collector or alter frozen protocols.

## Unchanged caps, cutoff and release requirements

Native pacing stays one second; model limits two, shared HF/Ollama limits two,
native provider ceiling eight and global ceiling eight. The router blackout is
04:55–05:05UTC, outage wait at most900seconds, and the original collection cutoff
is 9November05:59UTC. All prior and new costs and full unknown reservations count
exactly once against unchanged phase/provider/combined/native-class/wallet guards.
No model switch, dropped condition, shorter output or changed spending setting is
permitted. A fresh forecast explicitly accounts for additional bounded recovery
waiting, but is a conditional scenario and cannot guarantee completion.

Commit/freeze/tag/push sources and the separate analysis registration before
fresh data. Strict export requires actual new collector completion/termination,
unchanged stopped-prefix proofs, completed original HF recovery and all scientific
replay/provenance/figure/sensitivity stages. The excluded serving pilot remains
blocked and unrun; any future requeue requires separate admission. Final paper authoring, every-page visual inspection
and queued reviews remain outstanding until their actual gates are satisfied.
The paper must disclose serving failures and all collection amendments; earlier
all-NONE results, scripted calibration and MAIN are separate populations.

## Primary sources and explanatory conventions

- RFC9110 sections9.2.2,10.2.3,15.6.1: non-idempotent request ambiguity, waiting
  guidance and server errors. https://www.rfc-editor.org/rfc/rfc9110.html
- RFC6585 section4: HTTP429 signals too many requests but does not alone establish
  whether the cause is provider capacity, quota or funding; inspect the actual
  bounded error classification rather than assuming. https://www.rfc-editor.org/rfc/rfc6585.html#section-4
- HF inference-provider documentation describes routed provider inference and
  provider/billing differences. https://huggingface.co/docs/inference-providers/index
- Apart guidelines/Judging and results require clear empirical methods and
  limitations: https://apartresearch.com/sprints/swarm-alignment-2026#guidelines
- 20-rules-of-learning guides the concrete stop→precise distinction→bounded repair
  explanation. It supplies no scientific evidence or judging-score guarantee.
