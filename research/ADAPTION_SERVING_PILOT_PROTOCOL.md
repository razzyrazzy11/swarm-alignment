# Excluded post-primary Adaption serving feasibility pilot

Register `adaption-serving-pilot-v1` before any pilot inference. This is an
engineering feasibility study, not another MAIN condition and not a repair or
replacement for earlier failed requests. The640-block six-reader comparison is
the priority. Pilot collection is prohibited until the actual canonical MAIN
continuation, HFv3 continuation AND offline router-resume postprocessor are all
complete with creation-time-aware process-termination proof. Other collector
locks block admission. Existing archives, endpoints and scientific scores stay
unchanged. No automatic serving-mode promotion is permitted.

## Fixed design and population

Sixteen requests: Q27/Q397 by synchronous JSON/SSE by assigned concurrency cap1/2
by two fresh fixed synthetic reporter-like inputs. Exact instructions, fake
policies, peer notes, identities, bodies and order are embedded in the source and
copied into the registration. They use no failed MAIN prompts, live actor calls
or observed semantic answers. The two fake note patterns are both-peers-claim-done
and one-peer-claims-refusal. They exercise output-format feasibility; correctness
of the claimed_done field is not used to select a mode.

Use the original shared actor instructions, model aliases, temperature0,
max_output_tokens4096, tools empty, tool_choice none, memory false and store
false. The transport comparison changes only stream false/true. Native final
responses are normalized with the frozen original normalizer. These are two
scripted toy inputs with reporter-shaped fields, not a representative sample or
exact length match for all MAIN contexts. Successful delivery on them does not
establish success on the MAIN workload or equal model behavior across transports.

Seed730119 shuffles four model/concurrency groups and each group's four
input/mode jobs. Groups run sequentially; requests within a group use its cap.
The two modes deliberately share the same capped group and can affect queueing.
Concurrency is an assigned maximum, not a promise of two simultaneous calls at
every instant. Submitted-active counts are recorded. Global maximum is two;
native starts are at least one second apart. No pilot traffic competes with the
primary collection. Default SDK retries are not used; every identity is attempted
at most once, even after HTTP504 or a broken stream.

## Serving records and operational endpoints

All calls use the documented Adaption Responses endpoint. Freeze a read-only
HTTP200 catalog snapshot with the two required aliases, exact policy, source/test
hashes, parent registration hashes, earlier pilot baselines and complete plan.
No model substitution or unsupported background=true workaround is allowed.
SSE is parsed as bounded events; only a validated authoritative terminal response
object supplies final text/model/usage. A completed/incomplete/failed/cancelled
terminal event can end the stream without waiting for connection EOF. Already
received contradictory terminal events are rejected; future unread bytes are
not claimed inspected. HTTP200, a text delta or [DONE] alone is not successful
completion. Partial output and raw stream are retained privately, key-scrubbed;
they are never promoted into a completed answer or guessed token usage.

Before submission, fsync an attempt with identity, body hash and full reservation.
After a terminal, fsync private receipt and normalized delivery metadata. Record
HTTP status, event/byte timing, final latency/status, known usage, model match,
format validity, diagnostics and receipt hash. Preserve all failures, including
unknown provider-side completion, with full unknown-cost reservations. Bound
raw bytes to2MiB and events to10000. No raw answers, reasoning, headers, keys or
native provider IDs appear in the public aggregate report.

Operational endpoints are delivered terminal, HTTP504, native completion, known
usage, returned-model match, task JSON validity and their conjunction, plus
latency and SSE event timings. Record all terminal latencies; success-conditioned
latencies must remain explicitly conditional. Do not select on verdict accuracy.
Every one of eight matrix cells has only two fixed inputs. Report counts and
descriptive latencies, with no inferential effect claim, general reliability
estimate, statistical-significance claim or automatic configuration change.
A separately registered confirmation is needed before broad adoption.

## Bounds, priority and stop rules

The new pilot's total full reservations must fit1Adaption credit. Retain the
earlier two excluded pilots'0.81430880credits and the original cumulative
10credit excluded ceiling. Known usage uses original token rates; missing usage
retains the full reservation. These are client estimates/holds, not invoices.
No automatic top-up or inference retry is introduced.

Primary cutoff remains9November05:59UTC. This separate post-primary pilot has a
9November09:30UTC cutoff, leaving2hours29minutes before the sprint's11:59UTC
submission deadline. The complete45minute wall budget must fit before that
secondary cutoff or the pilot is explicitly deferred with no inference. Shared
connectivity gating enforces the04:55–05:05UTC router blackout and two healthy
catalog checks15seconds apart, bounded by a900second pause. Authentication,
funding, TLS, capture-integrity, unknown transport failures and model substitution
halt; ordinary bounded gateway/stream-validation failures remain pilot outcomes.
HTTP429 waits at least60seconds;502/503/504 wait at least15seconds. Honor valid
Retry-After across groups up to900seconds; larger/invalid values stop instead of
silently shortening the server's delay. Operator STOP prevents new dispatch and
drains already submitted calls.

Per-request socket/stream budget is180seconds and the soft whole-pilot budget is
2700seconds. Python DNS/getaddrinfo and some blocking OS operations cannot be
reliably preempted by urllib's timeout. Therefore collection requires the actual
root-owned supervisor `runs/adaption-serving-pilot-driver/state.json`, matching
parent/child PIDs and an aware UTC hard-watchdog deadline no later than45minutes
or09:30UTC. The watchdog may terminate ONLY its owned pilot child, never primary
processes. It records the real termination and leaves fsynced attempts intact;
unresolved sends retain full reservations and are not repeated. Analysis reports
partial/interrupted coverage with actual counts, never fabricates terminal rows
or a COMPLETE summary. A killed child's stale owned lock may be recognized only
with its exact dead PID proof; no other owner's lock is removed.

## Release and interpretation

Use `python -m experiments.adaption_serving_supervisor` for the registered queue
and hard watchdog. Its tracked source and tests are bound in this pilot's source
registration; there is no untracked private-only watchdog dependency. The queue
waits for the primary completion proofs and calls this one-shot collector only
when its full secondary budget fits. It records actual pilot_child_pid separately
from any later analysis subprocess PID.

Normal analysis requires the actual pilot child to have ended and strict request,
receipt, normalization, cost, identity and summary checks. Report missing cells
and unresolved requests explicitly. Native-normalization and aggregate replay
require the private archive; hash commitments alone do not provide independent
public reconstruction. Existing primary outputs are never overwritten or pooled
with the pilot. The report explains implementation feasibility, not swarm intent
or a causal improvement in monitor reasoning.

Primary references: [Adaption SSE/API](https://docs.adaptionlabs.ai/api/resources/responses/methods/create),
[SDK streaming and retry defaults](https://docs.adaptionlabs.ai/api/python),
[HTTP retry semantics](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2),
and [Apart judging guidelines](https://apartresearch.com/sprints/swarm-alignment-2026#guidelines).
The project uses20-rules-of-learning for concrete examples, clear distinctions
and connected explanations, not as evidence for serving or scientific effects.
