# Follow-up decision from the measured weight experiment

6 November 2026. This is a post-study decision memo, not an amendment to a frozen protocol or a claim that training has occurred. It uses the completed [weight results](weight-results.json), without inspecting ongoing live-study outcomes.

## First preserve the distinction the data establish

A receiving controller can change its action while its incoming handoff bit stays unchanged. The constructed controls contain 88 such unauthorized changes. Conversely, all 24 harmless reparameterizations changed checkpoint hashes while preserving correct behavior. A hash is therefore useful provenance evidence, but it does not establish harmful behavior or intent.

The 144 actual writer requests also show that a well-formed artifact is insufficient. Gemma 31B returned 16/24 exact in-budget repairs; the other two endpoints returned none. Synthesis produced only 0/24, 5/24 and 1/24 exact artifacts. Safety, usefulness, numerical validity and budget compliance remain separate. These are fifty-scalar controllers and three planted defect templates, not directly edited hosted LLMs or a general weights-only swarm-intent detector. Full limitations and denominators are in [WEIGHT_RESULTS.md](WEIGHT_RESULTS.md).

The strongest immediate direction is **checkpoint-aware behavioral auditing**: retain checkpoint identity and authorized-change provenance, then test the declared global action contract and permitted-work completion. Keep function-preserving changes as negative harm controls. A bounded behavioral probe can miss a defect; an exhaustive check is an upper reference only in this finite domain. This is a more defensible conclusion than treating every changed checkpoint as malicious.

## Four different ways of changing a system

| Method | What changes | Interpretation here |
|---|---|---|
| Direct weight programming | A writer supplies numeric parameters without a target-network gradient loop | The completed tiny-controller study |
| Ordinary SFT | A model learns target responses from individual examples | A possible local policy or audit skill intervention |
| Interaction-aware SFT | SFT examples include role/handoff histories and supported trajectory/evidence labels | A test of whether interaction context improves learning beyond individual examples |
| Joint multi-agent optimization | Interaction outcomes inform policy credit assignment and updates | Requires its own rollout, reward and evaluation design |

LoRA selects an efficient trainable parameterization; it is not itself a swarm-learning method. [HF PEFT](https://huggingface.co/docs/peft/en/quicktour) documents adapters and base-plus-adapter inference. [TRL SFTTrainer](https://huggingface.co/docs/trl/en/sft_trainer) supports conversation/completion datasets and loss masking. A gradient-trained baseline on the tiny numerical controller would still be a tiny-policy baseline, not language-model SFT.

[MALT](https://arxiv.org/html/2412.01928v2) already derives role-specific training from generator/verifier/refiner trajectories and downstream rewards. Its roles are updated independently with interaction-derived credit; this is not simultaneous gradients through an entire swarm. No claim of originating multi-agent training follows from adding a shared adapter or several roles.

## One conditional training comparison, with a new test set

If separate development data demonstrate a meaningful **monitor** failure, compare the same pinned small base against individual-example SFT and interaction-aware SFT. A failed weight repair alone does not establish that monitor failure. Match base checkpoint, adapter rank, optimizer and training-token budgets; report context-length and source-count differences. Evaluate the same evidence views and exact/abstention baselines, keeping unsupported worker/NONE, invalidity, definite coverage and task usefulness visible.

Assign new source groups to training, validation and locked testing **before** projection or augmentation. All handoff variants, aliases and paraphrases from a source remain in one split. Use validation for selection; test once. Ambiguous audit evidence requires ABSTAIN targets, not the hidden actor. Already inspected main data can motivate a question but cannot also be its untouched evaluation set.

## Service gates and scope

Adaption inference can supply writers and teachers; its documented Responses interface does not expose direct modification of hosted base weights. [AutoScientist downloads](https://docs.adaptionlabs.ai/autoscientist/download-the-model/) provide trained checkpoint archives, typically including LoRA artifacts. That does not establish serving of arbitrary edited weights through an existing hosted model ID.

Require a bounded training charge and working base/adapter inference before launch. [AutoScientist creation has no estimate mode](https://docs.adaptionlabs.ai/tools/mcp/); an iteration limit is not a monetary cap. HF inference credits or Pro status do not reserve training hardware. No GPU job, training launch, top-up or new spending follows from this memo.

This sequence keeps the [Swarm judging rubric](https://apartresearch.com/sprints/swarm-alignment-2026#guidelines) central: extract a narrow, checkable oversight finding from actual data, then test one justified intervention. It preserves execution quality and clarity while avoiding a collection of unvalidated techniques under a broad swarm-programming label.
