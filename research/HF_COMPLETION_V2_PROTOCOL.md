# Prospective HF completion recovery v2

The first completion journal stopped after nine terminal receipts. A metadata-only
inspection found an HTTP 429 with a top-level `type: server_overload` and a message
beginning `server overload`. The frozen v1 classifier recognized nested error
profiles only, so it conservatively classified this receipt as fatal. Its bytes,
false `service_overload` flag and all nine observations remain unchanged.

This amendment applies only to the 1,889 original identities that were never
started. It does not repeat the overload receipt or any earlier observation.
The source wrapper is registered under analysis v2 before supplemental-answer
inspection; then a separate `hf-completion-v2` operational registration commits
the first nine journal hashes, original body descriptors and exact remaining
complement before fresh calls. Existing scientific endpoints, prompts, decoding,
scores and estimands remain unchanged.

The prospective classifier additionally accepts HTTP 429 JSON with an exact
top-level type or code `server_overload` **and** a string message beginning
`server overload`. Other unknown 429s remain fatal. Bounded private captures keep
trace IDs and raw bodies private. No change is made to frozen v1 source.

One request may be active; starts are at least 30 seconds apart; transient
overloads wait at least 60 seconds and honor Retry-After; eight consecutive new
transients pause 600 seconds. No identity is retried. Timeout 120 seconds, exact
route/price catalog recheck every 100 new calls, max 4096 output tokens, original
unknown-usage reservation, and fatal profile/capture gates remain in force.
The combined completion cost cap is $2.50 across nine plus 1,889 terminals, and
the 256 new-transient allowance includes the diagnosed first-journal overload
while excluding the original historical five 429 terminals. Estimates are not
reconciled invoices. The new driver stores safe metadata at
`runs/hf-completion-v2-driver/state.json`.

Both journal prefixes, terminal normalization, returned-model aliases, request
hashes and cost arithmetic must validate before a completed-original report.
All 1,898 supplemental terminals, including every failure, are combined with the
immutable 9,742 original terminals. A completed report is forbidden while a
planned identity is absent or unresolved. Operational serving and schema
success remain distinct from terminal completeness. Public verification needs
only committed public artifacts and both operational registrations.
