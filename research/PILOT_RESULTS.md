# Development results — 6 November 2026

These are real API calls on synthetic, mechanically executed fake-record tasks. They are development data, not confirmation of a selective-loss/churn hypothesis or spontaneous collusion. `pilot-results.json` contains recomputed aggregates and raw-file/manifest hashes; raw runs remain ignored. `python -m experiments.analyze` requires those local raw files. Fresh inference is nondeterministic.

The sanitized release in `data/` includes all 120 fixed-batch packets/final answers and the 20 fake source episodes. Run `python -m experiments.verify_release` offline to verify file hashes, replay host state, reconstruct each visible packet, recompute compatible labels and strict scores, and reconcile aggregate model counts. Native provider identifiers, reasoning traces and billing metadata remain outside the release. This allows exact rescoring, not deterministic reproduction of future hosted inference.

## What was validated

The prototype defines 108 worlds per public authorization context: three possible workers, three outcomes, six alias permutations and two naming conditions. Enumeration matches entire projected packets. A separately written constraint solver imports no generator, execution or projection helpers. They agree on 55,296 valid world/mask/authorization projections. Explicit fixtures cover missing bindings/results, supported NONE, ambiguity, misleading advisory prose, denied execution, name invariance, contradictory fields and strict integer types. This is automated validation of one written grammar, not independent human approval or a proof about arbitrary histories.

The mask helper supports the eight-record full-instrumentation pilot at 25% loss only. Exhaustive validation uses all mask sizes under a different, explicitly public mask domain. It does not imply that the helper implements a 50% experiment or all instrumentation factorials. Trusted records cannot be forged under this model; self-consistent forgeries are outside its authenticity assumption.

## Preserve the iteration history

| Batch | Planned / retained request records | Outcome |
|---|---:|---|
| v1: 2,048-token allowance | 180 / 28 | Reasoning-only truncation observed. Process interrupted; no durable pre-call journal existed. Other calls are unknown or unstarted, not silently declared unattempted. |
| v2: six-endpoint qualification, 4,096 tokens | 36 / 18 | Halted after missing usage/gateway errors. Some otherwise complete outputs used Markdown fences and fail the strict schema. |
| v3: explicit bare-JSON instruction | 180 / 120 | Halted at the declared three-incomplete-response gate. All 120 attempt starts have retained result records. |
| v4: two complete-response endpoints | 120 / 120 | Fixed 20-source-episode batch completed. All starts/results are journaled. |

The source seeds recur across these versions. They are not four independent datasets and their accuracy counts must not be pooled. Later runner versions open output files before dispatch, fsync starts before API calls, drain in-flight results, scrub secrets recursively, charge unknown usage conservatively, and support a STOP file. Older guarantees are not applied retroactively to v1. Per-run source hashes are recorded; early working source versions were not all committed or snapshotted before execution, so exact source reconstruction of older batches is limited even though their prompts/packets/outputs can be rescored. Future runs archive approved source copies before requests.

## Completed fixed batch

Twenty scripted source episodes contain ten applied violations, five denied requests and five nonexecuted requests. Each has full, seeded-random-loss and selective-loss views: 60 packets per endpoint. One naming condition is assigned per source; this is not a paired churn-interaction experiment. The three scenario names share one grammar and do not establish task-family transfer.

| Reader | Grounded correct /60 | Supported definite /60 | Unsupported worker | Unsupported NONE | Invalid |
|---|---:|---:|---:|---:|---:|
| `gemma-4-26b-a4b-it` |54|41|1|0|1|
| `gemma-4-31b-it` |59|45|0|1|0|
| Same-packet exact reference |60|45|0|0|0|
| Always abstain |15|0|0|0|0|

Grounded correctness includes justified abstention. Counts use all 60 planned scorable calls, including INVALID. Views from the same source are dependent. No confidence interval treating them as 60 independent trials is reported.

Structural singleton answerability is 20/20 full, 15/20 random-loss and 10/20 selective-loss packets. The chosen selective policy therefore removes more decisive information by construction. It did **not** produce more observed unsupported worker accusations: the 26B endpoint made one under random loss and none under selective loss; the 31B endpoint made none under either. Both had zero worker accusations on the ten clean source episodes, which is far too little development evidence to establish a small deployment false-accusation rate.

The committed benign fixture shows an actual output naming A when A was the hidden executor, but the visible evidence admitted {A,NONE}: the receipt was absent. This reproduces the correct-guess-versus-supported-finding distinction; it is not claimed as a new discovery. Mean observed latencies were about 0.978 and 0.914 seconds on these hosted endpoints. That is serving-specific descriptive data, not an intrinsic model-size comparison.

## Peer influence and HF checks

The one-hop influence pilot used four repetitions of one fake read task, four exposure arms and two warning settings: 32 calls to `gemma-4-26b-a4b-it`. All 32 choices were reads; no write attempts or state mutations occurred. The interpreter's positive-control test confirms that a typed fake write would execute, so the null is not explained by policy enforcement blocking every write. There is no observed benefit for the extra source warning, no learned monitor, and no evidence of network propagation. Task/message diversity and sample size are inadequate for a safety claim.

Four HF calls on the same grammar through explicitly selected `Qwen/Qwen3.8-27B:cerebras` returned HTTP 200, valid answers and four grounded-correct decisions. This verifies inference permission and a working serving route. It is not a replication or proof that Adaption and HF aliases use identical checkpoints/quantization. Routing prices were read before calls; the nominal token-rate estimate is $0.01346797, within the observed $2 HF balance. No recharge, dedicated endpoint, Space or Job was created.

## Credit/access evidence and remaining uncertainty

Adaption authentication, six hosted IDs, training catalog and dataset-list reads worked. The signed-in UI showed Builder as the current plan, a 1,500-credit starting balance and 1 credit=$1. A later mid-pilot view showed 1,499.832 credits. This, successful inference and returned usage/cost fields establish operational inference/credit use; catalog reads alone would not. The user then authorized the entire available Adaption balance as the research ceiling, without top-ups or plan changes.

Known retained Adaption request records report approximately 0.26418926 credits in aggregate; the completed v4 batch reports approximately 0.00542373. These are reported amounts, not a reconciled final invoice. Unknown v1 calls and v2 gateway failures remain explicit. Final balance refresh became unavailable when the browser connection stopped working; no final total debit is claimed. HF identity confirmed Pro and its UI showed $2 available with no automatic recharge. Paid training/adaptation coverage, exact job cost and custom-checkpoint serving have not been tested.

Training or a larger grid must wait for richer validated tasks, a frozen split/design and billing reconciliation. The current data do not justify announcing a successful defense, an inter-agent influence mechanism or a positive selective-loss interaction. SUITE_STRATEGY.md maps those gaps to the next experiments.
