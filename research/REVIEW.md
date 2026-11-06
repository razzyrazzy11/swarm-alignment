# Consistency and originality review

Review date: 6 November 2026. Initial baseline: `ab8d546` / `scoping-v0.1`. The early corrections below preceded experiments; the development-status update below follows real inference. Protocol v0.4 remains prospective and unfrozen. This log distinguishes completed editorial/source work, delegated code review and empirical work. It does not certify acceptance or originality.

## Scientific and mathematical corrections

| Finding in the first draft | Correction and evidence |
|---|---|
| Responsible actor could mean executor, initiator or decisive cause | Define the executor of one designated unauthorized mutation. Who&When and BLADE address different responsibility questions; no causal blame or collusion label is claimed. |
| Coordinated deletion sounded like observed agent behavior | Define a scripted loss transformation on investigator exports. Protected originals remain unchanged; no spontaneous or adaptive attack was observed. |
| Receipt/identity ablations leaked the same ID into both channels | Receipt has an opaque call handle; a separate binding links it to a stable instance. Each channel has a distinct function. |
| A receipt captured before execution could falsely certify success | Separate request capture from post-execution status/state change. Denied or attempted calls are not completed mutations. |
| Every compatible history could be vacuously true for an empty set | Empty compatibility means inconsistent evidence; ambiguity requires a nonempty set with several labels. NONE also needs positive support. |
| The comparator might use privileged loss metadata | The same whole-packet observation contract and public constraints apply to all readers; hidden masks are integrated out, not leaked to the comparator. |
| Equal record count was called an equal observation budget | Restrict the statement to record counts, and report token/cost differences separately. No efficiency claim without sensitivity checks. |
| Primary main effect and interaction were conflated | One proposed primary contrast: targeted-minus-random at 25% loss with churn, full instrumentation and plain prompt. Churn difference-of-differences is secondary. |
| Invalid responses could disappear from an evaluable-only denominator | Keep all planned calls on scorable packets, including INVALID. Exclude/report inconsistent packets separately; primary differences use common episode pairs. Score one terminal result per planned call, with retry attempts recorded separately. |
| Correlated packets could inflate independent n | Bootstrap whole source episodes with paired conditions/repeats. The zero-event upper bound at n=60 is 4.87%; n=299 gives below1%. Recompute actual eligible n. Exact binomial coverage assumes common risk; the zero-event formula conservatively bounds mean heterogeneous risk under independence. |
| The core sampling grid hid its cost | Historical profiles estimated 4,320 calls for one model or 26,640 across three. Completion/token assumptions failed development qualification; neither is a validated launch grid. Future costing must use measured behavior and reconciled liability. |
| Model name was treated as the full serving condition | Freeze/disable retrieval, memory and self-improvement; specify complete context columns and split families before augmentation. Supported by supplied workshop. |

The proof now fixes all public side information, allows probability mass on other outputs, states the two-history equal-prior assumption, and explains why an unequal prior changes the guessing bound. It is a constructed ambiguity, not a theorem that arbitrary deletion always defeats attribution. No novel information-theoretic theorem is claimed.

## Source-to-claim and originality boundaries

| Primary source | Established contribution we must acknowledge | Scope that remains proposed |
|---|---|---|
| [Qin et al.](https://arxiv.org/abs/2609.30266) | Tampering, peer influence, independent recording/completeness | Selected export loss crossed with instance naming conditions |
| [Yun et al.](https://arxiv.org/abs/2610.09581) | Evidence bindings, abstention and same-packet comparator | A different bounded multi-worker query and loss policy; novelty unproven |
| [Syscon](https://apartresearch.com/sprints/projects/syscon-kernellevel-syscall-monitoring-for-ai-agent-control-in-sandboxed-environments-guun) | External execution receipts and observability/detection distinction | Measure preservation versus interpretation under explicitly incomplete exports |
| [Who&When](https://arxiv.org/abs/2505.00212), [BLADE](https://arxiv.org/abs/2610.18780), [BRIDGE](https://arxiv.org/abs/2610.17805) | Decisive-error attribution, handoff responsibility evidence and verified repair | Executor attribution under a declared finite observation model, not a new generic blame graph |
| [Kitaoka et al.](https://arxiv.org/abs/2610.24052v1) | Planned distributed attacks and separate/joint monitoring | Export-loss question, not a new demonstration of distributed evasion |
| [OpenAI monitoring](https://openai.com/index/how-we-detect-frontier-model-misalignment/) | Multilayer investigations and external telemetry | No operational deployment or reproduction claim |

No claim of being the first logger, first receipt system, first abstaining reader, first distributed attack or first attribution framework remains. A literature search cannot prove no earlier method exists. The interaction and practical preservation tradeoff must be experimentally demonstrated before being called findings.

## Lessons from eight selected winning examples

These are examples, not a representative sample or an explanation of prize outcomes.

| Example | Transferable principle | Application here |
|---|---|---|
| Omission Attacks | Isolate a failure class; acknowledge narrow validation | Fixed target and clean controls; do not infer safety from a few positive examples |
| Noticing the escapes | Inspectable evidence and restrained conclusions | Source ledger; real payloads do not supply complete labels |
| Readable but Not Causal | Prediction and causal validation answer different questions | Executor support is separate from decisive causal error |
| [Syscon](https://apartresearch.com/sprints/projects/syscon-kernellevel-syscall-monitoring-for-ai-agent-control-in-sandboxed-environments-guun) | Honest null result; observation is not detection | Separate record preservation from reader interpretation; report coverage/uncertainty |
| [ActionLens](https://apartresearch.com/sprints/projects/actionlens-preexecution-environment-probing-for-agent-action-approval-xy22) | Component ablations and usefulness costs | Binding/receipt factorization; correct definite coverage as companion outcome |
| [Detecting LLM Subversion](https://apartresearch.com/sprints/projects/detecting-llm-subversion-in-vulnerability-patching-settings-gagj) | A useful, checkable setting can be a contribution | The bounded toy target/oracle now exists with automated validation; richer stateful scope and independent human review remain gaps |
| [Counterfactual Components](https://apartresearch.com/sprints/projects/counterfactual-components-for-ai-control-protocols-ibli) | Specify valid perturbations and audit the judge | Predeclared loss selector, hidden-label leakage checks, independent oracle fixtures |
| [Declare Before You Run](https://apartresearch.com/sprints/projects/declare-before-you-run-an-open-filing-standard-for-frontier-training-and-evaluation-runs-dkok) | Explain adoption mechanism and untested feasibility | Deployers would preserve evidence before incidents; actual overhead/adoption remain unmeasured |

Reading-depth and access qualifications are in SOURCE_AUDIT.md. Talk speculation about judges' interests is not used as a rule. The current Swarm Guidelines, particularly Judging and results, govern this project's impact, execution and clarity assessment.

## Learning and reading order

The 20-rules-of-learning skill is applied as an editorial method: start with the fake-record example; define execution and evidence support before introducing metrics; keep one claim per paragraph; distinguish easily confused concepts; connect each comparison to its source and purpose; state limitations immediately alongside the relevant inference. Learning prompts remain in DECISION.md; the paper remains a research narrative. The skill is not evidence for novelty, causality or eligibility.

## OpenCode recovery and code verification

The connected adapter's five-second startup check expects an older CLI startup string/API. A task-local compatible CLI/MCP bridge started within the original timeout while leaving global configuration unchanged. Separately, sandboxed CLI startup reproduced a log-file EPERM; that was not proven to be the connected MCP's exact failure. OpenCode Go then returned a monthly-limit error, Ollama returned401 and Anthropic insufficient credit. Failed/dispatched tasks are not counted as completed reviews.

Completed free-provider OpenCode reviews:

- Repository scout, task `fc9364fc-ca2b-44ba-a5a3-47e84930a81e`, GLM5.3Flash: 28 completed read/grep calls, no agent source edits. Confirmed stale-artifact detection was absent, PDF manifests were unenforced, assert guards disappeared under Python optimization, and unknown table markers could leak into output. Findings about missing citations/25%-loss wording were taken during an intermediate edit and rechecked against the final text rather than copied as current defects.
- Mathematical review, task `278097d6-1c8c-4a8d-a4ae-133361894a78`, DeepSeekV4.1Flash, completed after an initial empty response and a same-session follow-up. Confirmed the two-world inequality and sample-size arithmetic, and exposed denominator, empty-history, mask-pairing and latent-metadata ambiguities. These were corrected. A further response confirmed the heterogeneous zero-event bound. Reviewer decimal rounding and a mistaken description of the primary effect as a difference-of-differences were independently corrected; review output is evidence to assess, not authority to copy.
- The implementation delegation returned planning prose without code changes and was cancelled. It is incomplete, not an implementation success. Codex implemented the integrity fixes.
- A bounded cross-model code review on the completed DeepSeek session inspected six source files without mutation. Its confirmed findings were one-way PDF text matching (removed prose could linger), premature manifest writes and duplicate/misordered paragraph spacing. The fixes add exact normalized whole-text comparison accounting for the retained template footnote, write the manifest atomically after all gates, and reuse correctly ordered paragraph properties. A regression now rejects attesting an old PDF after prose deletion. Claims about nonexistent tests, ZIP hash nondeterminism and unsupported module entry points were checked and rejected as false positives. Task-local review servers were stopped afterward.

The updated verifier reconstructs expected DOCX parts in memory, checks current prose and table cells against PDF text, checks source/template/builder/DOCX/PDF hashes, derives page/word/size counts, validates citation IDs and checks ignored secrets/raw outputs. CI checks committed artifacts before any regeneration; Python `-O` keeps explicit guards active. Table1 is source-driven. Tests exercise stale prose, altered preserved XML, modified PDF bytes, missing PDF pages, unknown markers, orphan references and optimized Python. They validate artifact integrity, not scientific oracle correctness or absence of arbitrary malicious PDFs.

Runtime `.swarm/` and browser download state are excluded from Git. No credentials or raw transcripts belong in the report package. Detailed diagnostic output stays task-local outside Git; the final source audit retains reading-depth limitations.

Local validation: nine regression tests passed; normal and optimized verification passed. The reference-ID check covers all current citations, including the added Adaption price source. The current official template's preserve-only parts and section geometry remain unchanged. Microsoft Word exports and page-image inspection are repeated after source changes. The abstract has 193 words; final page counts are derived in pdf-check.json rather than inferred from an earlier render. No scientific experiments or research-credit charges were introduced by these checks.

Historical credit-plan render: six main pages, two reference pages and one appendix/disclosure page (nine total), all inspected at that revision. All 26 references were cited then. One regression fixture used a hardcoded new reference ID; adding reference26 exposed it, and it now derives the next unused ID before testing orphan detection. The full nine-test suite passed after that correction. The cost calculator reproduces the historical 26,640-call/252.36-credit arithmetic; that output is planning data, not agent-performance evidence or a current validated launch profile. New empirical prose requires a fresh render/integrity pass; earlier page/reference counts do not attest the later report.

## Development-status reconciliation after actual calls

The current empirical source of truth is PILOT_RESULTS.md with pilot-results.json; SUITE_STRATEGY.md defines the proposed next stage. A finite enumerator and separately written constraint checker agree on 55,296 valid projections of the same toy grammar. This is automated validation, not independent human approval. Current mask support is limited to the eight-record full-instrumentation 25%-loss pilot; exhaustive checks over a declared broader mask domain do not implement the prospective 50% or instrumentation factorials.

There are 318 retained Adaption request records across interrupted/qualification/formatting/fixed-reader/influence batches and four HF serving checks. Reader versions reuse 20 source seeds 71000–71019; these and influence seeds 84000–84003 are excluded from future confirmation. Three scenario-family names share one grammar and all were used in development. No family was held out. Each fixed-batch source has only one naming condition, so the data cannot estimate a paired churn interaction. Retained versions are not independent datasets to pool.

The completed fixed batch reports grounded correctness of 54/60 and 59/60 for the two qualifying endpoints; these denominators are dependent packet views, not independent episodes. Selective loss reduced structural answerability more than random loss but did not increase observed unsupported worker accusations. The influence pilot produced 32 read choices and no write attempts/mutations. These are transparent development negatives, not evidence that a defense works or that inter-agent influence is absent generally. The four HF answers verify a serving route, not independent replication or checkpoint equivalence.

The first runner had no durable pre-call journal, and early working sources were not all archived before execution. Some early calls remain unknown and exact source reconstruction is limited. Later fsynced journals, drainage and hashes improve future provenance without retroactively completing older evidence. Document retained records and unresolved liabilities instead of calling every missing response unattempted.

The initially observed Adaption balance was 1,500 credits at 1 credit=$1 on the existing Builder plan; the user authorized all available credits, with no top-ups or subscription changes. Known provider-reported amounts total approximately 0.26418926 credits, but final debit is unreconciled after browser refresh failed and early unknown calls remain. The former $500 and 600-episode/26,640-call estimates are historical only. Training remains unlaunched: official iteration controls are not monetary caps, and both bounded charge and demonstrated base/adapter serving are required before allocation. No current account/charge claim rests only on a catalogue read.

## Remaining gates before an empirical submission

Final local development-report check: 19 experiment tests and nine paper integrity tests passed. The 120-case sanitized release replays and rescores without keys or network. Normal and optimized artifact verification pass; the official-template export has seven main pages, 12 total pages and a 196-word abstract. All 12 final pages were visually inspected. These checks supersede earlier artifact counts above and do not establish the prospective scientific effect.

1. Extend the validated toy grammar to genuinely different stateful handoffs, then independently check its new projections/fixtures and reserve a new untouched family. Existing oracle agreement does not validate unimplemented extensions.
2. Reconcile billing/unknown early liabilities and freeze exact endpoints, prompts, serving configuration and a costed grid using observed completion behavior. Account inference works; training and custom-checkpoint serving remain separate gates.
3. Freeze/tag protocol v0.4's successor with new seeds/split manifest before confirmation. Report all actual counts, failures and uncertainty; preserve the development negatives. Current descriptive pilot accuracy is established only for its toy packets, while defense improvement, transfer and the proposed interaction remain unestablished.
4. Obtain human author review of scientific claims, affiliations and submission details. This review cannot supply author approval or a guarantee against disqualification.
5. Recheck live submission rules and required appendix, final PDF links, page/size/abstract limits and the confirmation email. No project has been submitted by this task.
