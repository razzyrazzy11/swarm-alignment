# Workload-shaped serving-capacity canary

## Question and scope

Does the same HF-routed Llama / Novita service accept 24 fresh neutral requests
with input size and output reservation resembling the planned audit workload,
at a conservative 30-second start interval? A previous tiny request succeeding
does not establish capacity for this workload. This canary tests serving behavior,
not evidence use, temporal reasoning, swarm safety or scientific accuracy.

Only operational input-count metadata informed the size: among 1,977 known HF
calls, minimum / median / maximum input counts were 1,119 / 1,423 / 1,579. No
scientific verdicts or correctness outcomes were inspected to set this protocol.

## Frozen request, budget and sequence

Use the original `meta-llama/Llama-3.3-70B-Instruct:novita` route, temperature 0,
4,096 output-token allowance, non-streaming transport and 24,000 input-byte cap.
The separate accepted input-token range is 1,579 to 24,000; the upper token and
serialized-byte bounds happen to have the same numerical value.
The 24 independently submitted neutral payloads start with distinct local IDs
`capacity-00` through `capacity-23`, followed by `a ` repeated 2,091 times and
`Reply exactly OK`. The early changing ID prevents reuse of an identical long
prefix. These are fresh synthetic requests, never copies of study packets or
retries of study IDs. Their eventual content is checked only as serving output.

One live catalog GET must confirm the exact route and original USD 0.135 / 0.40
per-million input/output prices before inference. At those prices each full
reservation is USD 0.0048784; all 24 reserve USD 0.1170816, below USD 0.12. Retain
actual known cost, including any provider-reported overrun. Unknown usage retains
the full reservation. The cap is a client scheduling bound, not control over a
provider that violates its own reported usage or requested limits.

Wait at least 60 seconds initially and 30 seconds between sequential starts.
Wait before durable start writes, checking STOP during waits and before dispatch.
There are no queued requests, retries, replacement cases or repetitions until
success. Check the main collector's existing hard-stop guards before the catalog
GET and again before every POST: original drivers stopped and dead, five retained
audit 429 events, no unresolved starts, no continuation lock or operator STOP.
The canary's own output STOP also blocks further requests. Never remove STOP.

Stop on the first bad receipt: failed HTTP transport, 429, incomplete or malformed
output, unknown usage, unexpected returned model, input count below 1,579 or above
24,000, output count above 4,096, finish reason other than `stop`, text other than
`OK` after trimming, or a cost / operator guard. At most 24 POSTs are permitted.
Retain each failure and all unstarted planned requests in the final report.

## Evidence and pass criterion

Create `runs/hf-capacity-v1` exclusively; an existing folder prohibits resume.
Keep durable starts and terminals. Reuse the separately registered diagnostic
transport's redirect refusal, bounded private receipts and credential scrubbing.
HTTP error bodies remain ignored private evidence; never execute their contents.

Pass requires all 24 planned requests returned and every serving check passed,
without a guard stop, missing receipt or budget violation. A partial or failed
canary remains a valid report with `passed: false`. Native receipts, headers and
provider IDs never enter the public report. Public metadata records local IDs,
timestamps, monotonic start offsets, HTTP status, conservative error category,
usage counts, permitted model alias or an unexpected-model sentinel, completion
and content booleans, cost and profile validity.
Wall-clock `started_at` records the durable start journal; monotonic
`start_offset_seconds` records the actual HTTP opener invocation. Subsequent
pre-journal waits are anchored to the previous opener invocation, so variable
journal or request-construction time cannot shorten the HTTP-start interval.

Export hashes of the private attempt and terminal journals and the source freeze.
Public verification rederives counts, costs, intervals and every pass criterion
from that metadata without credentials or private receipts. It verifies internal
replay consistency; hashes alone do not prove that a private receipt is truthful.
An unresolved interrupted start is reported explicitly and can never pass.
Before any later main continuation, private preflight must additionally rebuild
this report from the actual canary journals and bound request plan and require
an exact metadata/hash match. This check does not contact a service or overwrite
the public report. It detects stale or edited public exports; it is not external
attestation against fabrication of the local private journals themselves.

## Subsequent decisions and limits

The source/configuration/helpers are committed and separately registered before
data collection. A pass does not restart the study, erase five historical errors
or change any scientific denominator. Any later main continuation must have its
own prospective registration binding this exact public report and its hash.

Twenty-four probes cannot establish a reliable service-level guarantee, diagnose
the past 429 mechanism, forecast future quotas, validate scientific performance
or eliminate time-varying provider/model drift. Distinct prefixes reduce identical
prefix reuse without proving the absence of all provider caching.

## Primary sources

- [HF Inference Providers pricing](https://huggingface.co/docs/inference-providers/en/pricing):
  routed inference pricing and billing differ from custom provider-key usage.
- [Novita LLM error codes](https://docs.novita.ai/api-reference/basic-error-code):
  request limits, token limits, insufficient balance and service unavailability
  are distinct documented service assertions.
- [RFC 6585, section 4](https://www.rfc-editor.org/rfc/rfc6585#section-4):
  HTTP 429 does not identify how a server counts requests or users.
