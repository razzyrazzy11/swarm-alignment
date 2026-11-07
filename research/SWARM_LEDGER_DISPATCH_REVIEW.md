# Authorized four-file OpenCode/Ollama review and local dispositions

Completed 7 November 2026 through an isolated task-local OpenCode server,
`security-reviewer` with catalog-confirmed `ollama-cloud/deepseek-v4-pro`.
Task `dd60d595-00e6-4c6d-b15e-e81d3bd25b61`; final run
`36795dd2-2424-4b19-a2dc-c3109bb7c4a6`. The first read turn produced no final
text; one text-only continuation completed the report. The owned server was
stopped. Only the four explicitly authorized V1 files were supplied; they were
read fully (709, 308, 43 and 143 lines), with no mutating tools. V2 files, raw
runs, keys and account data were excluded. This is a bounded static review,
not empirical validation or a scientific primary source.

| Authorized file | LF-normalized SHA-256 |
|---|---|
| `experiments/swarm_ledger_dispatch.py` | `df23772a0980cbab8e680bd0b9923394d937f96ed3aed0c467bcf336769c288b` |
| `experiments/swarm_ledger_forecast.py` | `aad2a494cf59a0d99914ce9a1164e768bc65b7e4fc8db449f631bda607126af0` |
| `research/swarm-ledger-dispatch-config.json` | `f9d9917ed1baeb21bf8876fb7be29c7bd5f7098133a23f39682267fd8c19f564` |
| `research/SWARM_LEDGER_DISPATCH_PROTOCOL.md` | `b161d72865a927552e17c2034c7833d235009a5dff84f29b0b12aaaaf6cd1e47` |

The reviewer found provider-separated financial caps, reserve-before-send,
unknown-send holds, persistent Retry-After and metadata-only capacity selection
internally consistent. It did not inspect the imported scientific collector,
pricing tables or experimental observations, so its conditional findings were
checked locally against the owning source rather than adopted as facts.

| Concern | Local disposition before V2 registration |
|---|---|
| Manual `STOP` has no programmatic writer | This is an operator soft-stop convention. Document the literal file, drain and unstarted-identity behavior; it never bypasses fatal stops or unknown sends. |
| Forecast hardcodes a 60-second floor | In reviewed V1, the immutable scientific config fixes `gateway_backoff_seconds` at 60; no mismatch was found. Before V2 registration, its scheduling protocol separately sets a 15-second floor for Adaption 502/503/504 and matches that policy in its forecaster; overload and other-provider floors stay 60. V1 remains unchanged. |
| Whole-window off-peak gate and wallet formula | Deliberately conservative for this weekend window. Document the complete interval and strict `projected MAIN peak / 2 + 5 + 0.10` threshold, separate from actual invoices. |
| Unknown usage is required to equal known eligible-transient count | The owning transport never normalizes HTTP-error bodies as successful native usage. Other unknown-usage failures stop collection and cannot produce a complete admitted DEV graph. The equality is a rejection guard for this registered source, not a claim about arbitrary APIs. |
| Drain does not update all terminating in-memory counters | Every caller drains and immediately exits. Durable receipts and costs are retained; later entry reconstructs accounting. Document this lifecycle rather than imply further checks use stale memory. |
| MAIN cooldown relies on a shared checkpoint | Intentional cross-process carrier, persisted for every eligible transient including the final response. Document its role; no deletion is an allowed workaround. |
| One error/profile versus two/group; Ollama pilot three versus fallback two | These are distinct, explicit design constraints. They are protocol-consistent; merging them would change the registered experiment. |

These dispositions do not retrospectively repair V1. Its completed-only health
gate actually stopped on known bounded completions; V1 remains a failed,
excluded pilot in `SWARM_LEDGER_DISPATCH_DEVIATION.md`. V2 separately registers
the narrow serving-only correction, shared historical cost and PID-reuse guard.
The external reviewer did not inspect those V2 changes. Local tests and the
independent unchanged public scientific verifier remain necessary.
