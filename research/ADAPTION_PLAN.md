# Turning credits into an empirical oversight study

Prepared 6 November 2026. This is a source-backed execution plan, not a completed experiment, a price guarantee or a prediction of winning. No research credits have been spent. The environment contains a placeholder `.env.example`, but no configured `ADAPTION_API_KEY` was found in this process or a local `.env` file. Actual balance and model access have not been inspected.

## Recommendation

Use hosted inference to evaluate supported executor attribution on mechanically labeled, executed fake-data episodes. Keep Track 4 as the anchor and Track 3 as supporting relevance. Prioritize a correct testbed, an information-matched comparison and an independently repeated result before optional training. The [sprint's current judging rubric](https://apartresearch.com/sprints/swarm-alignment-2026#guidelines) makes execution and clear evidence central; using a sponsor or spending the entire allowance does not supply scientific value by itself.

The first scoping build has no agent-performance data. Its nine report-integrity tests check documents, not a swarm monitor. An empirical submission needs new, genuine execution traces and model responses, plus measured outcomes. “Actual data” can mean observed runs in a clearly labeled synthetic environment; it must not mean invented outputs or simulated numbers presented as observed model performance.

## What the data should contain

Use three bounded workflows, for example fake access approval, fake record amendment and fake delegated release. Each has one coordinator, three immutable worker instances and a designated request. Execute typed operations in memory. Record pre-state, attempted action, authorization rule, result and post-state. Derive the executed-mutation label from state transition, not a model's narrative. Script clean cases and known-positive violations initially; this isolates oversight and does not establish spontaneous collusion.

Keep authentic host originals. Project investigator packets with complete, random-loss and fixed selective-loss views, crossed with display-name churn. Reuse pre-churn masks across paired views. Keep instance binding and execution receipt relations distinct. A second implementation or independently hand-derived fixtures must check the compatibility oracle. Empty compatible-history sets stop the scoring pipeline and are reported, not relabeled ambiguous.

Suggested files, under ignored `runs/` until redacted for release:

| Artifact | Required content |
|---|---|
| Episode manifest | Seed, family, development/test split, public task rules, request ID, host-state digest |
| Host trace | Immutable instance/parent IDs, ordered typed calls, authorization facts and actual results |
| Export manifest | Projection version, candidate inventory, masks, churn mapping, binding/receipt availability |
| Private reference | True executor/NONE, compatible labels, supported status and independently checked fixtures |
| Reader request/response | Exact bytes, prompt/version/model, returned model, status, output, latency and usage |
| Analysis output | Counts/denominators, exclusions, paired effects, cluster intervals, coverage and cost |

Only the public rules and visible packet reach a reader. Do not include a hidden label, deletion mask or condition tag in filenames/prompts. Record real responses including invalid JSON, refusals, timeouts and truncation. One retry is one planned call's terminal status, with both attempts auditable. Model errors are results, not grounds to silently replace data.

## Primary test and useful intervention

Keep one primary contrast: selective-minus-random unsupported executor accusations at 25% loss with churn, full pre-corruption instrumentation and the plain prompt, on the chosen primary model. The churn interaction, other prompts/models and restoration are secondary. Report structural answerability and compatible-label counts before interpreting model failure. A targeted selector that destroys more decisive evidence may reduce answerability by construction.

The useful intervention is **minimal authentic evidence restoration**. Enumerate the smallest add-back bundle that makes a packet's executor label singleton; report its cardinality and actual token cost. Compare with seeded equal-record random restoration and report the fraction resolved, correct supported definite coverage and unsupported accusations. An oracle-minimum bundle is a diagnostic lower bound using the bounded model, not a deployable selection policy. If a deployable selector is proposed, restrict it to visible packet/public rules and evaluate it separately. This is distinct from claiming a new generic logger or runtime repair system; see GAP_ANALYSIS.md for Qin, Yun, BLADE, BRIDGE and Syscon overlap.

Add a no-handoff control retaining the same candidate workers and action opportunities, plus name-permutation fixtures with compatible labels held fixed. Single-worker controls have a different answer space and need separate interpretation. If dependencies do not matter, report identifier/evidence fragility, not a new swarm phenomenon. Use authentic-source restoration only; fabricating an apparent receipt is a different threat model.

## Recommended data size after a feasibility pilot

The earlier 120-episode/three-repeat profile remains a fallback, not a frozen registration. Prefer the following larger profile if the pilot confirms oracle validity, throughput and affordability:

- **20 development episodes**, excluded from confirmation. Test labels, context size, output completeness, endpoints, error handling and observed charges. No picking prompts on held-out-family outputs.
- **600 independent source episodes**,200 per family: 100 clean and 100 scripted violations. Hold one family out of prompt/rule development while retaining its 200 confirmatory episodes. Independence comes from fresh task/state draws under a declared distribution, not merely new IDs or copied transcripts.
- **Six core packets per episode**: zero loss plus random/selective 25% loss, each with churn absent/present. Two prompts, one initial response per candidate model. Three candidate model families imply 21,600 core calls.
- **60 episodes selected before outputs**, balanced by family/cohort, receive two extra responses per packet/prompt/model to characterize inference variability: 4,320 additional calls. Keep these repeats secondary; they do not change the primary one-call estimand or independent n.
- With the pilot, total planned calls are 26,640 before retries, secondary add-back experiments or LLM-based trajectory generation. Mechanically executed source episodes themselves need no model tokens in the initial scripted environment.

More independent episodes improve precision more directly than repeatedly reading the same 120 cases. With zero false-accusation events across 300 eligible independent clean episodes, the one-sided 95% zero-event upper bound is about 0.994%. This is exact at common Bernoulli risk and conservative for the mean independent heterogeneous risk. It is not a guarantee of less than 1% deployment risk or a power analysis for the targeted/random effect. Recompute actual n after exclusions. Pair and bootstrap at source-episode level; report per-family/model results and the fixed aggregate, with secondary comparisons labeled.

Freeze the final sample size before confirmation using operational cost/variance feasibility, without inspecting the favorable direction of held-out effects. If 600 is infeasible, use a prespecified smaller profile and report its weaker precision. Do not stop because a result becomes significant. The old 4,320-call profile and this expanded plan must never be mixed in the reported denominator.

## Verified Adaption capabilities and configuration

The [official Responses quickstart](https://docs.adaptionlabs.ai/inference-stacks/quickstart/) supports direct hosted calls using SDK 0.16.0 or later. The [Models page](https://docs.adaptionlabs.ai/inference-stacks/models/) states that availability varies by API key; query `client.models.list(type="hosted")` before choosing models. Hosted and training model IDs differ.

Use the [Responses API contract](https://docs.adaptionlabs.ai/api/resources/responses/methods/create): direct hosted ID, `tools=[]`, `tool_choice="none"`, `agentic_memory=False`, `store=False`, no previous response, fixed temperature and an output cap selected in the pilot. Parse/validate the requested JSON locally; do not assume undocumented structured-output parameters. Retain response status, returned model, usage and output details. `store=False` controls API continuation storage, not a blanket assertion that the provider retains no operational data. No retrieval index or uploaded test labels are needed.

The [stack/memory documentation](https://docs.adaptionlabs.ai/inference-stacks/key-concepts/) explains why direct hosted calls simplify this comparison: stacks can supply tools, datasets and memory. Freeze requested/returned IDs and software/config hashes. A provider may still change a hosted alias; record dates and any available revision metadata and acknowledge that limitation. Confirm that reasoning-token/output limits and charging match the pilot; visible answer length alone is not a billing measure.

## Published prices and reproducible costing

The [Adaption hosted-model price table](https://docs.adaptionlabs.ai/inference-stacks/models/), accessed 6 November, quotes **platform credits per million tokens**. It does not verify this account's balance, dollar conversion or sprint-credit applicability. Treat the user's $500 award as a ceiling pending that check.

| Candidate role / hosted ID | Input | Output | Estimated credits: core + repeat subset + pilot |
|---|---:|---:|---:|
| Primary candidate `qwen3.5-397b` |0.55|3.50|92.96|
| Replication `glm-5.2` |1.40|4.40|154.61|
| Cost comparator `deepseek-v4-flash` |0.04444|0.13332|4.79|
| Total | | |**252.36**|

These are candidate choices for availability and complementary serving families, not a measured ranking of ability. Assumptions: 6,000 billed input tokens and 2,048 billed output tokens for each planned response, uncached rates. Formula: calls × (input_tokens × input_rate + output_tokens × output_rate)  / 1,000,000. Actual output can be smaller, but retries, larger contexts, generation, secondary tests or billing overhead can increase cost. Do not assume cached discounts. At 512 output tokens, the same hypothetical plan estimates 142.79 credits, but a truncated reasoning response is not a useful saving.

Reproduce the arithmetic with `python research/cost_plan.py`; rates and design live in `adaption-design.json`. The calculator performs no network calls and its output is not experimental evidence. Proposed spending control: retain the earlier 25 pilot /250 core /100 replication /125 reserve envelopes; do not exceed 375 spendable research credits overall without revising the plan. Track an estimated liability for every pending request; reconcile returned usage and account debits at batch boundaries. A local token estimate is not a guaranteed provider hard cap. Stop on missing usage, unrecognized models/prices, unreconciled charges or insufficient balance. At aggregate 60 requests/minute, 26,640 calls take at least 7.4 hours before latency/retries; at 120/minute, 3.7 hours. These are arithmetic scenarios, not verified account limits. Measure throughput before freezing.

## Why training is an optional later experiment

The [AutoScientist supported-model conventions](https://docs.adaptionlabs.ai/autoscientist/supported-models/) impose minimum effective row counts (at least 1,000 for SFT and 12,000 for DPO, with some models requiring more), and warn that overlong training rows may be truncated. Those are launch requirements, not sufficient scientific sample sizes. Multiple projected packets from one episode are not independent examples.

Fine-tuning is justified only after the evidence oracle works, a baseline failure exists and there is time for a distinct training experiment. Split by source episode and family before augmentation; never upload held-out references into training or retrieval. Compare trained versus untrained models on identical untouched packets, same serving features and measured cost/latency. Platform preference win rate or synthetic-data quality scores do not replace task-grounded endpoints. Training price and account training entitlement remain unverified, so no training spend is recommended in the core plan.

## Concrete submission evidence

The main figure should show unsupported accusations **and supported definite coverage** by loss/churn, with episode-level uncertainty. A second panel shows oracle answerability so information loss is visible. The main table should include the same-packet deterministic comparator, always-abstain/fixed-actor baselines, candidate models, invalid outputs, latency and credits. A compact restoration table reports evidence recovered per added record/token and a random-add-back control. Show one real failed reader example with source/packet/output hashes; do not write an illustrative output as if it were observed.

Retain scripts, frozen manifests, benign fixtures, redacted measured aggregates and a reproduction command. Separate scripted-condition results from any later LLM attacker. Complete the report only after real runs; label null/negative results and limitations. Keep the current scoping paper distinct until those results exist. The required ethics appendix must discuss evidence suppression and false accusations. No empirical data, model responses or credits are invented by this plan.
