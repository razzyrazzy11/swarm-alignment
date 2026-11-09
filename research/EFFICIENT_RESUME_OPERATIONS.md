# Prospective eligibility-efficiency amendment

The current six-reader study is healthy, but a synthetic operational benchmark
identified avoidable dispatcher CPU work. With20,000 pending descriptors and
six active requests saturating every remaining provider/model key, the literal
eligibility loop spent1.50–1.62seconds (1.09–1.23CPU seconds) finding zero eligible
requests. Frozen profiles already come from a verified memory snapshot; repeated
profile copies and active-provider scans cause this work, not configuration
file reads. The anticipated issue grows when HF finishes and fewer than eight
global slots can be occupied despite every remaining provider being full.
This synthetic benchmark is not an empirical model result or a demonstrated
end-to-end speedup.

## Exact scope and prospective handoff

The new collector caches verified profile-to-provider/model descriptors and
maintains pending-key and active-provider counts. It skips a pending scan when
every remaining key is capped. For a fixed scheduler state and completion-event
stream, this preserves the eligible set and first eligible sorted request.
Actual completion batching and timing can differ when the client is faster;
neither model outcomes nor an identical empirical timing sequence is promised.
All provider/model/global ceilings, native spacing, cooldowns and guards remain.

Prepare/review/test the new implementation while v3 continues. Only then use the
existing v3 STOP mechanism to cease new dispatch and drain already started
requests. Require its actual stopped/terminated supervisor and immutable archive,
not an invented failure exit code or forced process kill. Preserve the STOP
marker and every terminal, request, receipt and cost. The forecast and collector
freeze bind the exact dynamic complement after that drain. Commit/freeze/tag/
push the new collector and five-batch analysis before any new inference. Never
retry a failed or ambiguous request. If a safe fresh budget/time/access gate
cannot pass, do not bypass it or claim completion.

The independent unit remains640blocks and all six reader profiles. Retain every
registered body, endpoint, sampling/decoding choice, host action, finite oracle,
primary estimand, scoring and bootstrap. Earlier serving failures and full
unknown-cost reservations stay in denominators. There is no model substitution,
shorter output, relaxed error allowance, new scientific hypothesis or optional
stopping on model accuracy. Unfinished empirical accuracy stays blinded.

## Recovery and delivery

Retain the v3 exact HF overload taxonomy and bounded availability recovery:
only specifically classified serving faults pause/drain/recheck before unstarted
dispatch. Unknown429s, funding/authentication, model/JSON/capture/integrity errors
stay fatal. The900second episode governs new inference admission; bounded GETs
and existing requests may finish later. The existing32 total500 allowance,
32 connection allowance,1024 phase serving allowance and all prior spending are
carried forward rather than reset. Preserve unchanged wallet floor, caps,
04:55–05:05UTC blackout and9November05:59UTC cutoff.

The new cost/time forecast uses exact unstarted counts and the original cost
model with observed service/barrier sensitivities, auxiliary work,25%headroom,
3300seconds overhead and declared server-wait sensitivities. It takes no assumed
CPU speedup credit. It remains conditional, not a bound or deadline guarantee.

## Actual final-data gates

Collector: `runs/swarm-ledger-efficient-v1-driver/state.json`.
Waiter: `runs/efficient-resume-postprocess-driver/state.json`.
Proof: `research/swarm-ledger-efficient-resume-release-proof.json`.
The new analysis requires actual terminated original/v1/v2/v3 predecessors,
complete terminated efficient collector and completed original HF recovery.
It admits the exact disjoint five-batch union and uses unchanged scientific
scoring/serialization, followed by strict replay, provenance, plots and the
registered sensitivity. Older stopped waiters cannot satisfy paper readiness.
The report remains historical until actual verified-data authoring, official
template export, eight-main-page check and inspection of every actual page.
The excluded serving pilot stays blocked/unrun. Four queued scientific reviews
remain after current validation and paper integration.

The implementation and its synthetic equivalence tests are the primary sources
for the eligibility claim. [Python futures semantics](https://docs.python.org/3.12/library/concurrent.futures.html)
distinguish submitted/running/completed work; faster bookkeeping does not make a
running request unstarted. [Apart guidelines and judging](https://apartresearch.com/sprints/swarm-alignment-2026#guidelines)
remain the execution/impact/clarity reference.
