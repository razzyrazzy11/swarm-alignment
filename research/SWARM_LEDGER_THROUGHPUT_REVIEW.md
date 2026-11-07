# Swarm Ledger: throughput review before main collection

Checked 7 November 2026, approximately 14:48–14:51 UTC. This memo uses only
development transport timings, start metadata, HTTP status and rate-header
metadata. No model answers, verdict accuracy, labels or scientific effect sizes
were inspected. The technical/development registrations remain immutable; main
collection had not begun when this review was requested.

## Decision

A prospective main-only scheduling amendment is justified for investigation,
because the existing two-request model cap may not finish the registered workload
before the deadline. It is **not** evidence that higher concurrency is supported
or that increased credits buy greater service capacity. Final selection needs
actual development reader timings and an independently registered bounded
capacity pilot. Neither changing running development collection nor silently
modifying its frozen module/config is appropriate.

## What official documentation establishes

The [Adaption SDK documentation](https://docs.adaptionlabs.ai/api/python/)
supports asynchronous clients and an aiohttp backend for concurrency. It maps
HTTP 429 to a rate-limit error, exposes raw headers, and retries certain failures
twice by default. Any SDK substitution would need explicit zero retries to
preserve this experiment's request accounting. The current collector does not
use those SDK retry defaults.

The [Responses API schema](https://docs.adaptionlabs.ai/api/resources/responses/methods/create)
documents output limits and generation settings, but I found no numeric RPM,
TPM or concurrent-request entitlement there. The
[model-list schema](https://docs.adaptionlabs.ai/api/resources/models/methods/list)
describes availability to the caller and model identifiers, not a concurrency
quota. Searching the official quickstart, key concepts, model page, FAQ, API index
and SDK documentation did not establish an account-specific rate-limit endpoint.
This is a bounded documentation search, not proof that no private limit exists.

The [hosted model page](https://docs.adaptionlabs.ai/inference-stacks/models/)
prices Qwen-397B at 0.55 input and 3.50 output credits per million tokens, with
0.225 for eligible cached input. Published context limits are deployment limits;
they do not specify throughput. Retain conservative uncached cost reservations.
Caching can affect measured latency and should not be treated as guaranteed.

The [MCP troubleshooting guide](https://docs.adaptionlabs.ai/tools/mcp)
also warns that too many job launches can cause 429. Those dataset/training job
instructions are not a published Responses concurrency allowance.

## Development transport observations

The snapshot at 14:48:19 UTC contained complete principal/coordinator phases and
a partially completed X phase. Times below include all observed terminal HTTP
responses; none were filtered by model correctness.

| Phase/profile | Completed | Mean seconds | Median | p90 | HTTP status |
|---|---:|---:|---:|---:|---|
| Principal/Q397 | 20 | 35.863 | 35.422 | 52.829 | 19 × 200; 1 × 504 |
| Coordinator/Q397 | 20 | 23.574 | 17.102 | 47.000 | 20 × 200 |
| X/Q397, partial | 8 | 29.481 | 26.641 | 46.360 | 8 × 200 |
| Principal/Q27 | 20 | 11.983 | 10.703 | 17.469 | 20 × 200 |
| Coordinator/Q27 | 20 | 4.072 | 3.851 | 5.656 | 20 × 200 |
| Principal/GLM53 | 20 | 3.198 | 3.523 | 6.656 | 20 × 200 |
| Coordinator/GLM53 | 20 | 2.296 | 2.343 | 3.344 | 20 × 200 |
| Principal/G26 | 20 | 0.640 | 0.609 | 0.797 | 20 × 200 |
| Coordinator/G26 | 20 | 0.555 | 0.532 | 0.641 | 20 × 200 |

No numeric rate-limit or Retry-After header was found among 301 private native
header receipts checked. No sensitive header values or native request identifiers
were printed or copied here. Partial-phase completed-response means can be
biased downward while slower requests remain outstanding. Actor timings are not
reader timings. The single observed 504 is a reliability warning, not an estimate
of a stable incident rate or proof of a particular quota.

## Deadline arithmetic

Planning deadline: 9 November, 11:59 UTC. Reserving six hours for analysis,
figures, report production and validation gives a collection stop at 05:59 UTC.
At 14:51 UTC on 7 November, approximately 39.13 collection hours remained; this
window shrinks while development and registration work continue.

For model/profile m with n calls, mean service latency L and effective concurrent
capacity c, nL/c is a service-time lower bound. It omits phase barriers, scheduling,
backoffs, metadata checks, disk I/O, failures, other users and latency inflation
under load. A sum of these floors is not a wall-clock guarantee.

Q397 has 12,840 main reader calls plus 2,300 actor/influence calls: 15,140 total.
If both types shared the illustrative latency below:

| Mean seconds/call | Readers only, c=2 | All Q397 calls, c=2 | All Q397 calls, c=4 | All Q397 calls, c=8 |
|---:|---:|---:|---:|---:|
| 20 | 35.67 h | 42.06 h | 21.03 h | 10.51 h |
| 30 | 53.50 h | 63.08 h | 31.54 h | 15.77 h |
| 36 | 64.20 h | 75.70 h | 37.85 h | 18.93 h |

These scenarios show why a reader-only estimate understates the risk. They do not
predict linear scaling at increased concurrency.
The later prospective dispatch design also imposes one-second native client
dispatch spacing. With 45,200 total native main calls, that introduces an
approximately 12.56-hour aggregate dispatch floor before other overhead; a
single model's shorter service floor cannot override it.

Ollama must also be forecast: 5,160 DS-off and 12,840 DS-low reader calls share
the same underlying model key and currently the same provider capacity of two.
With DS-off at an illustrative two seconds/call, DS-low at 10, 20 or 30 seconds
implies approximately 19.27, 37.10 or 54.93 service hours respectively. Raising
native concurrency alone cannot solve an Ollama bottleneck. Use actual complete
development reader timings for all eight profiles before selecting main settings.

## Requirements for a prospective amendment

Use a separate module, operational config, protocol and registration. Bind the
unchanged scientific source and every scientific request body/hash, job identity,
cohort, endpoint, output limit, prompt, evidence view and scoring rule. Do not
monkeypatch frozen globals. Retain existing native receipts, terminal failures,
unknown-send holds, global lock, budget reservations and no-retry rules. The
current development and original HF completion drivers must remain untouched.

A separately capped capacity pilot can compare predeclared native concurrency
levels using distinct scripted task-like packets. Select using throughput,
latency, HTTP/usage integrity and deadline feasibility, never verdict accuracy.
All pilot attempts must be retained and excluded from scientific estimates.
Higher offered concurrency may increase latency or errors; it is not a quota
guarantee. Honor a documented Retry-After when available and pause new dispatch
on eligible transient failures; never resend a started observation.

Keep HF's new route and its two-request cap stable. Any Ollama concurrency
increase additionally needs evidence of support for the subscription and a
registered capacity check; do not infer it from a successful request or balance.

Before main registration, calculate provider/model service floors, global-worker
constraints, phase barriers and conservative completion scenarios using the
remaining time. Include calibration, influence, operational overhead and the
paper reserve. If the complete registered design does not fit, decide and
register the operational/workload change before held-out collection. Do not
launch a condition known to stop part-way and later conceal the missingness.

At the time of this memo, no concurrency change or new capacity pilot had been
executed by its author. A separate prospective implementation was authorized for
preparation; its rules still require registration before any calls.
That draft ultimately tests 32 cases each on Q397 and GLM52 at four, eight and
sixteen requests/model (192 native calls), plus six balanced DS-off/DS-low calls at Ollama's documented
three-request Pro limit. Its selection and complete-workload forecast are
specified in `SWARM_LEDGER_DISPATCH_PROTOCOL.md`; this memo is evidence for
investigating the amendment, not an authorization or successful pilot result.
The sixteen/model contingency leaves the native provider total at sixteen and
does not establish a supported provider quota. A stopped eight-load group blocks
further ramp, with every skipped sixteen-load identity retained diagnostically.
