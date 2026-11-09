# When Can a Swarm Be Audited?

**Track 4 Multi-Agent Oversight and Control.** Does an auditor lack authentic evidence, fail to deliver a usable verdict, or answer incorrectly despite sufficient evidence?

A worker claiming that a delegated update completed does not establish who acted or whether permission still held. We test those distinctions in a bounded five-role fake-data workflow with authentic host records and untrusted agent notes.

## Completed MAIN

Collection completed on 9 November 2026 at 05:33:56 UTC. Registered offline V2 completed all seven strict stages at 06:33:33 and terminated. The independent paper-candidate gate subsequently passed frozen MAIN/HF replay, provenance, figures and generator sensitivity. There are **640 independent blocks, 2,560 matched trajectories and 53,760 MAIN reader responses**, plus 240 separate scripted calibration and 240 exploratory influence calls. Repeated arms, views and readers do not add independent blocks.

The paper integrates the complete MAIN. The corrected native Word PDF has 15 total pages, eight main pages and a 188-word abstract; every page was visually inspected. The four ordered, scoped reviews are recorded below. They corrected the Figure 2 endpoint description and clarified export-time native admission versus later verification. The earlier results-v3 paper is historical; no official submission is implied. Exact-commit validation is visible in [Report integrity checks](https://github.com/razzyrazzy11/swarm-alignment/actions/workflows/report-integrity.yml); older green checks do not validate a changed artifact.

The primary Gemma 26B FULL16 PROCEDURE-minus-DIRECT effect is **−2.07 percentage points [−4.06,−0.12]**, a 95% stratified block-bootstrap interval. Correct-definite verdicts fall from 1,497/2,560 to 1,444/2,560. The proposed procedure did not improve the primary endpoint. Secondary effects vary:

| Reader | Correct definite DIRECT / PROCEDURE, each /2560 | P minus D, pp [95% CI] |
|---|---:|---:|
| Adaption Gemma 26B, primary |1497 /1444|−2.07 [−4.06,−0.12]|
| Adaption Gemma 31B |2075 /2330|+9.96 [+8.55,+11.37]|
| HF Llama text |834 /900|+2.58 [+1.72,+3.44]|
| HF Llama schema |838 /908|+2.73 [+1.88,+3.63]|
| Ollama DeepSeek off |1689 /1689|0.00 [−0.55,+0.59]|
| Ollama DeepSeek low |2357 /2308|−1.91 [−3.01,−0.82]|

Secondary intervals are descriptive, not familywise-adjusted discoveries. Six profiles span four checkpoints and three families. G26/G31/DeepSeek low also read six reduced/restored views on 1,280 matched honest/both-arm trajectories within the same 640 blocks.

Contract-record restoration raises finite-domain answerability from 452/1,280 to 1,280/1,280. Supported-correct gains including required abstention are 3.44, 15.31 and 10.31 points for those three readers. Changing available evidence is distinct from improving evidence use. DeepSeek off delivers valid bare JSON throughout FULL16 but makes 871 false executor accusations in 2,560 DIRECT readings. Format compliance is not correctness. The 788 actual target violations imply an always-NONE baseline of 69.22%; scripted calibration and peer influence remain separate.

## Read and reproduce

Start with the [integrated PDF](paper/out/swarm_audit_scoping.pdf), [DOCX](paper/out/swarm_audit_scoping.docx), [aggregate report](data/swarm-ledger-v1-public/report.json), [scientific protocol](research/SWARM_LEDGER_COMPLETE_PROTOCOL.md), [generator sensitivity](data/swarm-ledger-generator-sensitivity-v1/report.json) and [figure provenance](paper/figures/swarm-ledger-complete-v1/ledger_figures_provenance.json). Current QA status is stated above.

```powershell
python -m experiments.swarm_ledger_complete_analysis verify-public --output data/swarm-ledger-v1-public
python -m experiments.offline_release_recovery_v2 verify
python -m experiments.test_runner
python paper/verify.py --public-replay
```

Public replay verifies exported jobs, actions, evidence, scores and arithmetic. Native-journal validation occurred during export; a fresh full native-journal check requires the private archive and admission path. The default paper verifier checks retained private failed-waiter evidence and provenance plus public replay, rather than repeating every native-journal check. Neither hashes nor replay independently authenticate a provider. See the [verification-scope erratum](research/PUBLIC_VERIFICATION_SCOPE_ERRATUM.md). Paper verification binds the current DOCX/PDF, aggregate tables, figure sources and actual all-page inspection receipt. CI alone is not visual inspection.

Seven disjoint collection batches preserve stopped prefixes and never retry/replace failed identities. All 53,760 planned MAIN reader identities are terminal; 34 retain unknown-usage reservations. Both auxiliaries have 240/240 HTTP200 terminals, known usage and zero capture anomalies. The excluded serving pilot is blocked/unrun. No new inference is needed.

The original paced HF export and registered offline V1 both failed before release; their states/logs/source/freezes remain immutable. V2 validates the omitted finite nonnegative next_delay_seconds metadata, then projects after frozen private/native admission. Public validation, rows/failures, costs, identities and scientific functions remain unchanged. See the [MAIN release proof](research/swarm-ledger-paced-resume-release-proof.json) and [HF recovery proof](research/hf-offline-release-recovery-v2-proof.json).

The [CI fixture amendment](research/CI_FIXTURE_AMENDMENT.md) preserves frozen test bytes/assertions while stabilizing explicit synthetic clocks, completion observation and journal snapshots. It covers 34 exact calendar methods, a single fault-first synthetic scenario and the documented journal ordinal fixture. Production clocks, cutoffs, caps and science are unchanged; the real optional serving pilot remains blocked and unrun. Historical red runs remain preserved. New artifact checks must pass at their own commit.

The four ordered reviews cover [historical serving failures](research/FINAL_REVIEW_1_SERVING_HISTORY.md), [attached historical CI failures](research/FINAL_REVIEW_2_HISTORICAL_CI.md), [mathematics](research/FINAL_REVIEW_3_MATH.md), [code/provenance](research/FINAL_REVIEW_3_CODE_PROVENANCE.md), [paper/primary sources](research/FINAL_REVIEW_3_PAPER_SOURCES.md), and [final narrative/template/visual QA](research/FINAL_REVIEW_4_NARRATIVE_VISUAL.md). Review 3 used native Codex Astra, Terra and Sol models as the documented fallback because OpenCode was unavailable. These are scoped reviews with explicit coverage gaps, not independent-vendor certification or exhaustive proof of originality.

## Historical work and limits

The [results-v3 snapshot](https://github.com/razzyrazzy11/swarm-alignment/tree/results-v3) preserves the earlier 192-source report. Its natural labels were all NONE, so its procedure gain concerns false accusations, not incident recall. Original HF completion recovers original identities and is not substituted into MAIN. Earlier [scripted](research/STATEFUL_RESULTS.md), [live](research/LIVE_RESULTS.md), [weight-policy](research/WEIGHT_RESULTS.md) and [factorial](research/FACTORIAL_RESULTS.md) studies remain separate.

Razvan Sacara's October 2026 [trusted-agent-sting](https://github.com/razzyrazzy11/trusted-agent-sting) is preexisting work; its code/data/results were not imported. AI tools assisted code and writing; the author remains responsible. The [talk-context synthesis](research/TALK_CONTEXT_SYNTHESIS.md) is contextual, not empirical evidence. The 20-rules-of-learning skill guides concrete examples and distinctions, not science.

A synthetic role graph, authentic-host assumption, generator-relative oracle, repeated sources and unpinned serving limit transfer. Layers can coexist; effect sizes do not causally partition errors. No universal prompting remedy, internal mechanism, spontaneous collusion, general swarm safety or judging outcome is established.

Keys, native IDs, headers, raw reasoning and raw runs remain excluded; see [SECURITY.md](SECURITY.md). The repository remains private and the PR a draft. Judge access, official submission, merge and publication remain author actions.
