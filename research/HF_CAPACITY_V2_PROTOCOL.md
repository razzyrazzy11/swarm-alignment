# Capacity v2: completed serving, independent of wording

## Why a separate version is necessary

The frozen v1 canary stopped after one HTTP 200 completion because its wording
was not exactly `OK`. Its known input/output counts were 2,134 / 32, with an
allowed model alias and stop finish reason; recorded cost was USD 0.00030089.
That observation failed v1's strict wording rule. It does not demonstrate a
serving-capacity failure. V1's source, tag, failed result and private receipts
remain unchanged and are never pooled with or replaced by v2.

V2 corrects this operational criterion prospectively, before new requests.
`content_ok` is still reported descriptively, but never determines admission,
stopping or pass. This is not monitor accuracy, schema-task qualification,
training or a choice of main-study prompts based on model answers.

## Fixed workload, resource bounds and stopping

Submit at most 24 fresh neutral requests with early IDs `capacity2-00` through
`capacity2-23`, followed by `a ` repeated 2,091 times and `Reply exactly OK`.
The distinct new prefixes make every request body different from failed v1.
No original study packet or ID is reused. No request is retried or replaced.

Keep the same Llama 3.3 70B / Novita route, temperature 0, no streaming, 4,096
output-token allowance, 24,000 serialized-byte cap, and accepted input-token
range 1,579–24,000. The size threshold derives only from previously recorded
operational token counts, not scientific correctness. One catalog GET must
confirm the original USD 0.135 / 0.40 per-million token prices and live route.
Each full reservation is USD 0.0048784; all 24 reserve USD 0.1170816, below
USD 0.12. The separate v1 cost is retained separately. Unknown usage reserves
the full amount; known usage always retains its actual calculated cost, even
if a provider reports an overrun. These are client bounds, not billing guarantees.

Use one request at a time, initial pause at least 60 seconds, and at least
30 seconds between actual HTTP opener invocations. Wait before durable start
writes; an immutable v1 timing helper records actual opens and checks STOP.
Before the catalog and each POST, require the original main guards: stopped
and dead registered drivers, five retained audit 429 events, no unresolved
starts, no main continuation lock or operator STOP. The canary's own STOP
also blocks requests and its final pass. Never remove STOP automatically.

A valid serving receipt requires HTTP 200, known nonnegative token counts
within those limits, an original allowed model alias, one chat-completion
choice with a dictionary message and string content, and finish reason `stop`.
Any string content is allowed; neither its exact wording nor its meaning is
an accuracy criterion. Stop immediately on any failed, incomplete, malformed,
unknown-usage, unexpected-model, token-limit, budget or operator receipt.
No “continue until success” procedure is allowed.

## Evidence, replay and subsequent decisions

Create `runs/hf-capacity-v2` exclusively. Keep durable starts and terminals;
unknown and interrupted starts retain full reservations. Reuse v1's immutable
timing and aggregation helpers, and the already frozen diagnostic transport
with no redirects, bounded private receipts and credential scrubbing. Error
bodies and headers stay ignored and private; their contents are never executed.

Pass requires all 24 planned requests completed with valid serving receipts,
proper spacing, no budget violation and no guard stop. `shape_ok` records the
transport shape; `content_ok` records exact-OK wording without affecting pass.
Retain partial failures, unstarted IDs, source/plan commitments and raw journal
hashes. Public reports contain only safe operational metadata and use LF bytes.
Public replay rederives counts, costs, intervals and criteria without credentials
or private receipts. Private preflight additionally reconstructs the report from
the actual bound journals and plan and requires an exact match without writing.
Neither check independently attests against fabrication of all local receipts.

Freeze these four new files and the imported immutable v1 module before any
new requests. Verification recursively checks v1 and its original helper/tag
chain, but does not require v1 to have passed. A v2 pass does not restart the
main study, reset historical failures, change scientific denominators or prove
future throughput. Any later main continuation needs its own prospective
registration binding the exact v2 report. Twenty-four completed neutral probes
cannot establish a service-level guarantee or scientific task competence.

## Primary sources

- [HF Inference Providers pricing](https://huggingface.co/docs/inference-providers/en/pricing)
  distinguishes routed inference pricing and billing from custom provider keys.
- [Novita LLM error codes](https://docs.novita.ai/api-reference/basic-error-code)
  distinguishes rate/token limits, balance and service availability assertions.
- [RFC 6585, section 4](https://www.rfc-editor.org/rfc/rfc6585#section-4)
  explains that 429 alone does not specify how requests or users are counted.
