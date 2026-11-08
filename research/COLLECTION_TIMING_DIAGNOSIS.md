# Reader timing diagnosis and delivery preparation

Recorded on 8 November 2026 using operational metadata only. No unfinished
monitor verdicts, correctness scores or scientific effect estimates were read.

## What is real

The frozen `swarm_ledger_resume._execute` stops new dispatch after 100 completed
calls, drains all active work, then invokes
`ConnectivityGate.before_dispatch(force_health=True)` and catalogue checks.
The gate requires two healthy probe cycles at least 15 seconds apart each time,
even without an outage. Each cycle checks all three providers. These recurring
pauses consume real time; changing them would change registered source behavior.

At the 10:52 UTC snapshot, 5,800 reader calls were terminal, all HTTP 200; six
were in flight. The nested transport diagnostics supplied all actual network
start/end timestamps. There were 54 completed internal network-idle gaps of at
least 15 seconds, totaling about 1,000 seconds, with median 17.85 seconds. This
is consistent with the source-defined barrier. Timing alone cannot attribute
every gap to that cause; metadata GETs, durable capture and dispatch activity
are not fully timestamped by these inference intervals.

DS-low's first 100 measured network latencies averaged 3.88 seconds and its last
100 averaged 4.47 seconds in that snapshot. There is some real service variation,
so assuming perfectly stationary future latency would be optimistic. The reader
phase had no recorded serving or capture anomaly at that checkpoint. This does
not establish that any answer is scientifically correct.

## What the earlier warning overstates

The original cumulative forecast divides each profile's completed count by the
entire reader elapsed time, then projects its remaining count at that fixed rate.
It treats current capacity shares and the frequency of completion-based checks
as permanent. Both HF conditions share two slots; both DeepSeek conditions share
two slots. Allocation can change as conditions finish. Fast profiles also make
the 100-completion barrier recur more often in wall-clock time while they remain.
Thus that forecast is a useful fixed-share stress scenario, not a calibrated
prediction interval or proof that the study will miss the cutoff.

The tested timing helper separately computes remaining service work under the
shared capacity, then adds an empirical idle-gap allowance for remaining check
waves. Its median-gap scenario at 10:52, including auxiliary work, 25% headroom
and the original 3,300-second allowance, finished around 00:47 UTC on 9 November.
This is a conditional scenario, not a bound or guarantee: drain losses, future
task mix, captures, serving failures and outages may differ. The helper also
reports a recent-service/longer-idle stress scenario. Do not add barrier overhead
again to the cumulative forecast, which already includes observed pauses.

At 10:55 UTC the median-gap scenario finished around 00:40 and the stress
scenario around 01:24 UTC on 9 November. The latter uses the larger cumulative
or recent-100 mean for each profile, and the nearest-rank empirical p95 idle gap
(22.16 seconds, versus median 17.87). It is not a probabilistic 95% forecast
interval. Both scenarios remain conditional on the observed timing being useful
for the remaining task mix. Completed-call latency averages can be biased down
by slow calls still in flight. Retain the old fixed-share stress warning and
actual operational checks rather than substituting a guarantee from this range.

## Safest implementation

Keep the current collector, identities, all six conditions, generation settings,
capacities, recheck behavior, spending guards and 05:59 UTC collection cutoff
unchanged. Monitor both the fixed-share warning and the shared-capacity timing
scenarios, including recent latency and idle-time trends. Do not silently remove
the health barrier or retry failed scientific calls to improve a schedule.

Recover delivery time outside collection. The existing strict offline export and
replay remain prerequisites for actual authoring. The prepared candidate tool
checks actual terminated drivers, complete public replay, HF recovery, figure
provenance and an independent reconstruction of the registered sensitivity.
Primary authoring can overlap the excluded post-primary serving pilot; final
provenance must reflect stable pilot output if it is included.

An internal, clearly labeled synthetic layout probe was exported with a new
hidden owned Word instance, then rendered. Two main figures plus two appendix
figures, the complete three-table shapes and the prepared narrative fit six main
pages, ten total. These were blank layout placeholders and synthetic test cells,
not empirical results. This demonstrates template capacity for the prepared
structure, not that the future completed paper is final or visually approved.
The historical content, DOCX and PDF remain unchanged. Real findings, longer
captions and final edits must still pass the eight-page cap and every-page review.

All four queued investigations/reviews remain after current validation and paper
integration, as recorded in `DEADLINE_COMPLETION_PLAN.md`. These timing and
document-engineering checks do not complete the queued scientific review.

## Sources and commands

The registered collector and connectivity implementations are the primary
sources for dispatch behavior. The diagnosis uses only committed request-count
definitions and safe timing/status fields from local operational journals.

Run with the bundled primary Python from the repository root:

```
python runs/experiment-sanity-check/check_metadata.py
python -m analysis.collection_progress
python -m analysis.collection_timing
```

The first command owns frozen-prefix/source/cost integrity. The latter two add
dated operational histories and never change dispatch or score model answers.

The [official sprint guidelines](https://apartresearch.com/sprints/swarm-alignment-2026#guidelines)
require a research report on the official template and close at 23:59 Anywhere
on Earth on 8 November, or 11:59 UTC on 9 November. Clear, reproducible evidence
and honest limitations remain necessary; a timing scenario is not research data.
