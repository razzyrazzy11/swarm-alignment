# Ollama reader extension v1

## Question and registration timing

Can a second-family reader use the same evidence, and does an explicitly controlled thinking mode improve decisions when that evidence is already sufficient? This is a separately registered secondary extension of the Track 4 swarm-audit study. The original single primary comparison remains unchanged. This document is written after original collection and operational missingness were observed, before scientific outcomes were inspected and before any Ollama inference. Operational access and model metadata checks are not scientific results.

The original 192 actor trajectories and evidence packets are reused without changing workers, hidden worlds, labels, restoration algorithms, or scoring. Repeated reader calls do not create additional independent trajectories. Hugging Face Novita remains an incomplete original condition; Ollama never fills its missing cells.

## Fixed conditions

| Condition | Requested model | Exact think value | Main views | Main calls | Calibration calls |
|---|---|---|---|---:|---:|
| ds_off | deepseek-v4.1-flash:1017 | false | All original ten | 3840 | 40 |
| ds_low | deepseek-v4.1-flash:1017 | low | Sufficient only | 384 | 40 |
| gemma_bridge | gemma4:31b | false | Sufficient only | 384 | 40 |

Total: 4728 planned reader calls, plus six excluded technical pilot calls (two per condition). Both original instruction bundles are used. Source worlds number 192; calibration has 20 distinct scripted worlds. All conditions are interleaved with order seed 710033 and at most two active requests. Each call has a fresh context.

The pilot uses unrelated prompts. Admission depends on authentication, completion, model identity, native response shape, valid usage counters and supported configuration, not exact wording or scientific task performance. Failed pilot receipts remain recorded; no outcome-selected model substitution is permitted.

## Serving and collection

Use the documented native `https://ollama.com/api/chat` endpoint with the original system and user strings, `stream:false`, exact condition-specific `think`, temperature zero and `num_predict:4096`. Input serialized bytes are capped at 24000. No tools, structured-output enforcement, additional memory or scientific prompt changes are introduced. Score only final `message.content`; retain separate thinking privately without publishing or interpreting it.

Check supported thinking values using `/api/show`. Record catalog digest prefixes as metadata, not full cryptographic weight commitments. Check model metadata before collection and every 100 calls; changed identity or configuration stops collection. Temperature zero is not a guarantee of determinism. A returned alias must be explicitly verified before scientific collection, not guessed.

Record durable starts and terminals, unique condition-aware IDs, request hashes, source/view/instruction metadata and native receipts in ignored output directories. Never retry a started ID. Known incomplete or invalid terminals receive the original operational INVALID score; unstarted calls remain unknown. Authentication, payment, unknown rate-limit errors, drift, unresolved starts, STOP or budget exhaustion stop new dispatch and drain active requests. Allow at most eight explicitly identified service-overload or gateway failures per stage; retain them and back off at least 60 seconds or the longer Retry-After before dispatching new IDs. Do not infer overload retrospectively for earlier errors whose bodies were not retained.

## Resource limits

Pilot estimated-cost cap: $0.10. Reader-stage estimated-cost cap: $9.90. Combined estimated-cost cap: $10.00, including reservations for unknown usage and active calls. Conservative published peak uncached rates per million tokens are Deepseek $0.30 input/$1.20 output and Gemma $0.14/$0.40. These are estimates, not invoices; do not claim exact billed cost from token counters. Do not assume cache or weekend discounts.

Poll account balance no more than once per 60 seconds; stop and drain when remaining credits reach $[private account value withheld]. No purchases, plan changes or top-ups are authorized by this protocol. Other account activity can confound balance differences. The official [chat API](https://docs.ollama.com/api/chat) describes `eval_count` as generated tokens. In the pinned [official chat implementation](https://github.com/ollama/ollama/blob/5e983d4f800053c6f5691496b675c3212aa8099d/server/routes.go#L3340-L3392), runner token metrics are copied before content/thinking separation; this supports using the counter for total generated tokens rather than recounting final visible text. It does not attest the hosted deployment or billing. The configured 4096-token request limit, observed counter ceiling, conservative reservations and balance floor are complementary guards, not an absolute invoice guarantee. Pilot admission requires valid counters within the requested ceiling; anomalous counters stop collection. No private thinking text is inspected to infer competence or cost. Retain any provider-reported overrun honestly rather than truncating accounting to the configured limit.

## Analysis and interpretation

The original Gemma 26B procedure-minus-direct sufficient-evidence comparison remains the only original confirmatory primary, with its frozen source ordering, strata and bootstrap. The new fixed secondary contrast is ds_low minus ds_off on DIRECT, sufficient evidence, paired over the same 192 sources. Use the original whole-source stratified bootstrap helper. Other Deepseek evidence and instruction comparisons are exploratory.

The exploratory bridge is Ollama Gemma minus original Adaption Gemma 31B on DIRECT sufficient evidence, paired by source. It compares implementation bundles: weights, quantization, templates and serving configurations may differ. It does not isolate a pure hosting effect. Procedure bridge summaries are descriptive. Neither mode changes nor this study establish that weights reveal intent. No fine-tuning is included; a later intervention requires a reproducible residual failure and separately frozen source-disjoint training and test splits.

## Sources and scope

Checked 7 November 2026: [native cloud API](https://docs.ollama.com/cloud), [thinking controls](https://docs.ollama.com/capabilities/thinking), [balance API](https://docs.ollama.com/api/balance), [pricing](https://ollama.com/pricing), [terms](https://ollama.com/terms). The documented authenticated API is the interface used for bounded research requests; no scraping or restriction circumvention is involved.

This is Track 4, Multi-Agent Oversight and Control. Impact comes from separating evidence acquisition from use; execution requires reproducible packets, honest missingness and bounded collection; clarity requires distinguishable conditions and denominators. Follow the [Swarm Alignment guidelines and judging criteria](https://apartresearch.com/sprints/swarm-alignment-2026#guidelines). The official-template report must disclose limitations, dual-use considerations, existing work and amendments. Registration freezes include this protocol, sources, tests, configuration and catalog metadata before the pilot.
