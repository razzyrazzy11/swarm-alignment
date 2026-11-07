# Capacity pilot stop and prospective correction

The `swarm-ledger-dispatch-v1-pilot` tag at
`a57fc965f18e577e9ad1bb26a4ed51b93c4d06dc` was pushed and verified before
capacity collection. Its first group stopped after 17 started and terminal
requests. All had HTTP 200, known usage, matching model IDs and no normalization
anomaly. Three responses were `incomplete` at the fixed 4,096-output-token
ceiling: one Q397 and two GLM52. The completed-only pilot health gate treated
these bounded responses as fatal. The stop was honored; later groups did not run.

This is a **failed, excluded pilot**, not a successful capacity result. The
overall pilot retains 17 terminals and 181 unstarted identities; its first
64-request group retains 47 unstarted identities. All native receipts, starts,
dispatch events and stop records remain unchanged. No started observation is
reissued or retrospectively converted to a completed scientific verdict.
`swarm-ledger-dispatch-v1-stop.json` contains scrubbed serving/accounting metadata
and provenance commitments, without answers, keys, headers or account balances.
Its 0.18300835 estimated Adaption credits remain charged to the combined
capacity-pilot ceiling.

The correction separates **transport integrity** from **delivery of a finished
answer**. A known-usage, exact-model, anomaly-free HTTP-200 response that reaches
the registered output ceiling can establish how the bounded request was served,
even when no completed answer was delivered. It cannot establish a valid or
correct verdict. The scientific decoder and admission rule remain unchanged:
an incomplete scientific response remains an operational failure under the
original scoring, not a rescued answer or proof of reasoning incapacity.

A separate v2 operational source/protocol/config and registration are required
before further capacity calls. They preserve the original scientific bodies,
token ceilings, endpoints, cohorts and estimands. Their capacity gate may admit
the precisely bounded completion status for serving assessment, without parsing
verdict accuracy. Unknown usage, unknown sends, alias, authentication, billing,
capture anomalies and other unexpected statuses remain fatal. The v1 partial
group cannot become an eligible comparison through this correction.

The v2 capacity identities are distinct, excluded technical observations. Its
budget must include the known cost of v1; neither old counters nor fatal stops
are deleted. Main collection still requires its own scientific and operational
registrations and a complete-workload cost/time forecast. More credit alone is
not a reason to start a comparison projected to stop part-way.
