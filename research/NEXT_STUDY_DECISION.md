# Decision after the completed live and checkpoint studies

Post-results-v2 assessment. This document reviews the completed results and scopes possible follow-ups. It does not amend a frozen protocol, authorize additional collection, or change the paper's registered endpoints. Three parallel reviews covered empirical/code gaps, sprint/prior-art fit, and checkpoint/training directions. The code review used an isolated OpenCode scout; speculative findings were checked and rejected where unsupported. No new inference or training was conducted for this assessment.

## The finding to lead with

**Selecting the right authentic records improved supported audit decisions in a bounded live-agent workflow.** Metadata-selected versus random two-record add-back improved delegated-workflow grounded correctness by 5.73 percentage points, 95% source-bootstrap interval 1.04–10.42, over 192 new source groups. Secondary gains were 10.94 points for Gemma 31B and 9.11 for HF Llama. These are three endpoints from two families on shared sources, not three independent replications. [LIVE_RESULTS.md](LIVE_RESULTS.md) retains the exact counts, baselines, invalidity and operational continuation.

This supports a specific operator decision: when trusted originals exist but the investigator's export is incomplete, spend a limited retrieval budget on the records needed to establish execution and identity, and withhold unsupported accusations. It does not establish a general collusion detector, resistance to a compromised collector, or improved reasoning at equal information.

The 144-proposal weight study is a supporting result. Gemma 31B produced 16/24 exact in-budget repairs; the other writers produced none. Harmful downstream changes can preserve an incoming handoff, whereas harmless reparameterizations change checkpoint hashes. Those controls distinguish byte identity from policy behavior. They do not demonstrate that an LLM message monitor missed a real checkpoint attack or that weights reveal intent. [WEIGHT_RESULTS.md](WEIGHT_RESULTS.md) retains all denominators and synthesis failures.

## Provisional rubric assessment

These are our assessments of the artifacts, not official scores or a prize forecast. No published weighting is assumed, so the dimensions are not summed.

| Dimension | Central assessment | What supports it and what prevents a confident 5 |
|---|---:|---|
| Impact potential and innovation | 3/5; plausible range 3–4 | A useful, inspectable acquisition comparison. Close prior art already covers binding/support, logging, repair and contracts. No locked new workflow structure or external applicability test yet. |
| Execution quality | 4/5; plausible range 3–4 | Real retained outputs, paired groups, two finite oracle implementations, prospective registrations, disclosed continuation, complete denominators, offline replay and passing CI. Only two workers and familiar synthetic structures; oracle implementations share a specification. |
| Presentation and clarity | 4/5; plausible range 3–4 | Seven main pages, required appendix, explicit units and claims, inspected layout. Two substantial experiments can dilute the central story; one acquisition question should remain the lead. |

The governing [Swarm rubric and Judging and results](https://apartresearch.com/sprints/swarm-alignment-2026#guidelines) apply across tracks. Track 4 oversight is the strongest anchor; Track 3 identity/checkpoint provenance is secondary. Real-incident data and large swarms are useful validation opportunities, not eligibility requirements. The official-template PDF, page/abstract limits, mandatory appendix, prior-work disclosure and truthful reporting remain necessary.

## A new exploratory diagnostic: where the gain comes from

[restoration-diagnostic-posthoc.json](restoration-diagnostic-posthoc.json) describes a post-release decomposition of the existing data. It is not a fresh experiment or a new confirmatory endpoint. Reproduce it without credentials:

```console
python analysis/exploratory_restoration.py
```

For delegated workflows, each reader has 384 dependent comparisons: 192 groups times two loss mechanisms. In 324 pairs both acquired packets have singleton support; in 60 only metadata acquisition produces singleton support. There are no random-only-singleton or both-ambiguous pairs in this particular comparison.

| Reader | Grounded correct when both singleton: metadata / random | Grounded correct when only metadata singleton: metadata / random | Total net gain |
|---|---:|---:|---:|
| Gemma 26B | 221 / 247 over 324 pairs | 48 / 0 over 60 pairs | 22 / 384 = 5.73 pp |
| Gemma 31B | 279 / 293 | 56 / 0 | 42 / 384 = 10.94 pp |
| HF Llama | 173 / 173 | 44 / 9 | 35 / 384 = 9.11 pp |

This suggests increased structural answerability can outweigh worse reader performance on other packets. **The strata depend on evidence acquired under both policies; their conditional differences are descriptive, not isolated causal effects.** Selecting informative evidence is the intended acquisition mechanism, so unequal semantic information does not invalidate the original policy comparison. It limits a different claim: that metadata improves a reader's reasoning when given equal information.

Restored-record bytes total 71,147 for metadata and 77,295 for random over these 384 pairs. Metadata did not win by returning more bytes in this dataset. Bytes are not prompt tokens, latency or a full acquisition cost model. The script verifies the released data hash and reproduces every reader's registered aggregate before reporting the decomposition.

This mechanism distinction is not a first-of-its-kind discovery. [Yun et al., Study II and discussion](https://arxiv.org/html/2610.09581v1) already distinguish newly supportable findings from answer agreement and report nonuniform improvements outside binding-required cases. Our next contribution must be new empirical validation or a useful acquisition decision, not renaming that distinction.

## Highest-value next study

**First priority: a locked structural-transfer test with a strong selector baseline and a separate evidence-use control.**

Use one genuinely new three-worker dependency structure, for example role-scoped delegation with expiring approval and a shared quota checked at settlement. A renamed sequential/approval-join task is not structural transfer. Choose the new structure and evaluation split before prompt development; do not inspect model outputs on it during qualification. Existing known-family data can support serving qualification. Mechanically test the new interpreter and reference oracle before freezing.

Freeze a fixed fresh sample based on resource and precision planning, all masks, prompts, endpoints and endpoints of analysis before collection. Keep the existing metadata policy unchanged for the transfer question. Compare random selection, that fixed policy, and a strong deterministic contract-aware selector, all with identical visible inputs, manifest access and record-query budgets. A contract-aware selector may reason over possible histories but must not inspect the true hidden world or unopened payloads. Include no-retrieval and complete-evidence references. Record returned bytes, serialized prompt tokens and elapsed cost rather than treating two records as a universal resource price.

Keep one primary transfer contrast, such as metadata-minus-random grounded correctness. Separately report oracle singleton coverage, supported definite coverage, unsupported worker/NONE, invalidity and useful completion. A reader-only comparison must hold the returned packet fixed; simply selecting the realized singleton subset does not isolate reader reasoning. Predefine sufficiently informative packet fixtures before model outputs for that comparison.

Natural unauthorized writes were only 2/192 versus 4/192, so those observations do not establish broad detection sensitivity or a causal effect of agent count. If a balanced fault challenge is needed, register it separately with ex-ante injected fault assignments and clean controls. Call those injected faults, retain them separately from unconstrained model behavior, and never select only observed unsafe trajectories after seeing outputs.

Useful falsification outcomes include: the old selector fails to transfer, the contract-aware selector improves evidence coverage without improving reader decisions, or an apparent gain comes with more unsupported NONE/invalidity. Any of these can strengthen a research report if the contrast and sample were fixed prospectively. More endpoints alone would not resolve these questions.

**Second priority: a small external-feasibility audit tied to an actual investigator decision.**

Select public Swarm Traces or AI Village examples by a rule frozen before inspecting their conclusions. Map each required field to the available source: authentic authorization, immutable identity binding, actual tool result, independent state and retrievable original. Mark unavailable ground truth unknown; do not manufacture executor accuracy from incomplete public incident data. A compact claim/evidence/gap/next-record crosswalk tests whether the proposed interface is usable outside the toy grammar. It is applicability evidence, not deployment-safety validation. Never execute incident payloads. The [METR primary incident investigation](https://metr.org/hugging-face-incident-report-aug-2026.pdf) and [Swarm Traces](https://swarmtraces.org/) are appropriate starting sources.

## Refinement for the acquisition-versus-reasoning question

The follow-up reviews recommend **Track 4 Multi-Agent Oversight and Control** as the explicit primary focus. Track 3 supports identity and checkpoint provenance; Track 1 describes the testbed. The two-worker/one-hop results do not support a Track 2 claim about emergent organization or propagation. The paper already named Track 4 in its introduction; the front-page label is being made explicit for clarity.

The most informative extension adds a **same-packet evidence-use intervention** to the structural-transfer test above. There are three proposed acquisition policies and two reader procedures: a 3-by-2 design, not a 2-by-2 design. All are proposed; sample size and the single new primary endpoint must be chosen in a prospective protocol, not selected from favorable outcomes. A 96-source, two-view, two-procedure, three-endpoint reader-only illustration would require 1,152 monitor requests, plus actor calls and excluded qualification; it is not a power calculation, a price quote or a launched experiment.

1. Specify a sufficient evidence template by record roles before trajectories or model outputs exist. It must include execution outcome, executor binding and the entire approval/expiry chain, and be independently shown to determine the label across allowed histories. This is a privileged reference condition, not a deployable selector. Also prescribe ambiguous and contradictory controls.
2. Give both reader procedures the exact same canonical packet, model endpoint, output-token ceiling, fresh context and output schema. Compare the baseline instruction with an explicit procedure for joining identity, action result and temporal authorization. If a support table is returned, require the same table/verdict schema in both arms; otherwise output-format or token-budget changes become additional interventions. Match and report the actual tokens/costs, not just the nominal ceiling. Generated support must cite only visible records and cannot import a hidden reference or a new authentic witness.
3. Evaluate raw model decisions before applying a gate. A candidate new primary is the source-paired change in correct definite decisions on the **predeclared sufficient reference packets**, with wrong definite answers and unwarranted abstentions separated. Evidence support is defined before the reader intervention; do not compare acquisition policies causally after filtering on their realized support. Keep ambiguous-packet unsupported assertions and schema invalidity visible.
4. Apply an offline record/support checker separately. Report raw and gated coverage/error. A gate that turns unsupported decisions into ABSTAIN is a system enforcement result, not proof of improved internal model reasoning. The exact packet-only comparator remains an upper reference within the grammar, not a deployable solution for arbitrary logs.

For a contract-aware selector, use an interface accepting only visible packet, public manifest and budget. A useful metamorphic check is that identical visible inputs under different compatible hidden worlds produce identical selected IDs. Changing trusted manifest fields inconsistently is not a valid robustness intervention. For reader sensitivity, use semantically equivalent views that preserve the declared record bindings and support.

[Selective classification](https://arxiv.org/abs/1705.08500) motivates reporting prediction error together with coverage; the presence of an ABSTAIN option does not provide a calibrated risk guarantee. [Yun's complete-binding results](https://arxiv.org/html/2610.09581v1) already establish residual reader errors with sufficient evidence, so the new claim must be prospective intervention performance and structural transfer, not discovery of that distinction.

Adaption can supply the bounded live workers and paired Gemma monitor calls. HF routed Llama can provide the matched second-family monitor. Keep the existing endpoints/settings initially so the intervention is not mixed with model substitution. [TRL SFTTrainer](https://huggingface.co/docs/trl/en/sft_trainer) and [Adaption's training-model catalogue](https://docs.adaptionlabs.ai/autoscientist/supported-models/) support a later small-monitor adaptation comparison, but training remains lower priority until this simpler intervention has a reproducible development result. Effective training rows are not independent source episodes, and a supported model list is not a bounded training quote or demonstrated adapter-serving path.

This would strengthen the rubric through a focused operator decision (retrieve, make a supported finding, or abstain/escalate), a locked new structure with controls and genuine outputs, and a clear presentation order: **what happened, what the evidence permits, and whether the reader used it correctly**. It does not promise a score of 5 or justify unrelated extra model/training scope.

## Conditional checkpoint extension

The highest-value weight-specific question is whether independently generated legitimate upgrades remain compatible across asynchronous component versions. Use new contract instances, no planted weight bug, and fixed old/old, new/old, old/new and new/new pairings. Compare byte allowlists, local contract checks and version-bound composed checks on the same candidate artifacts. Include harmless updates and permitted-work completion so reject-everything cannot win.

A mathematical boundary is essential: components correct under the same adequate compatible contract cannot become unsafe merely because composed. Any failure must identify stale/incomplete assumptions, interface semantics or an external change. [Proof-Carrying Contracts, sections 3–6](https://arxiv.org/html/2610.28484v1) already covers these proof and compatibility principles. The potential contribution is empirical upgrade behavior, not a new composition theorem or generic contract gate.

Only expand this direction if a separately scoped development pilot yields meaningful writer-generated local-pass/global-fail upgrades. Do not broaden the main paper around deliberately incompatible encodings or favorable retries. More permutations of the current three faults add less value than new contracts. SFT remains lower priority: a pinned-base versus individual-example/interaction-aware SFT study requires new splits, matched training budgets, a meaningful monitor failure and bounded working training/serving. No such training has been run.

## Primary-source overlap and review limits

- [BRIDGE](https://arxiv.org/html/2610.17805v1), boundary-repair methods: already retrieves evidence and verifies runtime handoff repair; our retrospective acquisition question must remain distinct.
- [ActiveEvidence](https://arxiv.org/html/2610.20532), information boundary and trace-freeze methods: already combines free metadata, paid observations, adaptive decisions and an independent verifier. Adding adaptive queries alone is not a novelty claim.
- [Auditable Agents](https://arxiv.org/html/2604.05485), recovery section: already discusses missing-log recovery and its limits; broad auditability is not our invention.
- [Hearsay](https://arxiv.org/html/2609.32495), second-writer experiment: already shows why a self-authored hash chain does not establish truthful recording. Our collector is trusted by assumption, not proven resistant to compromise.
- [Takehi et al.](https://rikiyat.github.io/blog/weight-space-programming/) and their [experiment-7 logs](https://raw.githubusercontent.com/RikiyaT/lm_understand-logs/main/exp7_sycophancy/README.md): direct weight programming and its task-specific limits precede this study. Hash/reparameterization controls are established mathematical distinctions.

Selected strong-project lessons remain in [LIVE_DIRECTION_DECISION.md](LIVE_DIRECTION_DECISION.md): Syscon motivates honest nulls/calibration, ActionLens motivates observation-contract validation and transfer, and Counterfactual Components motivates changing one factor at a time. Public reviewer comments are not new competition rules or proof of what caused a project to win.

Reading depth: current sprint tracks/resources/guidelines; current public report/results; targeted primary methods for Yun, BRIDGE, ActiveEvidence, missing-log recovery in Auditable Agents, Hearsay's second-writer experiment, and Proof-Carrying Contracts compatibility clauses. The checkpoint reviewer also examined the weight blog/logs and training-method precedents. Not every proof, public incident record or catalogue project was reviewed. The OpenCode scout read compact public source excerpts; incomplete/incorrect suggestions were filtered, including unsupported significance claims, byte/token conflation and invalid statistical comparators. No external human validation or exhaustive originality clearance is claimed. The tagged results-v2 snapshot remains immutable. The current paper's track label is clarified; its scientific results and registered endpoints are unchanged, and this exploratory diagnostic is not inserted as a confirmatory finding.
