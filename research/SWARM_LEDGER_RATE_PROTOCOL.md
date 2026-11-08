# Prospective precise rate-limit continuation

This is a new operational amendment, not a change to any already frozen policy.
It is prepared before new data and requires independent review, a passing exact
remaining-work forecast, committed/tagged source and a separate analysis freeze
before any inference. No automatic retry of an attempted POST is introduced.

## Concrete trigger and independent admission

The efficient collector stopped on8November18:07UTC after1,497 started requests
all had terminal records:1,495 HTTP200 and two G31 Adaption HTTP429 errors. The
failed private JSON envelopes specify `type=rate_limit_error`,
`code=rate_limit_exceeded`, null param and a rate-limit message whose explicit
60second wait agrees exactly with numeric Retry-After60. There was no funding,
quota or authentication evidence in those two bounded error envelopes. This does
not establish an account balance or provider-wide service health. Old rows keep
their original fatal-provider flags and full unknown-usage cost reservations.

Admission independently replays the actual predecessor's full phase ledger,
including body/native-receipt/normalization/cost commitments and every start's
terminal. It requires exactly those two proven rate errors, native hashes,
known-usage anomaly-free HTTP200s for the other1,495 rows, no capture/connection
faults or capture-failure journal entries, the expected fatal guard marker,
actual stopped/readers/exit1 state, dead owned parent/optional child and no lock.
It does not silently bypass a generic fatal stop. A different fault requires a
new investigation and cannot use this exact exception.

## Precise classifier, bounded waiting

New Adaption429s are considered operational rate limits only when the JSON error
object has exactly the observed keys/type/code/null param, a message at most512
characters containing the rate-limit phrase and exactly one explicit numeric
retry-after duration with units, and one positive numeric Retry-After interval
at most900seconds and within the inherited wait ceiling. Message and header
values must agree exactly as decimals; no tolerance, zero wait, header-only rule,
multiple headers or duplicate JSON keys is accepted. Funding, credit, billing,
quota, authentication, authorization and account-suspension markers remain fatal.
Unknown429s remain fatal. These rules are deliberately narrower than all possible
provider429 errors and may safely stop on an unfamiliar future error.

Only new-amendment rows receive `provider_failure_class=adaption_rate_limit`.
Their earlier generic negative rate-word flag is removed only after this exact
positive operational classification. Existing archived flags are never edited.
For inherited failure/streak accounting, the new amendment reads hash-verified
private rate envelopes before applying the generic fatal-flag rule, so the two
old failures remain counted rather than disappearing from guards or denominators.

A recognized rate response remains terminal, receives no successful verdict and
keeps its full reservation. Pause only never-started work. Preserve the existing
60/120/240/480second backoff, valid larger Retry-After wait, at-most-eight provider
failure streak and900second live provider admission episode until a clean
HTTP200/known-usage/non-anomalous completion resets it. A cooldown that cannot fit
inside that episode stops the process. Drain active requests, obtain two healthy
read-only catalog cycles at least15seconds apart, and revalidate pinned models,
routes, capability and pricing before new dispatch. Blocking read-only checks and
draining can finish later than an admission episode; they never authorize a POST
after that episode or the collection cutoff. Metadata-only recovery is bounded
and cannot mask funding/auth/model/capture errors.

## Immutable six-batch union and unchanged experiment

The union comprises original MAIN, v1, v2, v3, efficient-v1 and rate-v1. This
collector writes only `runs/swarm-ledger-rate-v1-main`. All five stopped archives,
native inventories and actual stopped driver states are bound into registration.
Full original plans remain authoritative: request identities are unique and
disjoint across batches, every started request is terminal, and all retained
bodies/host actions/normalizations/costs replay. No previously attempted failure
becomes unstarted. The new forecast must match dynamically computed remaining
reader/calibration/influence counts and exact descriptor hashes; no stale count
is hardcoded. Previous excluded serving pilots remain blocked/unrun unless
separately admitted.

The 640-block design, all six readers, procedures, evidence contrasts, endpoints,
decoding, scoring, bootstrap and fine-tuning status remain unchanged. The literal
eligibility cache, sorted first-eligible dispatch order, verified configuration
snapshot and one-second native spacing remain. Global/provider/model capacity
limits, original cost caps, unknown reservations, wallet floor and all prior cost
lineage carry forward. Known rate failures count toward the existing1,024-per-
phase server allowance and provider streaks; HTTP500total32 and connection32
allowances are not reset. No spending setting or model route changes.

The04:55–05:05UTC router pause, bounded health checks and collection cutoff
9November05:59UTC remain. The new forecast separately allows an Adaption admission
episode in addition to existing recovery stress, but is conditional and gives no
completion guarantee. Frozen sources are not edited; hashes/tags precede fresh
calls. Strict six-batch export, actual termination proofs, completed original HF
recovery, figure provenance and sensitivity precede empirical paper authoring.
Final PDF inspection and queued reviews remain separate outstanding work.

## Defensive interpretation and primary conventions

These are delivery failures, not evidence of reasoning failure. All-request
accounting stays separate from accuracy conditional on admitted sufficient
evidence. The report will disclose the operational amendments and serving
failures while retaining the Track4 question: evidence acquisition, verdict
delivery, or use of sufficient evidence? Earlier samples, scripted calibration
and MAIN are not pooled into a favorable result.

- RFC6585 section4 defines429 and discusses Retry-After guidance:
  https://www.rfc-editor.org/rfc/rfc6585.html#section-4
- RFC9110 section9.2.2 explains why ambiguous non-idempotent requests are not
  automatically repeated; section10.2.3 specifies Retry-After.
  https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2
  https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3
- Provider error details are primary observations from the retained failed
  envelopes, not a general documented guarantee about future Adaption errors.
  Public Adaption API conventions: https://docs.adaptionlabs.ai/api/python
- Apart guidelines/Judging and results emphasize empirical execution and clear
  limitations: https://apartresearch.com/sprints/swarm-alignment-2026#guidelines
- 20-rules-of-learning is editorial: concrete fault, exact distinction, bounded
  repair and explicit limits. It is not evidence or a guarantee of judging scores.
