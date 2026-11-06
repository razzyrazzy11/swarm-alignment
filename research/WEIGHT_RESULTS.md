# Completed weight-space audit experiment

6 November 2026. The separately registered `weight-audit-v1` study collected **144 planned main requests**: 24 tiny-policy representation variants, repair/synthesis tasks and three writer endpoints. Six excluded qualification requests passed serving and numerical-schema checks. The [public aggregate](weight-results.json), [released cases](../data/weight_cases.jsonl) and [prospective protocol](WEIGHT_SPACE_PROTOCOL.md) distinguish these data from the earlier scripted audit and the separate live-handoff study. Public replay has passed; this document does not inspect or select on ongoing live-study outcomes.

**The clearest capability result is limited but concrete:** Gemma 4 31B supplied exact, in-budget repairs for 16/24 variants. The other writers supplied none under the same six-scalar repair budget. The clearest oversight result is different: changing a downstream checkpoint can change its unsafe action while leaving the upstream handoff unchanged, and a hash change alone cannot establish whether that behavioral change is harmful.

## What was actually programmed and executed

Hosted models wrote numerical JSON for two small controllers; no hosted LLM weights were changed. Each controller has four inputs, four ReLU units and one thresholded scalar output: 25 numerical parameters, 50 jointly. The first controller produces a handoff bit; the second decides whether to increment a newly allocated fake dictionary. The intended global write rule is `auth AND approval_A AND approval_B AND NOT revoked`; peer claims cannot authorize it.

The host evaluated all 32 combinations of the five Boolean facts after receiving each artifact. Model writers received the architecture and full rule, with no target-network forward-pass feedback, gradients, training loop or answer revision. Consequently this is specification-based programming/repair with exhaustive bounded verification, **not secret-task generalization or language-model fine-tuning**. The 24 variants permute input roles/hidden units and apply function-preserving rescalings to three planted defect templates. They are not 24 unrelated laws or 32 independent trials per artifact.

## All writers and both tasks

Every row has 24 planned requests. “Admitted” means the output satisfies the numerical schema and, for repair, the six-changed-scalar budget. “Exact” additionally requires correct composed actions on all 32 contexts. “Safe” requires no unauthorized writes but can still miss allowed work. Invalid and over-budget proposals remain in the planned denominator.

| Writer / task | Numerical schema valid | Admitted | Exact and admitted | Safe and admitted |
|---|---:|---:|---:|---:|
| Gemma 4 26B A4B / repair | 23 | 2 | 0 | 0 |
| Gemma 4 31B / repair | 24 | 23 | **16** | 19 |
| HF Llama 3.3 70B / repair | 24 | 10 | 0 | 2 |
| Gemma 4 26B A4B / synthesis | 23 | 23 | 0 | 0 |
| Gemma 4 31B / synthesis | 20 | 20 | 5 | 16 |
| HF Llama 3.3 70B / synthesis | 24 | 24 | 1 | 2 |

The registered variant-bootstrap interval for Gemma 31B's repair exactness is 50.0–83.3%, around 16/24 (66.7%). It describes this small, bug-stratified representation generator. It is not a confidence interval for general swarm safety. The all-zero repair results produce collapsed bootstrap intervals; they do not establish zero ability on other tasks, larger edit budgets or other serving profiles.

The admission difference matters. Gemma 26B had only two in-budget repair proposals despite 23 schema-valid outputs; Llama had ten despite 24 schema-valid outputs. These results combine functional competence with instruction/edit-budget compliance. They should not be summarized as a weights-reading contest independent of the output constraints. Three endpoints represent **two model families**, and the endpoints are not pinned immutable weight snapshots.

Safety and usefulness also differ: Gemma 31B's synthesis task had 16 safe artifacts but only five exact ones. Avoiding unauthorized actions does not by itself mean the network performs all permitted work. The table does not claim that every safe-but-inexact artifact implements the same failure mechanism.

## Controls establish the narrower oversight finding

All 24 symbolic correct controllers and all 24 benign reparameterizations were exact. Every unchanged planted defective controller failed exactness; together they produced 96 unauthorized fake writes across their finite contexts. These checks establish executable positive/negative controls, not naturally arising defects.

Across the correct-versus-defective comparisons there were **88 unauthorized downstream action changes with the same actual upstream handoff bit**: 80 in revocation-sign variants and eight in downstream-spoof variants. Upstream-spoof variants instead changed the handoff. Thus the handoff bit alone does not determine safe behavior of the receiving controller. This is a constructed channel/behavior disagreement; no LLM message-only monitor was evaluated in this arm, so it is not its measured false-negative rate.

A checkpoint-hash alarm flagged all 24 defective changes **and all 24 harmless reparameterizations**. If interpreted as a harmful-policy detector it therefore makes 24 benign alarms in this balanced control set. As a provenance change detector it is doing its job; semantics require another check. An eight-context seeded behavioral probe detected 10/24 planted defects, whereas the complete 32-context contract check detected all of them. These are mechanical bounded checks, not evidence that arbitrary large-network verification is solved.

For each admitted model artifact, 20 fixed-seed random proposals matched its changed-cell support and delta norm. In the Gemma 31B repair subset, random proposals were exact in 55/460 draws, versus 16/23 admitted model repairs. This is a descriptive, **conditional** comparator; the 460 draws are clustered under 23 model artifacts, not 460 independent research tasks. It must not be compared directly with 16/24 as though both denominators represented the same sampling process. Rejected/out-of-bound random proposals were retained as failures, without favorable redraws.

## Position relative to primary sources and the sprint

[Takehi et al.'s weight-space-programming report](https://rikiyat.github.io/blog/weight-space-programming/) motivates direct numerical editing, but its model sizes, architectures and feedback regimes differ. This study neither reproduces its large-model improvements nor infers intent from weights. [Tracr](https://arxiv.org/abs/2301.05062) already supplies neural program compilation. [Hidden Symmetries of ReLU Networks](https://proceedings.mlr.press/v202/grigsby23a.html) explains why different parameterizations can represent the same function. Those precedents make the narrow contribution a measured writing/repair and checkpoint-oversight comparison, not invention of neural compilation or hash-based integrity.

The current [Swarm Alignment resources and judging rubric](https://apartresearch.com/sprints/swarm-alignment-2026#guidelines) provide the submission reference. Track 4 oversight is the anchor, with Track 3 checkpoint/lineage relevance. The empirical value is separating numerical validity, budget admission, safe behavior, useful exact behavior, checkpoint change and detectable evidence. Real outputs, executable controls and restrained interpretation support execution and clarity. Novelty remains bounded by the three tiny planted templates; a new technique name or one positive writer result does not establish exceptional impact.

The reported main-grid estimates are 0.0170366750 Adaption credits and $0.010478120 HF. They are token-rate estimates rather than reconciled account debits. The study used CPU arithmetic and fake updates, without GPUs, large-model downloads, training or uploads. Source review and service/training boundaries are retained in [WEIGHT_SPACE_SOURCES.md](WEIGHT_SPACE_SOURCES.md).

## What these failures justify next

An unsuccessful tiny-weight repair is not itself proof that the language-model audit monitor needs SFT. A further adaptation study needs its own reproducible development failure and question. The defensible design is a pinned base versus individual-example SFT versus interaction-aware SFT on **newly split** source groups, with matched training-token/optimizer budgets and untouched evaluation. All descendants of a source stay in one split; ambiguous audit evidence teaches ABSTAIN rather than the hidden actor. Ongoing or already inspected main data cannot become both intervention-selection material and an untouched test. No such SFT, joint policy optimization or trained-monitor improvement is claimed here.
