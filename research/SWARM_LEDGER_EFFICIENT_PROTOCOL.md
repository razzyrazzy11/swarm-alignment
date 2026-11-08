# Prospective eligibility-cache continuation

This amendment changes local eligibility bookkeeping, not the scientific design
or provider capacity. It must be committed, frozen, tagged and pushed before any
new inference. The live predecessor is not modified by this implementation. The
root operator will separately request its existing cooperative STOP, let all
started work drain, and verify actual supervisor/child termination before the
new collector can be admitted. It does not kill processes, remove locks, retry
requests, drop a condition or shorten a model response.

## Why the local repair is useful

The predecessor repeatedly walks a large sorted pending list while every
remaining provider/model key is already at its capacity. Its eligibility test
also reloads profile configuration for active jobs on each candidate. Synthetic
saturated-queue inspection identified avoidable local scheduling overhead; this
is not an empirical model result or evidence of reasoning failure. A local
performance improvement cannot guarantee provider latency or the deadline.

The new collector caches only immutable profile-to-provider/model descriptors,
counts pending jobs per provider/model key and counts active requests per
provider. When no pending key can admit another request at the existing limits,
it stops before copying/scanning the pending list. It also stops the current
scan once all remaining keys are capped. Zero-count keys are ignored. Completion
and drain paths decrement active-provider counts exactly once. No queue is
reordered: eligible jobs retain the original sorted list and first-eligible
selection rule under the same completion, cooldown and readiness events.

Bulk plan/complement construction additionally uses the existing verified
configuration context. Its entry and exit checks bind unchanged source settings;
it avoids repeated file parsing and creates no alternative configuration. All
six request-body constructions, the original body builder, response normalizer,
one-second native dispatch spacing and recovery transport methods are unchanged.

## Immutable history and exact complement

The five-way union is original MAIN, router continuation v1, server continuation
v2, provider continuation v3 and this efficient continuation. Each old archive,
native receipt inventory and actual stopped-driver state is hash-bound. Original
full phase plans remain authoritative. Starts must be unique, disjoint and have
exactly one terminal, with body/receipt/host-action/cost replay unchanged. All
failed terminals keep their identities and full unknown-usage reservations.

V3 must actually be stopped in readers, have the controlled STOP marker and no
fatal `stop.json`, have no live owned parent/child or collector lock, and have no
unresolved started request. A nullable child is legitimate only because the
frozen supervisor waited for that child before clearing it. No artificial exit
code or PID is written. A coincident capture/funding/integrity failure cannot be
bypassed by the performance amendment.

The new folder is `runs/swarm-ledger-efficient-v1-main`. The remaining reader,
calibration and influence counts and exact pending-descriptor commitments are
computed after the cooperative drain, never hardcoded from a stale snapshot.
The new forecast must match every count and descriptor. Every new request is in
that exact never-started complement; a previously failed request is never resent.
Freeze and analysis-admission registration are separate, prospective and required
before new calls. Actual source and ancestry commitments must verify at launch.

## Preserved scientific and operational controls

The 640 independent blocks, six readers, four requested checkpoints, three model
families, procedures, views, calibration and controlled influence remain fixed.
No endpoint, decoding, evidence builder, support oracle, scoring or bootstrap is
changed. All earlier effects remain separate; this does not pool experiments or
select favorable results. No unfinished answer accuracy is inspected for this
engineering repair.

Global active ceiling remains eight, native provider ceiling eight, native model
limits two, shared HF and Ollama limits two, and native starts one second apart.
Every provider, phase, combined, native-class and wallet-floor cost guard carries
all prior spending/reservations exactly once. The verified v3 HF429 availability
classifier, negative funding/quota/rate markers, bounded backoff, read-only health
and pinned route/model/pricing checks are unchanged. HTTP500 total32, per-phase
known-server allowance1024 and connection allowance32 remain. The900-second
live availability episode still bounds admission of another POST; draining and
blocking read-only checks may finish later but cannot authorize a late POST.
No heartbeat restarts a stopped collector.

The router blackout remains04:55–05:05UTC, two healthy catalog cycles are at
least15seconds apart, bounded waits/cooldowns remain, and the collection cutoff
is still9November05:59UTC. Deadline projections are conditional, not guarantees;
the root forecast need not credit an unmeasured performance gain. The excluded
serving pilot remains blocked/unrun and requires separate admission for requeue.

## Validation and paper consistency

Offline tests compare fixed and randomized completion streams against the
predecessor selection rule, verify active/pending counter identities and all
caps, saturation checks without profile reloads, zero-pending-key behavior,
unchanged request bodies/transport/policy, duplicate and unresolved rejection,
failed full reservations, bounded recovery and dynamic forecast commitments.
Synthetic checks are engineering evidence, not additional empirical observations.

Actual completed collection must pass strict five-batch scientific replay,
original HF completion proofs, figure provenance and registered sensitivity
before authoring findings. Final report integration, actual PDF pagination and
visual review, and queued investigations remain outstanding until performed.
The paper will disclose all collection batches, retained serving failures and
this prospective bookkeeping-only repair. Its central Track4 question remains:
which part of oversight needs repair—evidence acquisition, verdict delivery, or
use of sufficient evidence?

## Primary conventions

- Python concurrent futures documents futures/completion and executor cleanup:
  https://docs.python.org/3.12/library/concurrent.futures.html
- Python context-manager semantics support bounded entry/exit verification:
  https://docs.python.org/3.12/reference/compound_stmts.html#with
- RFC9110 non-idempotent-request semantics explain preserving failed identities
  rather than retrying an ambiguous POST: https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2
- Apart guidelines/Judging and results: transparent empirical accounting and
  clear claims support execution quality and presentation; no score is promised.
  https://apartresearch.com/sprints/swarm-alignment-2026#guidelines
- 20-rules-of-learning is used editorially: identify the concrete bottleneck,
  explain one bounded repair, then connect each invariant to its test and limit.
  It supplies no scientific evidence or authority to alter registered outcomes.
