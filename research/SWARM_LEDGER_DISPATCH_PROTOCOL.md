# Prospective main-only scheduling amendment

Status: READY FOR PROSPECTIVE REGISTRATION. No capacity pilot or amended main
collection may run from an unregistered artifact. Freeze and tag this module, its tests/config, and this protocol
before new capacity calls. Freeze a separate main operational registration after
the declared metadata-only selection and original main scientific registration.

The scientific study remains immutable: identical cohorts, tasks, endpoints,
prompts, bodies, job IDs, labels, parser, scoring and per-row price estimates.
This module changes local scheduling only, with an optional explicitly declared
peak-equivalent Ollama spending allowance. It never monkeypatches old globals.

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

The pilot has separate estimated caps of ten Adaption credits and $0.10 Ollama;
no HF pilot requests are added. Preserve every started identity and native
receipt. No request retries, replacement cases, tools or persistent memory.
At the full original input/output reservations, all 192 native calls reserve
7.5992064 credits, below ten; all six Ollama calls reserve $0.0726912, below $0.10.
Sixteen/model remains bounded by the shared native total of sixteen. It is a
prospective contingency for slower reader workloads, not a provider entitlement.
Each qualifying native candidate needs all 64 assigned terminal records, with at
least 31 of 32 HTTP-200, known-usage, model/serving-admitted responses per profile
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
outside 12:00–18:00 UTC. The original conservative peak per-row estimates remain
unchanged. A peak-equivalent cap increase, if needed after development usage
forecasting, must be explicit in the operational config before registration and
allowed only during off-peak collection. No such increase is enabled in the
current draft. Original combined peak-estimate cap is 25.00, of which main is
24.70 and technical/development together are 0.30. If forecasted usage requires
it and the off-peak wallet check passes, selection can declare a combined
peak-equivalent cap of 50.00 and main cap of 49.70. Pilot 0.10 is separate.
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
least 60 seconds or the valid longer requested delay, up to 900 seconds. A delay
beyond the registered bound causes a safe stop instead of
ignoring the provider's instruction. Existing backoff and no-retry rules remain.
All failure records remain part of accounting and scientific denominators.
The original scientific source retains its 256 known-gateway threshold. This
prospective main-only executor explicitly allows up to 1,024 classified gateway
or explicit-overload responses per main phase, because an admitted pilot rate
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

Before main starts, forecast all actor, reader, calibration and influence work,
including the shared DS-off/DS-low model limit. Apply a 1.25 time safety multiplier
and an additional thirty-minute overhead allowance. No selection uses development
accuracy. Collection stops no later than 9 November 2026, 05:59 UTC, reserving six
hours before the stated submission deadline for analysis, figures, report and
validation. A time cutoff or provider failure does not make an incomplete
condition complete; report it honestly and preserve every previous terminal.
