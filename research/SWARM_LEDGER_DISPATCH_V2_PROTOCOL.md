# Prospective main-only scheduling amendment: V2

Status: READY FOR PROSPECTIVE REGISTRATION. No capacity pilot or amended main
collection may run from an unregistered artifact. Freeze and tag this module,
its tests/config, and this protocol
before new capacity calls. Freeze a separate main operational registration after
the declared metadata-only selection and original main scientific registration.

The scientific study remains immutable: identical cohorts, tasks, endpoints,
prompts, bodies, job IDs, labels, parser, scoring and per-row price estimates.
For MAIN, this module changes local scheduling and, conditionally, the declared
peak-equivalent Ollama spending allowance. For the excluded capacity pilot, V2
also corrects the serving-health gate described below. Scientific admission,
normalization and scoring remain unchanged. It never monkeypatches old globals.

## V1 stop and prospective V2 correction

The immutable V1 pilot stopped after 17 terminal native calls; 181 assigned calls
remained unstarted. All 17 had HTTP 200, known usage and matching models. Three
were bounded incomplete responses at 4096 output tokens, with native reason
`max_output_tokens`. V1 incorrectly treated that expected output bound as a
transport-integrity failure. Its 0.18300835 Adaption credits, stopped journals,
registration and excluded status are retained. See
[deviation](SWARM_LEDGER_DISPATCH_DEVIATION.md) and
[metadata snapshot](swarm-ledger-dispatch-v1-stop.json).

V2 registers fresh, distinct excluded identities. It does not retry or relabel V1.
For Adaption pilot serving health only, a response may be completed or incomplete
at exactly the registered 4096-token output bound; the latter requires the hashed
native receipt to show `incomplete_details.reason=max_output_tokens`. HTTP 200,
known usage, no anomaly and the exact allowed model remain mandatory. Such an
incomplete response remains scientifically unadmitted and INVALID under the
unchanged study scorer. Ollama retains completed-only, zero-error eligibility.
No answer correctness or final JSON accuracy enters capacity selection.

All V1 and V2 pilot spending shares the same 10-credit/$0.10 ceilings. Before
new dispatch, replay the exact 17 historical receipts, request commitments,
stopped-driver state and journal hashes. Only this attested bounded-output stop
is excepted; unknown sends, changed history or other fatal stops still block.
A reused Windows PID is accepted only when its current creation time is strictly
after the final driver-state timestamp; missing or ambiguous identity blocks.

## Why and when

The throughput review identifies a deadline risk at two requests per model.
Complete the registered technical/development graph first; verify its driver and
last child are dead and its readers have 256 terminal records. The capacity pilot
uses the same scientific global guard, so it cannot race development collection.
The old HF completion process is independent and must not be modified.

## Capacity pilot and selection

Use 32 distinct scripted full-16-record task-like cases for each of native
Q397 and GLM52, at concurrency four, eight and sixteen using the same cases.
This is 64 calls per candidate and 192 native pilot calls. IDs identify the excluded
pilot condition; they are never main observations or replacements. Alternate
DIRECT/PROCEDURE and canonical/shuffled layouts in fixed cases. A separate six
request neutral Ollama capacity check (three DS-off and three DS-low) tests its
documented Pro limit of three.

V1 and V2 together have estimated caps of ten Adaption credits and $0.10 Ollama;
no HF pilot requests are added. Preserve every started identity and native
receipt. No request retries, replacement cases, tools or persistent memory.
At the full original input/output reservations, all 192 native calls reserve
7.5992064 credits plus the retained V1 cost of 0.18300835, below ten; all six Ollama calls reserve $0.0726912, below $0.10.
Sixteen/model remains bounded by the shared native total of sixteen. It is a
prospective contingency for slower reader workloads, not a provider entitlement.
Each qualifying native candidate needs all 64 assigned terminal records, with at
least 31 of 32 HTTP-200, known-usage, model-matched serving-healthy responses per profile
within the fixed output bound. At most one known eligible gateway/explicit
overload error per profile is tolerated; preserve it without retry. More than
two known errors in a group may stop that group after draining in-flight work.
Alias, capture, unclassified quota, unknown sends and other integrity errors
remain fatal. The six Ollama pilot requests retain zero error tolerance.
The larger pre-data batch reduces warm-up/tail sensitivity in a workload
projected to many thousands of calls. Do not parse
verdict accuracy to select capacity. Record per-profile client elapsed time and
throughput. Choose the healthy, deadline-feasible candidate with the lowest
forecast native critical-service duration, using actual development actor timing,
per-profile pilot reader throughput and pacing/phase constraints; choose the
smallest qualifying level when tied. Aggregate throughput cannot hide a slow reader profile. A partial or
failed candidate is ineligible. Any unresolved start prevents continuation.
A known capacity failure at a higher load may justify a previously completed
healthy lower load. A completed group that is ineligible because two known errors
occur in one profile, without a fatal stop, does not itself forbid the next load.
Any stopped lower native load blocks further native ramp: in particular, a stop
at eight forbids sixteen even when its error is a known capacity failure. A known
capacity stop at eight may skip the unstarted sixteen group and proceed to the
Ollama check, retaining every skipped identity. A known capacity stop at sixteen
may likewise leave a healthy eight or four eligible. Preserve all planned identities
and explicitly record unstarted pilot
IDs. Only explicit overload/eligible gateway failures qualify for this fallback;
authentication, billing, alias/metadata/capture failure, unknown sends or excessive
Retry-After are not capacity evidence and cannot be bypassed.

After selection, main uses native model limit four, eight or sixteen, native provider
limit sixteen, HF provider/model limit two, and Ollama provider/model limit at
most three. Total in-flight ceiling is twenty-one. These are offered client
loads, not a guarantee of provider capacity or linear speedup.
Native calls have a one-second client transport-dispatch spacing gate, preserved
between phases. This is a client scheduling constraint, not a promise about
provider arrival times. Private dispatch/finish events support timing replay;
scientific response shapes and request bodies remain unchanged.

Source and registration anchors use SHA-256 after CRLF-to-LF byte normalization,
matching the LF Git blobs on other platforms. This does not rewrite existing
engineering files. Private native-receipt hashes deliberately remain hashes of
their exact raw file bytes. New operational registrations and selection files
are written with LF line endings; the hash convention is declared in registration.

## Provider conventions and budgeting

[Adaption's SDK](https://docs.adaptionlabs.ai/api/python/) documents asynchronous
clients but no numeric concurrency entitlement was established by the documentation
review. SDK default retries are not used. Main continues to use original request
builders and explicit endpoint/usage checks.

[Ollama's pricing page](https://ollama.com/pricing) documents three concurrent
requests for Pro/PAYG. Its off-peak schedule includes weekends and weekday hours
outside 12:00ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ18:00 UTC. The original conservative peak per-row estimates remain
unchanged. A peak-equivalent cap increase, if needed after development usage
forecasting, must be explicit in the operational config before registration and
allowed only during off-peak collection. No such increase is enabled in the
current draft. Original combined peak-estimate cap is 25.00, of which main is
24.70 and technical/development together are 0.30. If forecasted usage requires
it and the off-peak wallet check passes, selection can declare a combined
peak-equivalent cap of 100.00 and main cap of 99.70. Pilot 0.10 is separate.
The fixed config records the maximum allowed bound before the pilot; the selected
bound is committed in the later selection/main operational registration.
Keep the original remaining-credit floor, fresh balance checks and
all conservative in-flight reserves; invoices remain distinct from estimates.

## Integrity, backoff and cutoff

The executor copies the original safety state machine locally: durable
start-before-send, hashed native receipts, exact native replay, full unknown-send
holds, global locking, fatal-stop persistence, cost reconciliation and immutable
scientific plans. Main requires both original scientific and new operational
registrations. Its existing journals retain their original shapes and body
commitments. Operational source/selection provenance belongs in a separate
companion artifact, not extra fields inside strict scientific exports.

Honor valid Retry-After for eligible 5xx/explicit-overload responses, waiting at
least 15 seconds for Adaption 502/503/504, or 60 seconds for all other eligible
transients, and any valid longer requested delay up to 900 seconds. A delay
beyond the registered bound causes a safe stop instead of
ignoring the provider's instruction. The prospective V2 base-wait amendment is
explained below; no-retry rules remain.
All failure records remain part of accounting and scientific denominators.
An operator can request a soft stop by creating a literal `STOP` file in the
current phase directory. This stops further submissions, drains already
submitted requests and preserves all unstarted identities. It does not delete
or override a fatal `stop.json`, waive an unknown send, or authorize a restart.
Drain paths immediately exit; later entry reconstructs costs from durable
receipts rather than reusing the terminating process's in-memory counters.
The original scientific source retains its 256 known-gateway threshold. This
prospective main-only executor explicitly allows up to 1,024 classified gateway
or explicit-overload responses per main phase, because a serving-healthy pilot rate
as high as one per 32 on the large readers could otherwise exhaust 256 before
finishing the fixed workload. Pilot groups remain limited to two such errors,
with at most one per profile for eligibility; Ollama pilot tolerance remains zero.
The 1,024 allowance is neither a spending target nor an assurance about future
error rates. Unknown sends, authentication, billing, unclassified quota, alias
and capture failures remain fatal. Finite request counts, budgets, no-retry rules
and all scientific scoring/denominators remain unchanged.

Every eligible transient persists a shared private cooldown, including a tolerated
error on the last response of a completed group. Subsequent phases and queued
client dispatch gates honor that deadline. Historical HTTP-date Retry-After
intervals are measured against the response Date header or recorded receipt-time
metadata, rather than today's clock. The full-workload forecast includes observed
transient frequency and global backoff duration before its safety multiplier;
larger error allowance cannot hide its time cost.
The shared private checkpoint is the cross-process carrier for MAIN cooldowns;
it must not be deleted to evade a wait. Pilot stop files additionally retain
their cooldown metadata. The immutable scientific config's historical 60-second
base remains unchanged on disk; the V2 local execution rule and forecast use
15 seconds for future native 5xx and 60 seconds for other eligible transients.
In complete
admitted development data, HTTP error bodies never supply trustworthy usage;
nontransient unknown-usage failures prevent this gate from passing. The
forecaster therefore requires unknown-usage and eligible-transient counts to
match, and rejects an input that violates that source invariant.

Before main starts, forecast all actor, reader, calibration and influence work,
including the shared DS-off/DS-low model limit. Apply a 1.25 time safety multiplier
and an additional thirty-minute overhead allowance. No selection uses development
accuracy. Collection stops no later than 9 November 2026, 05:59 UTC, reserving six
hours before the stated submission deadline for analysis, figures, report and
validation. A time cutoff or provider failure does not make an incomplete
condition complete; report it honestly and preserve every previous terminal.

The wallet gate deliberately requires the entire interval from forecast
generation through the collection cutoff to be off-peak. After the shared
wallet check accounts for known scientific and V1/V2 pilot spending, available
allowance must be strictly greater than `projected MAIN peak-equivalent Ollama
cost / 2 + 5.00 + 0.10`: the documented off-peak estimate, retained five-dollar
floor and an additional conservative pilot reserve. This whole-window gate
can reject schedules that might work with deliberate weekday pauses; no such
pause schedule is registered here. Estimates and reserves are not invoices.

## Prospective response-specific cooldown

Before the V2 pilot, register a 15-second base cooldown only for Adaption HTTP
502, 503 or 504 responses. Explicit-overload 429 responses and all other providers
retain 60 seconds. Honor any valid larger Retry-After value, up to the registered
900-second bound; invalid or excessive values stop collection. Cooldowns remain
global, persist across phase boundaries, and use the latest not-before timestamp
when in-flight responses finish together. Historical resume starts conservatively
at 60 seconds. These waits govern dispatch of distinct future identities; retries
remain zero and failed observations remain in the dataset.

The [official Python SDK documentation](https://docs.adaptionlabs.ai/api/python/)
describes short exponential backoff for eligible transient failures. Fifteen
seconds is a conservative client-chosen operational wait, not a documented
provider quota or entitlement. The prospective forecast uses this new rule for
future native 5xx responses while retaining historical DEV timing metadata.
All V1 files and prior scientific response rules stay unchanged.

## Fixed gateway-allowance feasibility gate

The forecast sums projected eligible transient terminals across all providers for
each complete main phase. A candidate is gateway-feasible only if every phase
projects at most the unchanged 1,024-terminal allowance. Recompute that flag from
the provider counts; do not trust a stored boolean. Keep clock feasibility
separate. Selection requires serving health, clock feasibility and gateway
feasibility together, retaining other candidates as diagnostics. If none passes,
do not start MAIN. These projections are expectations, not guarantees: realized
errors may still trigger the registered runtime stop. The allowance and budgets
are not increased to make a candidate pass.

The V2 optional Ollama ceiling is prospective: complete DEV shows that conservative
peak-priced projections can exceed 49.70 despite remaining affordable at the
published off-peak prices. The conditional 100.00 combined peak-equivalent bound
includes the original 0.30 engineering allocation; MAIN may use at most 99.70.
Original scientific and V1 ceilings remain immutable. Activate the extension only
if necessary for the full registered workload and a fresh private wallet check
covers projected off-peak charges, the five-dollar floor and separate pilot cap.
It authorizes no top-up, plan purchase or spending merely to exhaust credits.
