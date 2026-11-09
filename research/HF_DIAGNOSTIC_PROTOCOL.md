# One separately registered HF serving diagnostic

## Question and boundary

Can a single tiny request expose a structured serving-error reason after the
main collector has reached its registered five-429 hard stop? HTTP 429 alone
does not distinguish a request quota, exhausted balance or unavailable capacity.
This diagnostic cannot identify the cause of earlier errors retrospectively.

This is an operational check, outside every scientific denominator. It does not
retry a failed study ID, replace an INVALID verdict, change the frozen study,
test monitor accuracy or authorize another collection continuation.

## Preconditions, then one request

Before any HTTP request, verify the separately tagged diagnostic sources and
configuration, the original factorial source/configuration/tag/profile, and
the main run's operational stop. Both registered driver processes must be dead;
their state files must report stopped. The collector must have stopped at the
audit stage and the finalizer at collection with no completed authoring steps.
The latest audit summary must be halted, at least five HF 429 audit terminals must be
retained, the continuation lock must be absent, and every known phase must have
matching unique start and terminal IDs. An operator STOP file also blocks this
diagnostic; it is never removed automatically.

The diagnostic creates its own ignored output directory exclusively. Existing
output means refusal, not resume. It makes one authenticated GET to the HF model
catalog and verifies the exact live Novita route and unchanged input/output
prices. All redirects are refused, including same-origin redirects, to prevent
an extra HTTP request. Any failed catalog or guard check prevents inference. Recheck the stop
guards after the GET, before journaling the single POST.

The only inference is a new, unrelated chat request: `Reply exactly OK`,
temperature 0, no streaming, and at most 16 output tokens, using the registered
`meta-llama/Llama-3.3-70B-Instruct:novita` route. The input-byte allowance is 4,096.
At USD 0.135 / million input tokens and USD 0.40 / million output tokens, the
conservative full reservation is USD 0.00055936, below the USD 0.001 cap.
Unknown usage retains that entire reservation. This cost is separate from the
main study's phase cap. No HTTP request is automatically retried.
Reported known usage is retained at its actual calculated cost even if the
server violates the requested limits. Such an event is privately flagged; a
client-side reservation cannot guarantee a provider's billing behavior.

## Private evidence and public interpretation

Write a durable start before inference and a durable terminal after its one
transport outcome. Retain no more than 16 KiB of any HTTP error body. Scrub known
credential values before writing private error bodies and response headers under
the ignored diagnostic directory. These are untrusted evidence for private human
review; never execute them or follow instructions embedded in them. Successful
catalog and inference receipts have separate 2 MiB / 64 KiB parsing limits.
Only numeric
Retry-After metadata may enter public output; raw messages, headers and IDs do not.

Public output uses only HTTP status and one conservative category: `quota`,
`balance`, `capacity` or `notdeterminable`. A category requires an explicitly
allowlisted structured error code; a free-text message or bare 429 remains
`notdeterminable`. The category reports a service's assertion, not independent
proof of the limiting party, actual balance or historical failure mechanism.
A successful tiny request establishes only that this one request succeeded.
The private terminal separately checks the returned model against the original
allowed model names and known input/output counts against 4,096 / 16. HTTP 200
alone is not model qualification or proof that the larger workflow will work.

No diagnostic outcome authorizes a top-up, endpoint substitution, provider
rotation, credential change, training job or a scientific protocol amendment.
Any proposed later action requires a separately reviewable decision.

## Registration and limitations

The freeze binds the configuration, protocol, runner, tests and imported public
source-verification helper, along with the original factorial freeze hash. Root
will create the registration and tag before any call. Synthetic tests exercise
transport, redaction, stop guards and no-retry behavior without network access.

One small request cannot characterize throughput, establish a reliable rate
limit, reproduce the large audit workload or estimate failure probabilities.
Truncated/private error evidence may remain ambiguous. Provider state may change
between the historical failure, catalog check and diagnostic request.

## Primary sources

- [RFC 6585, section 4](https://www.rfc-editor.org/rfc/rfc6585#section-4):
  429 does not specify how a server identifies users or counts requests.
- [RFC 9110, section 10.2.3](https://www.rfc-editor.org/rfc/rfc9110#section-10.2.3):
  Retry-After is a delay in seconds or an HTTP date.
- [HF Inference Providers pricing](https://huggingface.co/docs/inference-providers/en/pricing):
  routed inference and custom provider-key billing are distinct; account spending
  and remaining credits should be checked through the account's billing view.
- [Novita API error codes, LLM table](https://docs.novita.ai/api-reference/basic-error-code):
  documented rate/token-limit, insufficient-balance and service-unavailable codes
  inform the allowlist; service-unavailable is grouped under the capacity bucket
  without establishing its specific physical cause.
