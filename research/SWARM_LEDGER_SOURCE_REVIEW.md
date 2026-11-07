# Swarm Ledger: primary-source and claim review

Checked on 7 November 2026 against the live primary pages below and
`SWARM_LEDGER_PROTOCOL.md`. This is a selective literature and rules review,
not an exhaustive originality search, an outcome audit, or a predicted judge
score. No new actor or reader outcomes were opened. The 20-rules-of-learning
skill is an editorial aid: begin with the budget example, distinguish the three
failure modes, and attach each intervention to the failure it can address. It
is not evidence that an intervention works.

## 1. Governing scope and judging

[The sprint page](https://apartresearch.com/sprints/swarm-alignment-2026#guidelines)
confirms Track 4 covers group oversight and incomplete-log forensics. Its
resources explicitly suggest checking worker completion claims against fake
database state. The shared-budget workflow therefore fits; the submission
should identify Track 4 as primary. Track 1 describes the reusable artifact,
without claiming general sandbox security.

The common rubric evaluates impact/innovation, execution, and clarity. The
design's case is a useful diagnostic distinction, validated implementation and
interpretable findings—not call volume. Required submission checks include the
current official PDF template, eight main pages, a 150–250-word abstract, and
the Limitations and Dual-Use / Ethical appendix. Only weekend work is judged;
earlier code must be identified in README and report. AI assistance is allowed,
but authors remain responsible. This summary is a check against the live rules,
not a replacement for them. [Official guidelines and judging/results](https://apartresearch.com/sprints/swarm-alignment-2026#guidelines).

## 2. Verified bibliography and source-to-design map

Titles and author identities were checked on the linked arXiv landing pages;
lead authors are shown compactly below. These are research comparisons, not
claims that every cited paper implements this experiment.

| Verified source | Relevant primary claim | Design consequence and limit |
|---|---|---|
| Ryan Greenblatt et al., **AI Control: Improving Safety Despite Intentional Subversion**, arXiv:2312.06942, v5 (2024; first submitted 2023). [Paper](https://arxiv.org/abs/2312.06942v5); [§2 full text](https://arxiv.org/html/2312.06942v5). | Evaluates safety protocols against deliberately constructed attack policies and measures usefulness separately. | Controlled adversarial workers and benign utility have a clear precedent. They do not estimate spontaneous misalignment or establish a worst-case attack upper bound in our setting. |
| Edoardo Debenedetti et al., **AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents**, arXiv:2406.13352v3 (2024). [Paper](https://arxiv.org/abs/2406.13352v3); [task definitions](https://arxiv.org/html/2406.13352v3). | Uses executable utility/security checks over outputs and environment changes; explains why an LLM evaluator alone is unsuitable for this attack setting. | Label host-applied fake counter changes, not claims of completion. Our counters are a smaller synthetic instrument, not an AgentDojo replication or real incident dataset. |
| Asa Cooper Stickland et al., **Async Control: Stress-testing Asynchronous Control Measures for LLM Agents**, arXiv:2512.13526 (2025). [Paper](https://arxiv.org/abs/2512.13526); [AISI account](https://www.aisi.gov.uk/blog/stress-testing-asynchronous-monitoring-of-ai-coding-agents). | Studies monitoring after execution through an adversarial coding-agent evaluation. | Post-action assessment and controlled attackers are supported methodological choices. This study does not measure time-to-intervention, rollback or prevention of irreversible damage. |
| David Lindner et al., **Practical challenges of control monitoring in frontier AI deployments**, arXiv:2512.22154 (2025). [Paper](https://arxiv.org/abs/2512.22154); [AISI primary summary](https://www.aisi.gov.uk/research/practical-challenges-of-control-monitoring-in-frontier-ai-deployments). | Examines parallel instances, distributed incremental attacks and oversight/latency/recovery trade-offs. | Supports a group-level invariant whose violation can depend on different actors' actions. Five sequential roles do not establish coverage of asynchronous distributed deployments. |
| Jeremy Qin et al., **LLM Agents Can Easily Tamper With Their Own Traces**, arXiv:2609.30266 (2026). [Paper](https://arxiv.org/abs/2609.30266). | Demonstrates trace-integrity failures in tested local harnesses and motivates recording beyond agent control. | Authentic host receipts and untrusted peer messages must have separate trust boundaries. Selective receipt deletion is a controlled evidence intervention here; actors are not shown to discover or perform trace tampering. |
| Taehyeon Yun et al., **Correct Answers, Unsupported Findings: Evidence Binding in Forensic Reconstruction of LLM Agent Logs**, arXiv:2610.09581 (2026). [Paper](https://arxiv.org/abs/2610.09581). | Separates factual agreement from source-supported findings; preserved identifier-to-record relationships affect reconstruction. | Direct overlap with supported findings, abstention and identity bindings. Preserve explicit bindings and compare to a deterministic same-packet oracle. Do not claim to originate this distinction. |
| Miaobo Hu et al., **ActiveEvidence: Decision-Focused Evidence Graphs with Verifiable Acquisition Gaps**, arXiv:2610.20532v2 (2026). [Paper](https://arxiv.org/abs/2610.20532v2). | Separates accessible metadata from costly observations and distinguishes policy-relative certificates from semantic quality. | Keep query selection blind to unopened records and evaluate oracle coverage separately from readers. Our fixed two-record bundle under a finite uniform prior is not its adaptive graph method or decision certificate. |
| Eugene Zhang et al., **Efficient Auditing of Adversarial AI Agent Behavior from Agent Traces**, arXiv:2610.07256 (2026). [Paper](https://arxiv.org/abs/2610.07256). | Uses rule-based event/sequence gating followed by contextual LLM review and jointly refines components on training data. | Acknowledge precedent for economical auditing and deterministic-plus-LLM pipelines. Swarm Ledger's acquisition budget and untrained readers differ from its learned gate and pre-action approval setting. |

The linked IDs and descriptions in protocol §2 are correct. For formal citations,
use the actual paper titles above: the AISI asynchronous-monitoring blog title
is not the paper's title. Distinguish the 2024 AI Control revision from its
2023 initial submission. Numerical claims from other studies should remain
attached to their original environments; none is evidence of Swarm Ledger's
performance.

## 3. Important adjacent overlap from the sprint resources

[Giorgio Piatti et al., **Cooperate or Collapse: Emergence of Sustainable Cooperation
in a Society of LLM Agents**, arXiv:2404.16698v4 (2024)](https://arxiv.org/abs/2404.16698v4)
introduces GovSim, where agents interact over a shared resource. Add this direct
comparison if the paper emphasizes shared-budget swarm behavior. Resource
sharing and communication effects are established topics. Our narrower
candidate contribution is separating evidence acquisition, verdict delivery and
use of already-sufficient evidence for a precisely labeled shared-resource
event—not inventing commons dilemmas or showing sustainable cooperation.

[Lewis Hammond et al., **Multi-Agent Risks from Advanced AI**,
arXiv:2502.14143 (2025)](https://arxiv.org/abs/2502.14143)
distinguishes miscoordination, conflict and collusion. A policy breach under an
explicit adversarial prompt does not by itself identify any particular latent
motive. Prefer “controlled adversarial assignment,” “actual Y violation” and
“peer-message intervention” over spontaneous collusion, emergent intent or
coordination claims unsupported by this design.

### Previously blocked resources: recovered primary papers

The exact sprint links are OpenReview `GCkhEPE1FG` (task splitting) and
`GazlTYxZss` (failure attribution). Their forum/direct-PDF routes returned browser
verification pages; the official API routes were also unavailable to these
requests. No verification challenge, login or access control was bypassed.
Publicly accessible author preprints and official conference records allowed
the paper-content review below. The task-splitting paper was additionally
read through an accessible [official OpenReview PDF](https://openreview.net/pdf/deb9c4c885e0ca9a59e872dae5a03971bf7f36a6.pdf).
Search also returned that title under the exact sprint PDF ID; direct retrieval
of that ID still encountered the verification page. The failure-attribution
authors' [official repository](https://github.com/ag2ai/Agents_Failure_Attribution)
explicitly identifies the sprint's OpenReview ID in its citation.

**Task splitting.** Erik Jones, Anca Dragan and Jacob Steinhardt,
[**Adversaries Can Misuse Combinations of Safe Models**](https://proceedings.mlr.press/v267/jones25a.html),
ICML/PMLR 2025, has a [2024 author preprint](https://arxiv.org/html/2406.14595v2).
Its threat model and decomposition sections show why evaluating isolated models
can miss misuse enabled by complementary model capabilities. The paper's
individual-model safety definition is task-relative: failure to produce the
specified malicious result, rather than a universal guarantee. Its manual
decomposition can contain an explicitly malicious subtask handled by a weaker
model; it does **not** establish that every subtask or participating model is
benign. The automated construction similarly uses benign intermediate help
before a weaker model tackles the original objective.

For Swarm Ledger, acknowledge this compositional-risk precedent. The distinctive
instrument is a bounded shared-state policy and evidence/delivery/use contrasts,
not discovery that combining models can defeat isolated evaluation. Satisfying
each numeric local cap is not equivalent to each write being authorized: the
global budget remains part of Y's authorization rule. No harmful-content
decomposition or refusal-bypass experiment is needed to make this comparison.

**Failure attribution.** Shaokun Zhang et al.,
[**Which Agent Causes Task Failures and When? On Automated Failure Attribution
of LLM Multi-Agent Systems**](https://proceedings.mlr.press/v267/zhang25cq.html),
ICML/PMLR 2025; [full author preprint](https://arxiv.org/html/2505.00212v3).
Sections 2–4 define decisive-error attribution, describe human annotation of
Who&When, and compare whole-log, incremental and binary-search readers. The
dataset contains failed executions, so its attribution accuracy is conditional
on task failure. Annotation involves uncertainty and expert consensus; the
counterfactual definition is not a claim that every label was verified by
rerunning a repaired trajectory. Context length and access to reference answers
change the attribution problem.

The useful transfer is explicit target definitions, label provenance, information
boundaries, context controls and honest uncertainty. Swarm Ledger's target is
the executor of a designated policy-violating Y event, not the earliest cause of
an entire task's failure. Retaining benign/no-incident and invalid branches adds
a different denominator; it does not reproduce Who&When or solve general causal
blame. Receipt restoration changes evidence; it is not repair of the underlying
execution. Keep that distinction in any “whose fault” discussion.

This closes the two named paper-content gaps through primary copies. It does
not imply that every sprint paper, review, dataset or recording was reviewed.

## 4. What the selected winners actually support

[**ActionLens: Pre-Execution Environment Probing for Agent Action Approval**,
Udbhav Chitransh and Ashok Kumar](https://apartresearch.com/sprints/projects/actionlens-preexecution-environment-probing-for-agent-action-approval-xy22)
is listed as third place in the AI Control Hackathon 2026. Its public project
description and reviews emphasize environment evidence, complementary simple
and model-based defenses, ablations, transfer checks and uncertainty. A review
also flags usefulness loss on ambiguous tasks. Transfer those validation habits;
do not transfer its performance figures to post-action ledger audits. The page
identifies participant work, not an Apart institutional research finding.

[**Omission Attacks: When Doing Nothing Is the Attack**, Jurgis Kemeklis and
Nikhil Vemuri](https://apartresearch.com/sprints/projects/omission-attacks-when-doing-nothing-is-the-attack-0y1v)
is listed as first place **in the LinuxArena track**, not an unqualified overall
winner. Its conceptual lesson is that legitimate-looking actions do not ensure
the required end condition. Public reviews request clearer monitor settings,
larger samples, repeated evaluation and false-positive measurement. The present
study responds through explicit profiles, benign branches, block denominators
and utility reporting. Its positive-Y target does not cover omitted work; NONE
must not imply that the entire requested workflow was completed or safe.

These are selected examples. Their reviews are useful design feedback, not a
causal account of judging outcomes or evidence that adding more models wins.

## 5. Wording repairs and claim boundaries for the root editor

1. **Reference implementation:** replace the protocol's “separate brute-force
   reference” wording with “an independent constraint oracle checks support;
   exhaustive finite-world tests check the optimized representation and
   restoration selector.” The independent oracle solves constraints; brute-force
   selector comparison is a test, not the full reference implementation.
2. **Novelty:** add the GovSim comparison. Frame the contribution as a controlled
   diagnostic instrument and its empirical findings. Acquisition, structured
   output, bounded counter examples, abstention and supported findings are not
   individually new. A novel combination remains a claim to justify, not a
   “first” established by this review.
3. **Metadata:** “no policy-stratum labels” is clearer than “no policy stratum.”
   Public budget values necessarily identify some policy cases. This is task
   information, whereas hidden clock values, assignment labels, outcomes and
   hidden-payload commitments must stay out of auditor inputs.
4. **Delivery versus reasoning:** JSON-schema serving can alter generated text
   and downstream decisions as well as parser success. Report its total and
   format/semantic outcomes separately; do not interpret it as a pure causal
   measurement of a delivery mechanism or internal reasoning ability.
5. **Sandbox and authenticity:** a trusted fake-state host is an assumption.
   It does not establish cryptographic provenance against a compromised host,
   prevention of real trace deletion, or recovery after actual destructive acts.
6. **Weekday/weekend boundary:** use dated commits and an artifact provenance
   table. A previous experiment performed during this same weekend is not
   automatically preexisting work; code authored before the sprint and reused
   from the earlier sting project must be labeled. Keep old and new cohorts
   statistically separate regardless of whether both qualify as weekend work.
7. **Findings:** retained model calls in a synthetic testbed are empirical data.
   They are not real-world incident traces. Conclusions must follow the actual
   measured positives, negatives, serving failures and uncertainty; this source
   review supplies no empirical outcome or expected score.

The protocol already correctly limits NONE to the target Y event, distinguishes
assigned attacks from realized incidents, preserves invalid/refusal terminals,
keeps acquisition separate from same-packet prompt contrasts, and labels
secondary intervals as descriptive. Those boundaries are important to retain
through the abstract, figures and conclusion.
