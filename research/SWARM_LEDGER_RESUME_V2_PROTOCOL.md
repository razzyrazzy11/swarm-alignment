# Prospective continuation after a terminal HTTP 500

This amendment is operational and must be committed, frozen, tagged and pushed
before further inference. It does not change the registered Track 4 question:
does the investigator lack evidence, or fail to use evidence already sufficient?
The 640-block design, six reader conditions, exact request bodies and identities,
scientific outcomes, baselines, paired contrasts and inference methods remain fixed.

## What stopped, and what remains

The first router-aware continuation stopped on 8 November at 13:24 UTC after
15,025 reader starts had 15,025 terminal records: 15,024 HTTP 200s and one DS-low
HTTP 500 with unknown usage. The unknown-usage response was outside the old
explicit transient list and correctly triggered its fatal guard. Neither a
successful HTTP status nor failure-free serving establishes scientific correctness.
This HTTP 500 remains a delivery failure, not a reasoning outcome or a replacement
opportunity. It retains its entire pre-send cost reservation and original identity.

Original MAIN and continuation v1 bytes, driver states, receipts, locks and stop
markers are preserved. V2 writes only `runs/swarm-ledger-resume-v2-main`. A
registration binds both stopped archives' metadata hashes and a private native
receipt inventory commitment. Current parent and child termination must be
verified from their actual state identities. A retained lock or unresolved start
blocks admission; this amendment does not delete locks or invent completion.

The prospective complement is exactly 38,735 never-started reader requests plus
240 calibration and 240 controlled-influence requests: 39,215 calls. Full actor
history is retained, including reporter failures. The original full phase plans
remain the authority; requests are rebuilt from authentic actor unions and the
same frozen builders. Across original, v1 and v2, starts must be disjoint and
unique, every started request must have exactly one terminal, and every body,
receipt, host action and cost must pass frozen ledger reconstruction. No failed
scientific identity is ever resent, even if its provider-side completion is unknown.

## Limited change to handling new server errors

V2 recognizes HTTP 500 as a terminal server-delivery failure alongside the
previously registered gateway/overload classifications. This is a prospective
extension, not a retroactive claim that v1 should have silently continued.
The number of HTTP 500 failures across v1 and v2 and all phases is capped at 32,
including the one retained failure. The existing per-phase gateway allowance
also counts HTTP 500s. Once either allowance is exhausted, dispatch stops; already
in-flight calls are drained and retained rather than cancelled or repeated.

For a new HTTP 500, dispatch of unstarted work pauses for at least 60 seconds,
or a valid Retry-After interval if larger, within the unchanged registered
Retry-After bound. The cooldown is persisted. Active requests drain; two healthy
read-only authenticated catalog cycles separated by at least 15 seconds are
required before new dispatch. These checks are readiness probes, not inference
retries. An invalid or excessive Retry-After stops collection. SDK POST retries
remain disabled. The response body is retained privately, not printed or scored.

Unknown usage keeps the full cost reservation. Capture errors, unresolved starts,
malformed successful replies, model/normalization anomalies, authentication,
funding and unclassified failures remain fatal. A known-usage anomalous 500
cannot be admitted as a valid answer. The original 32-connection-error allowance
is carried across v1/v2 rather than reset. Classifying a server error is not
classifying its answer as correct, supported or scientifically usable.

## Unchanged safeguards and finish gates

Keep native one-second spacing, per-model limits two, HF/Ollama provider limits
two, native provider ceiling eight and global ceiling eight. The daily router
blackout remains 04:55–05:05 UTC, bounded outage waits 900 seconds, and the
collection cutoff remains **9 November 05:59 UTC**. No condition is dropped,
endpoint switched, output limit changed or fresh training introduced. Technical,
development, original MAIN, v1, v2 and excluded-pilot costs are counted exactly
once against the same provider, combined, native-class and wallet-floor guards.

A new remaining-workload forecast and independent offline analysis-admission
registration must be bound before new calls. Strict scientific export requires
the actual v2 driver to finish and terminate, actual HF completion and unchanged
stopped archives. The new postprocessor must not mistake stopped old drivers
for current failure or use invented completed states. The excluded serving pilot
must not run before complete primary collection and verification. The paper will
disclose batch timing, all retained delivery failures and this amendment. No
finite estimate is a deadline guarantee; final validation and actual PDF visual
inspection remain necessary. Existing queued research reviews keep their order.

## Primary conventions

- RFC 9110, sections 9.2.2 and 15.6.1:
  https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2 and
  https://www.rfc-editor.org/rfc/rfc9110.html#section-15.6.1.
  HTTP 500 indicates an unexpected server condition; that does not establish
  whether a non-idempotent request was applied, so it is not automatically resent.
- RFC 9110, section 10.2.3:
  https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3.
  Retry-After concerns waiting; here it postpones only never-started work.
- Apart guidelines and Judging and results:
  https://apartresearch.com/sprints/swarm-alignment-2026#guidelines.
  Complete conditions, explicit denominators, preserved provenance and clear
  limitations support execution quality and clarity without promising a score.
- 20-rules-of-learning is used editorially: explain the observed stop, distinguish
  server delivery from reasoning, then state the bounded repair and its limits.
  It supplies neither empirical evidence nor permission to revise frozen outcomes.
