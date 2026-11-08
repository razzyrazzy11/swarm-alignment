# DS low service bottleneck and safe response

This is an operational, result-blind diagnosis. It does not inspect answer
accuracy, change experimental conditions or authorize inference admission.

A fully observed hour ending at22:47UTC on8November contained940 DS-low
HTTP200 responses. Recorded transport latency averaged4.86s, with median3.08s
and p9517.80s. DS-off averaged0.76s in the same hour. The reported DS-low output
count averaged approximately907 tokens. Different inputs, output lengths and
provider conditions can affect those times; no causal model-quality claim follows.

A small, nonrepresentative metadata sample of six DS-low receipts reported
49.794s summed native total duration versus51.609s summed transport time. Native
prompt/evaluation duration breakdowns were unavailable. The remaining difference
includes network, gateway and client handling; it cannot be assigned to local
CPU alone. Reported native duration is not a measurement of pure model compute.

Ollama shares a frozen two-request guard across DS-low and DS-off. Completed
network intervals occupied approximately67% of those two slots in the measured
hour. This is observed request occupancy, not GPU utilization or proof that the
remaining time is recoverable. In-flight requests have unknown network endpoints.
The new `analysis.collection_utilization` diagnostic reports those separately,
clips intervals to15/30/60-minute windows and labels provider-guard denominators.
Adaption's guard of8 differs from its two reader models' theoretical combined
model-guard ceiling of4; neither number establishes achievable throughput.

Fixed global health pauses and their preceding drain tails explain substantial
idle time. A descriptive reconstruction found approximately1,046 idle Ollama
slot-seconds during long global gaps and511 during drain tails. The residual
approximately790 slot-seconds/hour remains unattributed: boundaries, capture,
wallet checks and reaping can contribute. It is not demonstrated avoidable work.

Measured pre-POST delay averaged about79ms, totaling roughly105 Ollama
slot-seconds/hour. Even the unrealistic illustration of eliminating all of that
component translates to only about52.5 wall-seconds/hour under two shared slots,
or about four minutes over the earlier4.71-hour resource scenario. That is not
an attainable speedup estimate, bound or new admission clearance. A new verified
handoff, freeze and startup would consume substantial time and could cost more.

The safe course is to continue the admitted collector unchanged. Preserve all
six reader conditions, auxiliary phases, bodies, output allowances, order,
concurrency, costs,100-completion barriers, failed identities and07:56 admission
cutoff. Do not reduce DS-low tokens, switch routes, increase shared concurrency,
drop DS-off or retry a failed request to improve a forecast. Unfinished numerical
results remain blinded. No optional pilot or new broad local test job belongs on
the primary critical path.

The implemented improvement is tested, nonfrozen utilization monitoring. Run
`analysis.collection_utilization` with the configured primary Python; it writes
new private snapshots and a separate history without overwriting the10:10
baseline. It issues no requests and computes no ETA, gain or admission decision.
Its tests cover clipping, simultaneous boundaries, cap overlap, missing timing,
right censoring, privacy and denominator interpretation. The CI metadata step
now includes those tests. This adds visibility without a collector handoff.

Keep all existing forecast scenarios and uncertainty allowances visible. A short
service tail is not a confirmed cutoff miss, while a favorable window cannot
waive a gate. The current completion runbooks, strict seven-stage waiter and
source-bound authoring handoff remain authoritative. Actual validation, verified
paper authoring and every-page QA precede the four queued reviews. Submission
by9November11:59UTC remains at risk until those steps genuinely complete.
