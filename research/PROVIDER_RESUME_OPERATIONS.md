# Prospective HF engine-availability recovery

The server-v2 batch stopped at14:58UTC on8November with4,901 unique starts and
4,901 terminal records:4,897HTTP200, twoHF-schema504s and twoHF-schema429s.
Both429 private error envelopes identify `engine_overloaded` with the structured
type `invalid_request_error` and a null parameter. This is more specific than
inferring funding or availability from a status alone. Existing frozen logic
recognized a different overload taxonomy, so its fail-closed stop was correct.
Preserve those four failed deliveries with full unknown-cost reservations;
they must not be repeated or converted into successful results.

The new amendment retains the complete original/v1/v2 archives and source maps.
Only33,834 unstarted MAIN reader identities plus240calibration and240influence
identities remain. All six scientific conditions,640blocks, original request
bodies, endpoints, decoding, evidence construction, scoring and bootstrap
remain unchanged. Register and push collector, analysis, supervisor and forecast
before inference. Four-batch disjoint union must reject repeated identities,
mutated retained receipts, unresolved starts or altered plan/body commitments.

## Bounded automatic recovery, not request retry

The collector owns automatic pause/recovery for specifically registered serving
errors. It records the failed call once, retains its reservation, drains current
work, observes bounded backoff/valid Retry-After and requires two healthy
read-only probes15seconds apart before dispatching only unstarted identities.
Its operational availability-state metadata is visible to sanity checks.
The900-second episode limit governs new inference admission. Already running
requests drain, and bounded read-only checks may finish later; it is not a hard
900-second termination promise for every operational call.
No heartbeat should blindly restart a stopped collector, repeat an inference
POST, remove a lock or invent a completion state. Known bounded pauses are
normal; exhausted guards and unrecognized failures require attention.

Unknown429s, credit/quota/authentication failures, capture/storage errors,
model/profile mismatches and malformed successful results remain fatal.
The exact HF overload classifier and finite pause/episode allowances are in
the collector protocol. A positive model catalog response establishes access
and advertised availability, not a guarantee of subsequent inference or billing.
No SDK retries, fallback model, endpoint change or quota/spending change occurs.

The existing global/provider/model ceilings, native spacing, wallet floor,
combined/scientific cost caps,04:55–05:05UTC router blackout and9November05:59UTC
collection cutoff remain. The updated conditional forecast uses exact remaining
counts and the original cost model, retained spending,25%headroom, auxiliary
work, original overhead, default500pause sensitivity and one bounded900second
HFavailability episode. It is not a bound on all future failures or all allowed
Retry-After waits, nor a completion guarantee.

## Offline completion and report

Actual collector state: `runs/swarm-ledger-resume-v3-driver/state.json`.
Actual waiter state: `runs/provider-resume-postprocess-driver/state.json`.
The waiter requires actually complete and terminated v3/HF collectors plus
unchanged stopped predecessors before HF export, MAIN export, strict provenance,
figure-input replay, plots, figure verification and generator sensitivity.
The manuscript must bind the new provider-analysis registration and
`research/swarm-ledger-provider-resume-release-proof.json`. Old stopped states
cannot satisfy readiness. Final empirical interpretation and every actual PDF
page still require review. Keep the main report within8pages, references and
appendices excluded. No unfinished empirical outcome is selected or scored
during operations. The optional serving pilot remains blocked/unrun; the four
queued scientific reviews remain after validation and paper integration.

The 20-rules-of-learning explanation sequence remains concrete handoff,
evidence/delivery/use distinctions, matched comparisons, findings and limits.
Operational failures are delivery outcomes, not evidence of deficient reasoning
or swarm misconduct. A health check is not scientific validation.

Primary sources:

- [HF provider routing](https://huggingface.co/docs/inference-providers/index)
  documents the proxy/provider distinction; keep the registered route fixed.
- [HF catalog API](https://huggingface.co/docs/inference-providers/en/hub-api)
  documents read-only availability discovery, not a completion promise.
- [RFC6585 §4](https://www.rfc-editor.org/rfc/rfc6585.html#section-4)
  defines429 and optional Retry-After; structured provider errors must still be
  distinguished rather than assuming every429 is funding or overload.
- [RFC9110 §9.2.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2)
  does not justify automatically repeating ambiguous non-idempotent POSTs.
- [Apart guidelines and judging](https://apartresearch.com/sprints/swarm-alignment-2026#guidelines)
  remain the execution, clarity and impact reference; publication/submission
  remains separate from private-repository collection and authoring.
