# Matched Hugging Face replication v2

Prepared 6 November 2026 before HF replication outputs. Adaption main-v2 collection is already running under its own registration. This secondary study does not change its prompts, sources, endpoints, stopping rules or primary analysis. No Adaption main answers or effects were examined to choose the HF subset. The subset was fixed from source indices, not model performance.

## Pre-inference v2 availability amendment

The published stateful-hf-v1 registration pinned Cerebras. At execution preflight that provider was absent from the live model catalog, so the code stopped before creating a run folder or issuing any inference calls. The zero-call preflight report is hf-preflight-v1.json; its original protocol remains HF_STATEFUL_PROTOCOL_V1.md and its tag is preserved. This was not a balance failure or a model-result-based selection.

V2 explicitly pins the live, priced Nscale route for the same Qwen model. Source subset, prompt, scientific outcomes, $1 cap and analysis remain unchanged. [HF's Nscale integration](https://huggingface.co/docs/inference-providers/en/providers/nscale) documents the exact model/provider suffix. V2 is committed/tagged before the first HF evaluation output. No silent provider fallback is enabled.

## Question and matched evidence

Does a separately served Qwen model family exhibit the same supported-decision and evidence-restoration pattern on the same packets? Use Qwen/Qwen3.8-27B through the explicitly pinned Nscale HF route. It is a matched model-family/serving comparison, not an independent source-scenario sample or evidence that two services serve identical weights. Requested/returned model strings are retained; the returned-model allowlist permits the catalog spelling and two punctuation/case spellings of that same Qwen model; an unexpected identity halts the run. A public model name is not an immutable checkpoint hash.

Select source indices 0–7 from each of the three main-v2 families: 24 source draws, four clean/four scripted violations per family. Derive them from the registered seed function, never from model outputs. Use all ten main-v2 evidence views for each: both naming conditions, full/random/selective exports and priority/random two-record authentic restoration for selective views. Total **240 calls**. The approval-join family remains excluded from development/tuning; these are its first HF evaluation outputs, not new training material.

Use the exact registered main-v2 PROMPT, public packet bytes, label checker and predeclared encoding parser. Fresh system/user messages, temperature zero, 4,096 output tokens, no tools or cross-call memory. HF Chat Completions is a different transport; only a terminal stop choice with string content normalizes to completed. No transport failure is turned into a refusal or justified abstention. The allowed JSON envelope, unsupported worker/NONE findings and raw strict validity have the same meanings as in the Adaption core.

## Outcomes and interpretation

Report counts and denominators by family/cohort/naming/loss/restoration: grounded correctness, supported definite coverage, unsupported executor, unsupported NONE, invalidity, raw strict validity, singleton answerability, latency/tokens and USD estimates. The selective-minus-random unsupported-executor contrast and priority-minus-random restoration comparisons are **secondary**, paired within the 24 sources, with the same 10,000-resample stratified source bootstrap convention. Main-v2's 192-source primary estimate is unchanged. Compare the Adaption endpoints on these same 24 sources descriptively; do not pool 240 HF views with 192 Adaption episodes as independent trials.

The script writes the full planned task manifest and request order before calls. Model/provider selection, subset and encoding cannot change after outputs are seen. Preserve nulls, regressions and all invalids; model-family transfer is bounded to this selected family/provider and finite grammar. This strengthens execution and checkability under the [Apart judging rubric](https://apartresearch.com/sprints/swarm-alignment-2026#guidelines), not a probability of winning or a novelty guarantee.

## Pricing, limits and freeze

The [HF routing contract](https://huggingface.co/docs/inference-providers/en/index) supports explicit provider suffixes and a live model catalog. Recheck the selected live provider's price before dispatch: frozen input **$0.20/M** and output **$2.50/M** tokens. Stop if that catalog price or provider availability differs; do not silently reroute. The earlier four-call smoke test already established inference access. HF Pro has a small shared compute allowance under the [billing documentation](https://huggingface.co/docs/inference-providers/en/pricing); it is not unlimited GPU/training access or a transfer of Adaption credit.

Nominal limit **$1.00**, two simultaneous calls, 18,000 input-byte reservation and 4,096 output-token reservation per call. Before a two-call batch, reserve the upper estimated liability against the cumulative limit. This is not a provider-enforced monetary cap, and actual HF billing can post later. Unknown usage consumes its reservation and stops new dispatch. Stop on source/config/tag mismatch, missing usage, unexpected returned model alias, token-bound violation, 401/402/403/429, third incomplete response, unavailable/changed pricing, STOP file or budget. No retries, outcome-dependent stopping, automatic top-ups or silent resume. Drain every started batch and fsync starts/results. Keep journal-only calls as uncertain liabilities after a crash.

Commit source/config/protocol and live catalog snapshot before running `python -m experiments.hf_stateful freeze`. Commit the resulting research/stateful-hf-v2-freeze.json and publish annotated stateful-hf-v2 before inference. Verify it binds the core main-v2 freeze, its runtime sources, the new HF script/config/protocol and intended source ancestry. Main-v2 remains unchanged. Raw outputs stay under ignored runs/stateful-hf-v2; release only sanitized fake-data packets/final answers and reproducible scores. The bounded fake interpreter is never a real tool interface.
