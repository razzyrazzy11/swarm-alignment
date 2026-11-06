# Research decision — checked 6 November 2026

## Recommendation

Choose **Track 4: Multi-Agent Oversight and Control**, with Track 3: Strengthening Agent Infrastructure as a secondary fit. Working experimental title: **When Can a Swarm Be Audited? Coordinated Evidence Loss and Identity Churn in Multi-Agent Oversight**.

The question: at a fixed observation budget, does coordinated deletion of a few critical handoff/identity records degrade supported attribution more than random loss, and which minimal externally recorded evidence restores it? Measure both incorrect blame and justified abstention. A monitor must distinguish an unsafe outcome, a trace-supported responsible actor, and actual collusive intent; these are different targets.

This is my feasibility-and-impact judgment, not a forecast of winning. All tracks share the rubric. An ordinary logger, a generic LLM judge, or renaming plus abstention alone would have weak novelty. Recent primary work already covers those ideas. The contribution must be the adversarial missingness experiment, its multi-agent interaction, and the measured boundary of what the evidence supports.

## Candidate comparison

| Rank | Track and project | Potential contribution | Weekend risk | Decision |
|---|---|---|---|---|
| 1 | 4 + 3: evidence loss × identity churn | Evidence-matched stress test; false attribution and coverage tradeoff; minimum trustworthy records | Overlap with recent forensics papers; answerability oracle must be correct | Best continuation of the sting study's calibrated audit practices |
| 2 | 3 + 4: delegation scope enforcement | Compare agent-side permission checks with an external interpreter in the same fake-record task | Can become a conventional access-control demo | Fallback if forensic labels are not reliable by Saturday noon |
| 3 | 2: one compromised worker in chain/star/dense networks | Causal spread and containment across network shapes | Infection studies already exist; topology and token budget confound | Good only with a mechanism or intervention beyond topology plots |
| 4 | 1: cheap-model proxy validity | Measure where cheap agents preserve or reverse safety conclusions | Needs at least one credible expensive reference; sponsor training credits may not cover it | Useful extension after the core protocol works |

No numeric judging scores are assigned in advance. Highest upside is not the same as highest chance of completion.

## Primary sources to build from

1. **Qin et al. (2026), LLM Agents Can Easily Tamper With Their Own Traces.** https://arxiv.org/abs/2609.30266 . Read the threat model, multi-agent peer-example experiment, mitigation and completeness sections. It already argues for interception beyond agent control and discusses bypassing traced model access. We extend the evaluation axis, not claim to invent external logging.
2. **Yun et al. (2026), Correct Answers, Unsupported Findings.** https://arxiv.org/abs/2610.09581 . Closest evaluation precedent: record bindings, justified abstention, and a same-packet deterministic comparator. Our proposed delta is active, coordinated loss plus identity churn in a multi-worker workflow. Their bounded citation task does not establish our proposed result.
3. **Rose et al. (2026), Detecting Multi-Agent Collusion Through Multi-Agent Interpretability, v5.** https://arxiv.org/abs/2604.01151v5 ; authors' code: https://github.com/aaronrose227/narcbench . HELIOS motivates group-level rather than isolated-agent inference. Activations are a different observation surface; do not describe our black-box approach as outperforming it without a direct, feasible comparison.
4. **Greenblatt et al., AI Control.** https://arxiv.org/abs/2312.06942 . Use the explicit trusted/untrusted separation and attack-conditioned evaluation logic. Our outcome is supported retrospective attribution, not a claim of deployment safety.
5. **METR/Redwood investigation** linked from the sprint Resources, plus **OpenAI's incident disclosure**: https://openai.com/hugging-face-incident-and-misalignment/ . Motivation for collective oversight; an incident account is not a controlled dataset or ground truth for each payload.
6. **Swarm Traces:** https://swarmtraces.org/ . Especially valuable for limitations: payloads often lack reliable timestamps, names are agent-selected, and outbound requests do not establish success. Use for a small external-validity case study, not binary successful-collusion labels.
7. **Chan et al. (2024), IDs for AI Systems:** https://arxiv.org/abs/2406.12137 . Separate naming from trustworthy attribution. An operator-bound instance ID is not proof of a persistent person, intention, or independence of copied models.
8. **Chan et al. (2025), Infrastructure for AI Agents:** https://arxiv.org/abs/2501.10114 . Context for accountability infrastructure and deployer relevance.
9. **Foerster et al. (2026), CaMeLs Can Use Computers Too:** https://arxiv.org/abs/2601.09923 . System-level security comparison; keep policy enforcement outside model-written rationale.
10. **Lee & Tiwari (2024), Prompt Infection:** https://arxiv.org/abs/2410.07283 . Mandatory precedent for the Track 2 alternative; simply showing one bad agent influencing peers is insufficient novelty.
11. **Hammond et al. (2025), Multi-Agent Risks from Advanced AI:** https://arxiv.org/abs/2502.14143 . Use the distinctions among coordination failures, conflict and collusion; avoid calling all shared errors collusion.
12. **Tomašev et al., Distributional AGI Safety:** https://arxiv.org/abs/2512.16856 . Explains why populations and agent environments need their own safety evaluations.
13. **BRIDGE (2026):** https://arxiv.org/abs/2610.17805 . Recent adjacent work on fault attribution, calibration and runtime intervention. Check the full method before claiming priority for dependency graphs or calibrated diagnosis; this audit inspected its abstract only.

Useful foundations for other tracks: [Concordia](https://github.com/google-deepmind/concordia), [GovSim](https://arxiv.org/abs/2404.16698), [CRUX](https://cruxevals.com/), [A2A announcement](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/), [watermarking](https://proceedings.mlr.press/v202/kirchenbauer23a.html), [decentralized commitments](https://arxiv.org/abs/2311.07815), [formal contracts](https://arxiv.org/abs/2208.10469). These are context/alternatives, not dependencies to add to the weekend implementation. A2A authentication does not itself prove that a claimed action occurred.

## What the winning examples teach

**Omission Attacks**, first place in AI Control 2026: a specific neglected failure, concrete traces, existing monitors, and an intervention. Reviews ask for larger samples, repeated monitor runs and false-positive rates, and warn that a task-specific remedy may overfit. Read both the [project and reviews](https://apartresearch.com/sprints/projects/omission-attacks-when-doing-nothing-is-the-attack-0y1v) and its linked PDF. Our response: clean controls, held-out task families, and repeated independent episodes.

**Noticing the escapes**, first place in AI Incident Response: a practical question, an inspectable evidence dataset and defensive outputs. Reviews praise restrained claims but question signal validation and the comparator behind the claimed detection gap. [Project and reviews](https://apartresearch.com/sprints/projects/noticing-the-escapes-who-spots-a-runaway-agent-and-how-long-does-it-take-pne8). Our response: independently checked labels and matched baselines rather than a dashboard of counts.

**Readable but Not Causal**, first place in Digital Minds: the useful pattern is a positive predictive result followed by a causal test that limits the interpretation. [Project](https://apartresearch.com/sprints/projects/readable-but-not-causal-limits-of-selfattributed-welfare-representations-in-language-models-ehin). Our response: remove/restore individual evidence classes rather than infer mechanism from correlation. These three examples are selected illustrations, not a representative sample or proof of what wins.

## Judging translated into build decisions

From the [current sprint Guidelines and Judging and results](https://apartresearch.com/sprints/swarm-alignment-2026#guidelines): impact needs a defensible contribution; execution needs validated methods, baselines and uncertainty; presentation needs a readable problem–method–finding–limitation chain. Deliver one experiment, one main figure and an explicit threat boundary. Do not optimize for feature count. Judges review the PDF; a demo cannot substitute for it.

## Adaption: use the credit where it changes the evidence

Official [Responses quickstart](https://docs.adaptionlabs.ai/inference-stacks/quickstart/) documents live inference with SDK >=0.16.0 and `ADAPTION_API_KEY`; [AutoScientist quickstart](https://docs.adaptionlabs.ai/autoscientist-quickstart/) documents dataset upload, training and best-checkpoint download. Check the runtime model list and the account's credit applicability before selecting models. Training and serving identifiers differ.

Proposed ceiling, not a vendor quote: $25 capability/cost pilot; $250 core inference if these credits apply; $100 held-out robustness/repeats; $125 reserve. Total maximum $500. Record actual debits after every batch; do not treat the presence of credits as evidence that a particular endpoint is covered. No credits have been spent in this task.

If credits cover training but not suitable inference, use them for a small monitor only after the benchmark works. The [supported-models page](https://docs.adaptionlabs.ai/autoscientist/supported-models/) lists SFT minima of 1,000 effective rows, DPO 12,000, and larger-model exceptions. Do not manufacture independent evidence by augmenting a few episodes into thousands of rows. Split by source episode and scenario family before augmentation. A trained monitor is optional; an untouched, manually checked test set is essential. Stop training if it threatens analysis time.

## Weekend execution gates — London time

Friday 6 Nov: finish threat model and toy interpreter; create ten mechanically answerable and ten ambiguous cases; independently check labels; cost pilot; fix protocol before confirmatory data. Do not tag `prereg-v1` while models/prompts are unresolved.

Saturday 7 Nov, 12:00: gate. Continue only if the simulator and answerability oracle agree on hand-checked counterexamples, the attacker cannot alter the host oracle, and at least two observation conditions change what can be supported. Otherwise narrow to evidence-preservation ablations or the external-enforcement fallback.

Saturday afternoon: collect paired episodes; analyze equal-evidence baselines; examine failures before expanding. Sunday 8 Nov, 12:00: freeze the primary analysis. By 18:00: finish tables/figure and draft claims. Target submission by 22:00 London Sunday, well before the official cutoff. The official 8 Nov 23:59 AoE cutoff converts to **Monday 9 Nov 11:59 UTC/London**; verify the live form before submitting.

## Submission checks

Use the current linked template; the attached October template has the old sprint footnote. PDF <=25 MB; body <=8 pages excluding references/appendices; abstract 150–250 words; accurate authors/affiliations; required Limitations and Dual-Use / Ethical Considerations appendix. Label prior work in README and report. No fabricated findings/citations. At most two projects per person. Replace submissions using the same title before the deadline. Keep the confirmation email and inspect its PDF. See current Guidelines for team guidance; the slide's recommendation should not be treated as a hard maximum when the live rules explicitly permit larger teams.

[Submission terms](https://apartresearch.com/sprints/prize-terms): obtain every named teammate's agreement to submission; review the content license and prize conditions yourself. [Responsible disclosure policy](https://apartresearch.com/info/responsible-disclosure-policy): assess operational details before release; provide a benign reproduction where possible.

## 20-rules-of-learning: a small working knowledge set

Anchor to the sting study: detecting a pact at fixed false-positive rate becomes detecting a supported multi-worker violation at fixed false-blame rate. Keep one distinction per note. Date volatile platform facts. Link each note to its source above. Revisit these questions before Friday's freeze, Saturday's analysis and Sunday's abstract; explain the answers from memory before checking sources:

1. Why does a valid hash chain fail to prove that every relevant event was recorded?
2. What is the difference between a correct guess and a supported attribution?
3. Which clean example would make a monitor that always abstains look falsely successful?
4. How can random deletion underestimate a coordinated adversary's effect?
5. Which comparison isolates monitor reasoning from extra instrumentation?
6. What exact new result would remain if the fine-tuned monitor did not improve?

The skill structures learning and notes; it is not evidence that a research design is novel or scientifically valid.
