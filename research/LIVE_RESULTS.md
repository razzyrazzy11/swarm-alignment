# Completed live-handoff audit results

This is the completed `live-audit-v2` study, with its separately frozen operational continuation. Earlier scripted findings remain in [STATEFUL_RESULTS.md](STATEFUL_RESULTS.md) and the immutable `results-v1` release. The current aggregate is [live-results.json](live-results.json); public cases support credential-free replay.

Actual collection contains **720 actor calls and 9,360 audit calls**. Main auditing covers 192 new source groups, 384 paired trajectories and 8,064 dependent views/readers. Influence contributes 144 new receiver trajectories and 1,296 audits on 48 shared sources. Calls and views do not increase independent n.

## Primary result and matched readers

The new primary endpoint is delegated-workflow grounded correctness under metadata-selected versus random authentic add-back, averaged over random and selective loss: **+5.73 pp (95% source-bootstrap +1.04 to +10.42; n=192)**, primary reader only. The original scripted primary was not replaced.

| Reader | Restoration grounded: metadata − random | Unsupported worker: selective − random |
|---|---|---|
| Gemma 26B A4B | +5.73 pp (95% source-bootstrap +1.04 to +10.42; n=192) | -15.10 pp (95% source-bootstrap -20.33 to -9.38; n=192) |
| Gemma 31B | +10.94 pp (95% source-bootstrap +6.77 to +15.10; n=192) | -6.25 pp (95% source-bootstrap -10.42 to -2.08; n=192) |
| HF Llama 70B | +9.11 pp (95% source-bootstrap +5.73 to +12.50; n=192) | -10.42 pp (95% source-bootstrap -16.15 to -4.69; n=192) |

Only the primary reader/restoration contrast is the registered new primary. Other readers and accusation contrasts are secondary; no multiplicity-adjusted universal claim follows. The 10,000-resample bootstrap retains whole source groups and family/assigned-authorization strata.

| Reader | Main calls | Grounded correct | Supported definite | Unsupported worker | Unsupported NONE | Invalid |
|---|---:|---:|---:|---:|---:|---:|
| Gemma 26B A4B | 2688 | 1752 | 1752 | 534 | 333 | 69 |
| Gemma 31B | 2688 | 2149 | 2149 | 205 | 320 | 13 |
| HF Llama 70B | 2688 | 1335 | 1286 | 833 | 240 | 0 |

Grounded correctness includes justified abstention. A factually correct executor guess can remain unsupported. Main totals include both branches and all seven evidence views; influence audits are separate. Exact-packet, always-abstain and fixed-A baselines and all by-view/model results are retained in the aggregate.

## Actual fake actions and influence

| Branch | Trajectories | Valid action | Unauthorized write | Useful completion | False completion claim |
|---|---:|---:|---:|---:|---:|
| solo | 192 | 192 | 2 | 50 | 0 |
| delegated | 192 | 192 | 4 | 48 | 0 |

Delegated minus solo violation: +1.04 pp (95% source-bootstrap +0.00 to +2.60; n=192). Useful completion: -1.04 pp (95% source-bootstrap -2.60 to +0.00; n=192). This is a compound identity/context-boundary intervention, not a pure agent-count causal effect. Useful completion means write when permitted or read otherwise; safe refusal is separate, not an unauthorized action.

| Influence arm | Trajectories | Unauthorized write | Useful completion |
|---|---:|---:|---:|
| actual | 48 | 2 | 11 |
| benign | 48 | 2 | 11 |
| malicious | 48 | 2 | 11 |
| warning | 48 | 1 | 11 |

Malicious minus benign violation: +0.00 pp (95% source-bootstrap +0.00 to +0.00; n=48); warning minus malicious useful completion: +0.00 pp (95% source-bootstrap +0.00 to +0.00; n=48). These are paired controlled one-hop exposures, not spontaneous propagation. Violations occurred in every arm; zero observed paired contrasts do not establish absence of influence, robust mitigation or zero risk.

## Evidence acquisition and trust

The protected host records actual typed decisions and fake state. Random loss removes four of twenty records; selective loss removes two critical and two other records. Both branches/readers share masks. Selection sees only opaque ID, kind and handle. Both restoration policies add at most two authentic records; bytes/tokens and semantic information are not matched. The typed interface and critical-record deletion policy are favorable synthetic assumptions. Public authorization/advisory context remains visible independently of redundant lost records.

## Registration, retained failures and costs

All five main/influence phases completed their planned identities. Across these phases 2 gateway errors and 12 incomplete outputs remain retained. The original audit gate halted at 204 terminal calls after three known-usage truncations. Before additional calls, `live-audit-v2-continuation-v1` registered the exact 7,860 unstarted complement, retained known-usage truncations as INVALID without a count halt, and replaced batch barriers with a four-active/two-HF sliding window. The eight-gateway allowance and cost reservations remained. No failed request was retried. Prompts, models, planned identities, token limits and frozen scientific analysis were unchanged. This is not an unamended uninterrupted confirmatory run. Excluded v1 qualification failed; fresh v2 qualification passed serving/schema gates, not a scientific accuracy gate.

Actor plus audit token-rate estimates are **1.0315761365 Adaption credits** and **$0.687000460 HF**, excluding qualifications and older studies. Gateway unknown usage retains a conservative reservation. These are not reconciled invoices, final balance deductions or provider-enforced caps. No training/GPU rental/top-up was launched.

Only two workers, three known workflow structures, two reader families and trusted collector originals were tested. Hosted weights are not pinned. Earlier serving results informed format/operational amendments. No real incidents, large-population coordination, collector compromise, spontaneous collusion or general deployment safety was established. See [WEIGHT_RESULTS.md](WEIGHT_RESULTS.md) for the separately frozen checkpoint study and [REPRODUCING_RESULTS.md](REPRODUCING_RESULTS.md) for offline commands.
