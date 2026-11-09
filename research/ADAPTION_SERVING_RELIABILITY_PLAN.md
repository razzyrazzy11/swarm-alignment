# Improving Adaption serving without changing the research question

Operational review, 8 November 2026. Current frozen collection continues unchanged.
No new inference, failed-request retry, model substitution or serving-mode change
was made for this review. The accompanying `adaption-serving-diagnostic.json`
contains a timestamped posthoc metadata checkpoint, not final study results.

## Diagnosis: a received timeout response, not the router incident

The captured Adaption HTTP504 responses arrive at approximately60.3seconds across
several models and phases. In the receipt sample examined during this review,
85 MAIN/recovery reporter504s had one identical error-body hash and the phrase
`gateway time-out`. No response bodies, native IDs, headers or credentials are
published here. A local HTTP-proxy environment variable was not set, which does
not rule out every intermediary or establish the exact gateway responsible.

This pattern strongly suggests a roughly60-second deadline somewhere along the
serving path. It does not identify the gateway hop, prove queue congestion or
establish whether provider-side generation continued after a504. The client
timeout is already180seconds, so merely increasing that timeout would not extend
a gateway deadline. These actualHTTP504s differ from the seven generic transport
failures aligned with the confirmed router reset.

The initial metadata checkpoint showed Q397 reporter23/80 HTTP504s in DEV,
28/200 in the stopped MAIN prefix and15/77 in the early continuation. Q27 had
18/424 and17/99 in those two MAIN batches; GLM53 had5/488 and0/152. Gemma26B
had0/640 reporter504s in the original MAIN batch. These partial/time-separated
counts are descriptive, not controlled evidence that time of day or a particular
concurrency setting caused the difference. Use the JSON checkpoint's later exact
denominators when quoting its groups; never combine mismatched snapshots.

## Preserve the useful experimental surface

Y's bounded host actions are already recorded for all2,560 assigned trajectories.
Reporters supply untrusted notes, not new host actions. A failed reporter is
retained as an invalid/missing note. The MAIN reader grid uses Gemma26B, Gemma31B,
HF Llama text/schema and Ollama DeepSeek off/low, not Q397 or Q27 readers.

The priority is therefore the full640-block, six-reader comparison of acquisition
and sufficient-evidence reasoning. A failed note must remain visible in delivery
accounting, but does not by itself prevent constructing the authentic host records
for the same trajectory. No failure should be called successful reasoning, dropped
to improve a score, or replaced by a more favorable fresh answer. Repeated readers,
transport experiments and extra batches do not create additional independent n.

Current dispatch already limits native concurrency to two per model and eight
globally/provider, spaces native starts, waits after gateway errors, and honors
bounded Retry-After. More credit and a larger failure allowance alone do not
repair a gateway timeout. Lower output caps, shorter prompts, reasoning changes
or model replacement alter the scientific condition and are not silent fixes.

## Ranked fixes and what would count as evidence

1. **Provider-side timeout/route correction is the cleanest remedy.** Prepare a
   sanitized support packet with endpoint, model aliases, UTC batch ranges,
   concurrency, client timeout, error-body hash and latency distributions. Ask
   whether a synchronous upstream deadline is60seconds, whether it can be raised,
   and whether the documented SSE route uses a different timeout path. No message
   has been sent; contacting another party requires the user's instruction.
2. **Test lower concurrency against SSE streaming in a separate serving pilot.**
   Use fresh excluded synthetic reporter-like inputs, never failed MAIN identities.
   Match generation settings and input lengths; vary only one transport/scheduling
   factor per comparison. Streaming may avoid a buffered-response timeout but
   might still hit an upstream first-token/overall deadline. It is a candidate
   requiring empirical validation, not a proven fix.
3. **Promote a serving change only after a prospective amendment.** Preserve all
   old failures and batches. If a different concurrency or streaming path improves
   usable delivery, bind its request bodies, final-event parser, usage accounting,
   concurrency, transport label and stopping rules before collecting new study
   data. Apply a rule to all remaining eligible requests, not only known failures.
   Keep comparable modes recognizable in the paper; do not claim identical model
   behavior solely because temperature and alias match.
4. **If time becomes the bottleneck, consider a block-readiness pipeline.** The
   current protocol serializes reporters before readers. A separate prospective
   scheduler could overlap reader work for fully ready four-arm blocks while the
   reporter tail finishes, under one shared provider/global capacity controller.
   It must still include every640 block, retain failed notes and reconstruct exact
   packet/body hashes. Selecting only successful or fast blocks would bias the
   comparison. This is a wall-clock option, not a gateway fix, and is not inserted
   into the running frozen phase order.

## Concrete bounded pilot proposal, not yet registered or run

Start with Q27 and Q397; retain a stable Gemma delivery control in a confirmation
stage if needed. The initial engineering matrix is two affected models times
two modes (synchronous JSON/SSE) times two concurrency levels (one/two per model)
times two repetitions:16requests. Use two fresh prespecified synthetic inputs,
balanced crossover schedules with disclosed seeds, and match every generation
parameter including the4,096-token cap. The small initial matrix can establish
support/parser feasibility, not a reliable effect size or broad promotion claim.

Predeclare operational outcomes: terminal delivery, HTTP504, complete final event,
known usage, returned-model match, parseable final task format, time to first event
and time to final result. Do not select on audit-verdict correctness. Preserve all
partial streams and failures privately with sanitized public metadata; partial
text is not a completed response. Bound wall time, bytes, requests, polls and total
token-rate reservations. Check a one-credit subcap against the remaining
excluded-diagnostic budget and actual full reservations before freezing it.
The pilot is not yet registered or scheduled.

Run only in an explicitly reserved capacity window or under an amended shared
dispatcher; do not add competing calls to the current experiment's provider/global
ceilings. A follow-up confirmation should have a prespecified sufficient number
of independent cases and decision rule before any broad switch. Engineering
results stay separate from the scientific primary. If there is no clear serving
improvement, finish the existing comparison and report reliability as a limitation.

## Sanitized provider-support draft, not sent

We are running bounded synthetic-data research through POST/api/v1/responses.
Several synchronous calls return HTTP504 at approximately60.3seconds despite a
180second client timeout. Affected aliases include qwen3.5-397b and qwen3.8-27b;
the former also failed23/80 DEV reporter calls, while the three other DEV worker
profiles had no reporter504s. Later MAIN failures affect multiple aliases. These
are separate from a known local router interruption at05:00UTC on8November.

Requests use temperature0, max_output_tokens4096, no tools, tool_choice none,
agentic_memory false and store false. Native concurrency is limited to two/model
and eight/provider/global, with start spacing, gateway backoff and no inference
retries. We retain every failed attempt rather than replacing it. Could you
confirm whether this route has a60second upstream deadline, whether an increased
deadline is supported, and whether stream=true uses a different timeout path?
We also need to know whether full final response status/model/usage is supplied
for these aliases in the terminal SSE event. We can provide sanitized timing and
error-body hash aggregates; no real-user data or credentials are involved.

## Primary-source constraints

- [HTTP RFC9110,504](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.6.5)
  defines the gateway's failure to receive a timely upstream response. It does not
  establish that generation never ran. Section9.2.2 cautions against ambiguous
  non-idempotent retries; the study retains zero inference retries.
- [Adaption's Responses create reference](https://docs.adaptionlabs.ai/api/resources/responses/methods/create)
  documents `stream` as SSE. It also states that only `background:false` is
  accepted, so a generic OpenAI-style background/polling workaround is not a
  documented option here. Storage defaults to false and requires explicit
  retention; current bodies use `store:false` and the failed requests have no
  usable response IDs for retrieval. Storage would be a new disclosed mode, not
  recovery of these existing failed identities.
- [Adaption's Python SDK](https://docs.adaptionlabs.ai/api/python) documents SSE,
  including a Q397 example, and default automatic retries. A new client must
  explicitly disable those retries; changing from synchronous to an async Python
  client alone does not change the provider's serving deadline.
- [Apart's guidelines and Judging and results](https://apartresearch.com/sprints/swarm-alignment-2026#guidelines)
  favor clear, well-executed research with substantive findings. Completing the
  matched diagnostic comparison with honest reliability denominators serves that
  goal better than adding uncontrolled calls or hiding unavailable results.

The explanation follows the project's20-rules-of-learning editorial convention:
concrete failure, distinct mechanism, evidence limits, then controlled action.
It is not evidence that a particular serving change will work or score higher.
