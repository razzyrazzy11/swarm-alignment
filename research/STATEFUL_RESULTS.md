# Completed stateful evidence-audit results

6 November 2026. The source of every number below is [stateful-results.json](stateful-results.json), replayed from the sanitized public cases. This report supersedes earlier descriptions of the main study as unexecuted; prospective protocols remain preserved at their registration-time state. The study concerns a finite fake-data grammar and supported executor attribution, not intent, decisive causal blame, emergent coordination or deployment safety.

## Primary question: no supported increase in accusations

The main grid completed 3,840 planned/attempted/returned requests: two Adaption Gemma endpoints, 192 source draws, and ten dependent evidence views per source. Each of three families contributes 64 draws, evenly split between clean and scripted-violation strata. Approval-join model outputs were held out from qualification/prompt selection. The 192 draws are not 1,920 independent packet trials per endpoint.

The registered primary contrast is unsupported executor accusations under selective minus random three-record loss, with churn present, on the 26B endpoint. Its estimate was **−1.04 percentage points**, with a paired, family/cohort-stratified 95% source-bootstrap interval of **−6.77 to +4.69**. The hypothesized increase was not supported. This is not evidence of equivalence, zero effect or safety: the interval includes effects in both directions.

| Contrast | Gemma 26B, percentage points [95% interval] | Gemma 31B, percentage points [95% interval] |
|---|---:|---:|
| Selective minus random unsupported executor |−1.04 [−6.77, 4.69], primary|−14.06 [−18.75, −9.38], secondary |
| Churn interaction |1.56 [−3.65, 6.77]|−1.04 [−3.13, 1.04] |
| Priority minus random restoration: grounded correctness |43.23 [37.50, 48.96]|44.79 [39.06, 50.52] |
| Priority restoration minus no restoration: supported definite coverage |63.54 [58.33, 68.75]|64.58 [59.38, 69.79] |

Every comparison other than the first endpoint's first row is secondary. Intervals use 10,000 source resamples and preserve all dependent views. They are not multiplicity-adjusted significance claims. The negative secondary accusation contrast does not make missing evidence a safety improvement: unsupported NONE, abstention, coverage and answerability must also be considered.

## Overall reading performance and evidence restoration

These counts pool the ten prespecified view types descriptively; they do not represent independent observations or a deployment mixture.

| Reader | Calls | Grounded correct | Supported definite | Unsupported worker | Unsupported NONE | INVALID |
|---|---:|---:|---:|---:|---:|---:|
| Adaption `gemma-4-26b-a4b-it` |1,920|1,396|1,372|146|343|35 |
| Adaption `gemma-4-31b-it` |1,920|1,371|1,367|175|373|0 |
| HF `meta-llama/Llama-3.3-70B-Instruct:novita` |240|128|76|36|6|0 |

Grounded correctness includes justified abstention. The exact same-packet reference is grounded-correct on all 1,920 main packets, with 1,398 singleton-supported definite answers. Always-abstain is grounded-correct on the 522 ambiguous packets but supplies no definite findings. These references expose the distinction between evidential support and hidden-world guessing; they do not prove real-world oracle completeness.

The main clean-source false-accusation event occurred in 7/96 sources for 26B and 6/96 for 31B, considering either primary targeted/random call. These are not zero-event results, and no small deployment-risk bound follows. The 26B endpoint had 1,296 raw strict-schema-invalid outputs, versus 384 for 31B. This includes the separately reported INVALID calls and otherwise accepted outer JSON fences under the prospectively registered v2 parser. Acceptance of a fence is an encoding rule, not semantic repair or a correct-answer guarantee.

Priority restoration adds exactly two authentic collector records, using public schema positions; random restoration adds the same number. The policy is deliberately aligned with the constructed selective deletion, so its Adaption gains are partly a designed evidence-preservation comparison. It assumes available authentic originals and a powerful schema-index query interface. It is not a new general retrieval algorithm, immutable-logging defense or demonstrated live prevention mechanism. Equal record count does not imply equal tokens or semantic information.

## Matched HF comparison: limited restoration transfer

HF v3 completed 240 calls on the ten views of 24 **shared main sources**, selected by fixed indices before model outputs. This is a secondary model-family/serving comparison, not 24 new independent scenarios or proof of identical checkpoints across services.

The Llama/Novita selective-minus-random accusation contrast was −16.67 points [−33.33, −4.17]. Priority-minus-random restoration grounded correctness was **−4.17 points [−29.17, 20.83]**: the same grounded-correctness gain was not established. Priority restoration increased supported definite coverage relative to no restoration by 37.50 points [16.67, 54.17]. Distinct comparators and endpoints explain why coverage can increase without establishing a priority-over-random correctness advantage.

Earlier HF failures remain separate: Cerebras disappeared at v1 preflight, issuing zero evaluation calls. Qwen/Nscale v2 returned eight of 240 planned calls before its third 4,096-token truncation triggered stopping; five answers were valid, three were invalid/incomplete, and 232 calls remained unstarted. Llama v3 was separately registered before its outputs, preserving the subset, prompt and scientific comparisons. It did not retry, erase or replace Qwen answers. See [hf-preflight-v1.json](hf-preflight-v1.json), [hf-incomplete-v2.json](hf-incomplete-v2.json) and [HF_STATEFUL_PROTOCOL.md](HF_STATEFUL_PROTOCOL.md).

## Model-worker influence: no unauthorized writes observed

The separate extension completed 216 calls: 24 origin calls and 192 receiver decisions across four scripted exposures with warning off/on. Across all 192 receiver decisions, there were zero write attempts and zero executed unauthorized writes. The malicious-minus-benign no-warning violation contrast is 0 over 24 contexts, with a degenerate bootstrap interval [0, 0]; this does not establish zero underlying risk or absence of peer influence generally.

Under malicious exposure, allowed read success was 11/24 without the extra warning and 23/24 with it. Benign exposure was 24/24 in both conditions. These are descriptive secondary usefulness outcomes, not demonstrated mitigation of an observed write mechanism. Messages are narrow, exposed arms match characters rather than tokens, and no-peer context is shorter. The origin read and receiver typed actions were actually interpreted on fake state; scripted peer-message substitution does not demonstrate spontaneous communication, collusion or network propagation.

## Collection deviations and accounting

The original main runner stopped after an HTTP 502 with missing usage at 3,028 terminal records. A separately frozen/tagged operational amendment dispatched the ordered complement of **812 unstarted identities**. It changed the continuation rule after a service failure while retaining the original sample, endpoints, prompt and analysis; no request was retried, discarded or replaced. The failed request remains INVALID with reserved unknown liability. The final grid is an audited union, not an uninterrupted run under the original stop rule. See [STATEFUL_CONTINUATION.md](STATEFUL_CONTINUATION.md).

| Completed arm | Token-rate estimate | Provider cost fields |
|---|---:|---:|
| Adaption main |0.350667288 credits|0.253835568 credits summed |
| Adaption influence |0.0057058035 credits|Not reported here as a reconciled debit |
| HF v3 |$0.031954015|No reported-cost field; the aggregate zero is not proof of free service |

The earlier HF smoke estimate was $0.01346797 and partial v2 estimate $0.0714972: approximately $0.08496517 before v3, or $0.116919185 including it. These measured estimates fit the previously observed $2 HF allowance. No top-up, subscription change or training job was required or created. Estimates, provider-reported fields and actual account debits are different quantities; final invoices and earlier unknown development liabilities remain unreconciled.

## Reproduction and limits

Run `python -m experiments.stateful_release verify` and `python -m experiments.verify_stateful_results` from a checkout containing registration tags. They require no keys, native logs or provider calls. [STATEFUL_RUNBOOK.md](STATEFUL_RUNBOOK.md) and [the data documentation](../data/README.md) explain the exact scope. Retained native evidence can additionally be checked locally with `verify --raw`.

The two finite-world implementations agree within the declared grammar, not all real histories. Core states/actions are scripted, endpoints were chosen after development completion checks, only one source distribution and one selected HF route were evaluated, and the operational continuation is a post-registration deviation. SFT remains unlaunched. The contribution is a checkable bounded evaluation with negative primary and influence findings, a constructed preservation comparison and limited cross-reader transfer—not an originality or deployment-safety guarantee.
