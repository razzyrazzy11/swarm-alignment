# Factorial reporting amendment: complete primary, incomplete secondary and registered extensions

## Timing and unchanged question

Written after original collection began and operational missingness was observed, but before scientific outcomes were inspected. This is an amendment, not a claim that partial-data reporting was in the original preregistration. Freeze it before computing real scientific metrics. The Track 4 question remains: does a swarm auditor lack necessary evidence, or fail to use evidence that is already sufficient?

Keep original frozen study and analysis files intact. Use a sibling reporting module. Preserve the single original Gemma 26B sufficient-evidence procedure-minus-direct primary, all 192 sources, original eight strata, source ordering, binary operational raw-score definition, and original 10000-replicate whole-source bootstrap seed 710029. Complete Gemma 31B comparisons remain secondary. No new primary is selected from observed outcomes.

## Actual observations and missing cells

The original reader plan contains 11640 calls: 11520 main and 120 calibration. Current original collection has 9742 terminal calls and 1898 unstarted calls. The two Adaption readers each have 3880 terminals, including 40 calibration calls; Hugging Face Novita has 1982 terminals. These are availability counts, not accuracy findings. Actor collection has 576 terminals for 192 trajectories. Reconstruct and validate these counts from journals, never from prose alone.

Publish actual case rows only. Put every planned job and its observed or unstarted state in a separate manifest. Do not manufacture responses or convert unstarted jobs into INVALID. Observed terminal INVALID is zero for the operational raw-score estimand; unknown unstarted outcomes are `null`. Report actual and planned calibration denominators separately. Multiple packets, prompts or readers do not increase the independent source sample beyond 192.

## Incomplete-reader bounds

For each fixed sufficient-evidence source let D and P be binary direct and procedure raw scores, and R_D and R_P indicate observation. Bound its difference using:

`lower_i = R_P*P - R_D*D - (1-R_D)`

`upper_i = R_P*P - R_D*D + (1-R_P)`.

Average over all 192 planned sources. Both known gives the observed difference; only P known gives [P-1,P]; only D known gives [-D,1-D]; neither gives [-1,1]. Interval width equals the number of unknown relevant cells divided by 192. The finite attainable values lie on a 1/192 lattice; the interval is their sharp envelope under unrestricted missing binary outcomes, not a claim that every completion is realizable by the fixed model.

These are finite-benchmark logical bounds, not 95% confidence intervals. Make no missing-at-random, monotonicity or deterministic-decoding assumption. Complete-pair averages may be shown only as descriptive selected-subset summaries with their denominator; they do not identify the full planned contrast. Do not bootstrap them into a full-benchmark effect. Observed operational zeros include serving failures and therefore do not estimate reasoning competence conditional on successful service.

This is established missing-data reasoning, not a new statistical method: [Manski, Partial identification with missing data](https://doi.org/10.1016/j.ijar.2004.10.006) and [Imbens and Manski, Confidence intervals for partially identified parameters](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1468-0262.2004.00555.x). The latter motivates explicitly distinguishing sampling uncertainty from identification uncertainty; this amendment does not implement its confidence procedure.

## Separately registered Ollama extension

Follow `OLLAMA_PROTOCOL.md`: ds_off 3880, ds_low 424 and gemma_bridge 424 planned calls, including 40 calibration calls per condition. Keep condition IDs distinct even when model names coincide. The predeclared secondary comparison is low minus off on DIRECT sufficient evidence; an exploratory Gemma implementation-bundle comparison uses the original Adaption 31B DIRECT sufficient rows. Both pair the same 192 sources. Procedure bridge summaries remain descriptive. Do not pool new models with the incomplete Novita condition or count repeated sources as new independent evidence.

## Export, verification and paper contract

Write `research/factorial-report.json`, leaving the original complete-plan exporter and its guards unchanged. Require independent replay of trajectories and evidence support, request/body/source commitments, exact planned manifests, terminal completeness for every started call and no active collector. Publication needs an explicit after-collection flag. Keep contexts private until all registered reader collection ends or a documented final cutoff is frozen.

Public verification must reconstruct all published packets, observed scores, missing counts, original primary intervals, partial-reader bounds and extension comparisons without API credentials or private receipts. Report original-plan completeness and each condition's completeness separately. A completed primary does not make the original Novita plan complete. Preserve all failed serving diagnostics and their excluded costs; no pilot contributes to scientific n.

Organize the official-template paper from a concrete audit example to definitions, acquisition controls, reasoning comparisons, empirical findings and limits. Use the 20-rules-of-learning skill for clear distinctions and prerequisite order, not as evidence for scientific claims. Keep actual denominators and amendments visible in the report, README and reproducible artifacts. Retain required Limitations and Dual-Use / Ethical Considerations appendix and the [Apart judging criteria](https://apartresearch.com/sprints/swarm-alignment-2026#guidelines).
