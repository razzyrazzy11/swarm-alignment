# Prospective paced continuation with a narrow provider wait

This is a new operational continuation, not an amendment to existing frozen
sources or registrations. No STOP, freeze or launch follows merely from preparing
this module. Independent review, preliminary timing headroom, an actual controlled
predecessor drain, a fresh exact-complement cost/time gate and committed/tagged
collection and analysis registrations precede any new inference.

## Why this bounded change is being considered

The current rate-aware batch has retained repeated precisely classified native
rate-limit429s, and its registered provider-rate recovery pauses all providers.
The completed MAIN HF profiles remain complete. Adaption waiting can therefore
consume time needed by the shared Ollama readers even when those readers have
healthy serving. These are delivery observations, not reasoning outcomes or
permission to replace failed identities. No unfinished answer accuracy is used.

The proposed client minima are **3.2seconds per Adaption model** and **1.6seconds
between all Adaption client-send clock claims**, both stricter than the previous
one-second global native rule. They are conservative operating choices, not a
claim about documented provider RPM/TPM limits, server arrival times or guaranteed
429 reduction. Actual provider traffic may be governed by other shared/token
limits. Forecasts include these pacing loads and do not credit avoided429s.

## Pacing and eligibility

Immutable profile descriptors and exact active/pending counters retain the
existing sorted first-eligible rule, with a newly registered clock-readiness
predicate. Native clocks are atomically claimed inside the transport immediately
before its single POST. The shared native global checkpoint is carried forward;
a new private model-clock map is bounded, finite and restricted to configured
native models. Clock locks are released before sleeping/rechecking. A blocked
model cannot hold the pacing lock while another model becomes eligible.

The dispatcher considers native next-ready clocks and reevaluates active futures
with a bounded next-readiness timeout of at most one second. An empty completion
set is normal; it does not release a reservation or duplicate a request. This
prevents a long Ollama response from delaying reconsideration of newly eligible
native work. Body construction, normalization, model routes, sampling and API
POST retry behavior are unchanged. Client clock claims are not a guarantee of
provider-side request arrival timing.

The07:56UTC boundary remains last **scheduler admission**, before its start record
and future submission. Already admitted requests may complete their finite
pacing and drain afterward; the worker does not throw solely because this
scheduler boundary passed, which could otherwise create an unresolved started
identity without a POST. The08:00UTC drain target reserves the180second request
timeout plus60seconds margin but is not a hard wall-clock guarantee. The official
submission deadline remains9November11:59UTC, leaving a targeted3h59 for strict
validation, report integration and actual PDF visual review.

## Narrow Adaption-rate pause; other rules remain global

Only the already registered exact Adaption rate429 classifier creates a
provider-specific hold. It still requires the exact JSON type/code/null param,
positive bounded numeric Retry-After and matching explicit message interval,
without funding/quota/authentication markers. Its request remains terminal and
keeps the full unknown-usage reservation. All historical rate/error counters and
costs carry forward unchanged.

For that one class, pause only unstarted Adaption work, drain in-flight Adaption
requests, and keep otherwise eligible Ollama work admissible during the cooldown.
Do not mark the global connectivity gate failed or overwrite the legacy global
cooldown for this provider-only event. Before Adaption resumes, require two
Adaption-only healthy catalog GETs at least15seconds apart, followed by the
**literal original full catalog check**. That check verifies the native model
set, HF route/status/structured-output capability/prices and Ollama digests;
it does not establish live native pricing. Missing models or changed prices,
authentication/funding, malformed replies and capture failures remain fatal.

The provider-health operation is deliberately synchronous. The normal healthy
path introduces a brief roughly15second dispatcher barrier; persistent metadata
unavailability can block submissions longer within its registered bounded wait.
Thus this change does not promise uninterrupted Ollama dispatch throughout
metadata recovery. Already active requests are retained and allowed to finish.
Non-rate server failures or network faults during a provider probe re-enter the
global readiness gate. All other500/502/503/504/HF/connection behavior, the daily
router blackout and the100-completion global drain/check remain global.

The existing60/120/240/480backoff, maximum eight consecutive failures and900second
provider admission episode remain. Exceeding them stops collection rather than
quarantining a reader or relaxing a guard. Within this new paced continuation, provider hold, episode start and streak
state persist across phase handoffs, so changing phases does not erase waiting
or reset an unresolved episode. Clean known-usage/non-anomalous HTTP200 transport
completions reset the corresponding episode; this is not answer-accuracy scoring.
Safe availability metadata includes provider, class, count and timing, never
credentials, native IDs, account balances or raw outputs. The previous legacy
global cooldown is inherited at startup rather than retroactively reinterpreted.

## Controlled predecessor admission and seven-batch union

The current rate collector keeps running until the root operator separately
requests its existing cooperative STOP. Admission requires actual stopped/readers
state, nullable child or proved terminated child, a STOP marker, no fatal stop or
capture-failure journal, all started identities terminal and unique, dead owned
processes, and absent phase/global locks. A coincident fatal guard cannot be
bypassed as a scheduling change. When the old availability record is waiting
with a remaining episode budget, its actual driver terminal timestamp must be
strictly earlier than the availability publication time plus that remaining budget.
An episode already exhausted at the old terminal stop is rejected even if a
STOP marker exists. The comparison uses the old stop time, not the later
engineering/registration time; an originally live episode does not become a
fatal historical fault merely because prospective review takes time. The old
remaining global cooldown must still elapse and fresh all-provider readiness
is required. The new amendment explicitly starts a fresh live admission episode
only on its first newly recognized failure; all old failure counters, streaks
and costs remain carried forward. Every retained failed predecessor row must pass
the precise existing server/rate/connection classification and full ledger
reconstruction; all failures and full reservations stay in the evidence.

The union is original MAIN, v1, v2, v3, efficient-v1, rate-v1 and paced-v1.
The new folder is `runs/swarm-ledger-paced-v1-main`. Old archive metadata, native
inventories and actual driver states are immutable commitments. Full original
plans, body hashes, normalization, host actions and costs are replayed. Batches
have disjoint starts and exactly one terminal per start. The remaining reader,
calibration and influence counts/descriptors are computed only after the actual
drain; no stale complement is hardcoded. The new forecast must match all counts,
descriptors and `pacing_minima_seconds={native_global:1.6,native_model:3.2}`
serialized as exact decimal strings.

Global active ceiling8, native provider ceiling8, all model limits2, shared HF/O
limits2, phase/provider/combined/native-class caps and wallet floor remain.
Server500total32, connection32 and1,024-per-phase known-server allowances are
carried forward, not reset. The04:55–05:05UTC router pause and07:56admission cutoff
remain. No endpoint switches, dropped conditions, shorter responses, successful
replacement requests, spending changes or new training are introduced.

## Validation, interpretation and sources

Offline tests cover client clock floors/persistence, no lock-held waits, a ready
model passing a waiting model, dispatch reevaluation before a slow other-provider
completion, scoped rate waits versus global503and metadata barriers, seven-batch
union, controlled-stop/fatal rejection, unchanged bodies/caps, retained failed
reservations and exact forecast commitments. Synthetic fixtures are engineering
tests, not additional empirical results.

Strict complete seven-batch replay, actual termination proofs, original HF
recovery, figure provenance and sensitivity precede report authoring. Earlier
iterations and scripted calibration remain separate. The report will disclose
pacing and recovery amendments without treating HTTP200 as scientific validity
or serving failures as reasoning failures. The Track4 question remains evidence
acquisition, verdict delivery, or use of sufficient evidence. Existing queued
reviews and final PDF inspection remain outstanding until actually performed.

- RFC9110 non-idempotent request and waiting conventions:
  https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2
  https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3
- RFC6585 explains429 without establishing a particular provider quota:
  https://www.rfc-editor.org/rfc/rfc6585.html#section-4
- Python futures completion and timeout semantics:
  https://docs.python.org/3.12/library/concurrent.futures.html#concurrent.futures.wait
- Apart guidelines/Judging and results:
  https://apartresearch.com/sprints/swarm-alignment-2026#guidelines
- 20-rules-of-learning guides the concrete bottleneck→bounded change→test→limit
  explanation; it is not empirical evidence or a judging-score guarantee.
