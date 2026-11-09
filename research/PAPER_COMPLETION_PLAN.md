# Result-blind paper preparation and completion gates

## Current authoritative paper path — paced seven-batch lineage

Updated on 8 November 2026 from frozen engineering sources, preparation contracts
and process metadata only. No unfinished empirical accuracy or raw answers were
reviewed. Historical snapshots below are not current operating instructions.

Use `swarm-ledger-paced-v1` and `paced-resume-analysis-v1`, frozen at commit
`327d582`. MAIN is the strict seven-batch union: original, router-v1, server-v2,
provider-v3, efficient-v1, rate-v1 and paced-v1. Preserve every failure, original
flag and unknown-cost reservation. Current process paths are
`runs/swarm-ledger-paced-v1-driver/state.json` and
`runs/paced-resume-postprocess-driver/state.json`; the eventual proof is
`research/swarm-ledger-paced-resume-release-proof.json`. At this check, metadata
said collector `running/readers` and waiter `waiting_collection`, with zero
offline stages complete. A snapshot is not scientific or termination proof.

The registered admission limit is **9 November 07:56 UTC**; **08:00 is a target
drain**, not a whole-request or termination guarantee. The official deadline is
**9 November 11:59 UTC**, equivalent to 8 November 23:59 Anywhere on Earth. An
actual 08:00 drain would leave 3 hours 59 minutes. No measured bound establishes
that strict validation takes 60 minutes or that all later work fits this reserve.
Use actual stage timings when known; report risk rather than waive checks.

## Each layer requires its own proof

| Layer | Acceptance evidence | Still outstanding afterward |
| --- | --- | --- |
| Engineering preparation | Current committed source/path/dependency checks; optional synthetic native-export rehearsal | Scientific completion, report authoring and final QA |
| Collection | All six profiles and auxiliaries complete; actual owned processes terminated; predecessor evidence preserved | Scientific replay and provenance verification |
| Strict analysis | All seven paced stages complete and terminated; MAIN/HF, continuation, figures and sensitivity verified | Result-specific interpretation and manuscript integration |
| Paper integration | Result/content slots resolved; source-bound figures; reviewed candidate explicitly promoted; `visual_review` still pending | Native PDF export and every-page inspection |
| Final artifacts | Actual Word export, content/page checks, every-page/figure inspection, truthful hash-bound receipt, normal/optimized verification; only then all 14 slots complete | The four queued reviews and final release checks |
| Review and submission | Ordered reviews, material fixes revalidated, final commit/CI, separate user submission and receipt | No guarantee of acceptance, originality or a prize |

The existing waiter owns this exact order: `hf_export`, `main_export`,
`continuation_provenance`, `figure_input`, `figures`, `figure_provenance`,
`generator_sensitivity`. Figure generation uses `C:/Python314/python.exe`; the
other commands use the configured research interpreter. Do not substitute bare
`python` blindly: it currently resolves to Python 3.14 on this machine. Do not
launch another collector/waiter or manually race its stages against active work.

## Current executable authoring commands

From the repository root in PowerShell, use the current collector supervisor's
interpreter and a new timestamped private target. These commands do not start
inference. **Commit this refreshed plan before a new handoff diagnosis:**
`completion_handoff.committed_sources` requires it and the other preparation
inputs to match HEAD. A prior receipt retains the old raw plan hash; do not
reuse it as proof of refreshed inputs or overwrite it.

```powershell
$researchPython = 'C:\Users\rsaca\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$utcStamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
& $researchPython -m paper.completion_handoff diagnose --output "runs/paper-completion-handoff/paced-readiness-$utcStamp.json"
```

Diagnosis is result-blind and leaves scientific validation, integration and
visual QA false. Preserve the committed draft and historical report. Only after
actual full collection, all seven stages and their termination proofs succeed:

```powershell
$utcStamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
& $researchPython -m paper.completion_handoff candidate --output "runs/paper-completion-handoff/paced-candidate-$utcStamp.json"
```

The candidate gate checks actual completion and termination **before reading
aggregates**, then requires complete MAIN replay, original HF reconstruction,
current continuation/figure provenance and registered generator-domain sensitivity
reconstruction. It does not promote content, choose a favorable interpretation or
attest visual review. The candidate is an authoring scaffold, not a finished paper.

## Fourteen author slots after strict data admission

| Slot | Atomic completion check |
| --- | --- |
| `primary` | Registered G26 FULL16 procedure-minus-direct estimate, interval and independent n; retain null/adverse results. |
| `six_reader_tables` | All six profiles and conditions; delivery, validity, admission, matched effects and explicit denominators. |
| `actor_class_mix` | Actual host actions and label mix by assigned arm; always-NONE/ABSTAIN references. |
| `acquisition` | Matched oracle answerability, supported correctness and restoration; distinguish availability from evidence use. |
| `calibration` | Separate scripted class-specific errors/coverage; no pooling with natural trajectories or prevalence. |
| `influence` | Controlled peer-note contrast with receiver state fixed; no emergent-collusion inference. |
| `sensitivity` | Whether registered domain sensitivity changes the conclusion, with the original primary retained. |
| `delivery` | All-request serving/format failures and the subset behind conditional correctness. |
| `prior_iterations` | Earlier all-NONE sample, original HF recovery and exploratory weight work kept separate from MAIN. |
| `figures` | Actual verified PNG/source hashes, captions and alt text; no layout placeholders. |
| `interpretation` | Which repair each matched contrast supports; layers can fail together, with no internal-mechanism claim. |
| `limitations_ethics` | Decisive main-text limits and the required Limitations and Dual-Use / Ethical Considerations appendix. |
| `visual_review` | Actual exported PDF, every page inspected, then a truthful hash-bound review receipt. |
| `references_originality` | Claim/source alignment, prior art, preexisting work and the new contribution distinguished. |

Apply 20-rules-of-learning through a concrete handoff example before definitions,
one claim per paragraph, stable terms and an explicit link from each finding to
its matched contrast and limitation. A hidden authentic grant concerns acquisition;
no usable returned verdict concerns delivery; a wrong parsed verdict on sufficient
evidence raises the evidence-use question. This is an illustrative explanation,
not an empirical case or an exhaustive causal partition. The skill supplies no
scientific evidence or authority for an extra confirmatory analysis.

## Build, export and inspect the actual report

Review all admitted results, figures and sensitivities. Archive historical content
and artifacts, then explicitly promote only the reviewed candidate to
`paper/content.json`. Use the existing completed-study table/figure adapter; do
not change the frozen legacy builder or the official template's styles, fonts,
geometry and source run sizes.

```powershell
& $researchPython paper/figure_build.py
```

Export with a **new owned hidden Word.Application**, opening only the intended
document. Close that owned document and quit that app in a finally block; do not
attach to or terminate an unrelated user instance. Render and inspect every
actual page and figure. Repair overflow and repeat affected export/inspection.
Only afterward create the required source/hash-bound figure-review receipt and
record/check the actual PDF:

```powershell
& $researchPython paper/verify.py --record-pdf
& $researchPython paper/verify.py
& $researchPython -O paper/verify.py
& $researchPython -m unittest discover -s paper/tests -v
```

Require a **150–250-word abstract** and **at most eight main pages**, excluding
references and appendices. Eight pages are a ceiling, not a target. Edit prose or
move supporting detail rather than shrink fonts/margins. Include author names and
affiliations, references, truthful AI/prior-work disclosure and the required
Limitations and Dual-Use / Ethical Considerations appendix. Generated candidates,
page counts and green CI cannot attest actual visual inspection.

## Native-export rehearsal and readiness limits

The older preflight records `export_application_probe='Not performed'`; that
historical field has not been rewritten. A separate successful rehearsal at
22:00 UTC on 8 November is recorded in
`runs/native-word-readiness-20261108T220033Z/export-result.json` and
`runs/native-word-readiness-20261108T220033Z/render-result.json`. It exported the
existing synthetic input in 7.886 seconds and rendered all ten new PDF pages.
Both receipts explicitly say this is not an empirical report or actual-paper
visual QA. This warm synthetic timing does not predict final-report export or
inspection time. Existing synthetic inputs are
`runs/deadline-layout-probe/paper/layout-probe.docx` (historical metadata: six main,
ten total pages) and
`runs/talk-context-review/layout-probe/paper/layout-probe.docx` (seven main, eleven
total). These are layout-only artifacts, not scientific findings or final QA.

The safe recipe opens an existing synthetic DOCX **once, read-only**, in a new
owned hidden Word instance, exports to a new unused private `runs/` directory,
and renders only that new PDF with installed PDFium/Pillow. Track the owned
instance through the opened document's `Windows.Item(1).Hwnd`; the earlier
attempt using `Application.Hwnd` failed and is not successful readiness proof.
Close only that document and quit only the owned app. Use the reviewed private
export recipe, not a whole old finalizer that can author or promote content.
Do not alter the real paper/draft/template, collector, waiter or registrations,
make a final visual-review receipt, or repeat the existing authoring marker.
Any new rehearsal requires its own proof. Real-data export, actual pagination
and every-page inspection remain required even after this engineering success.

## Four reviews remain after validation and integration

Keep the exact order in [the deadline plan](DEADLINE_COMPLETION_PLAN.md#four-queued-reviews--still-deferred):
historical failure/corruption investigation; historical screenshot-CI tracing;
complementary line-by-line scientific/code/source/rules reviews; then unreviewed
material and narrative/visual refinement. Preparation does not perform them.
Resolve material findings and repeat affected validation, export and every-page
inspection. Require final commit integrity CI. Submission/receipt is a separate
user action; no automatic submission is authorized.

<details>
<summary>Historical preparation snapshots — not current operating instructions</summary>

The dated rate/efficient/provider paths, old 05:59 buffer, runtime budgets and
"current" labels below belong only to their earlier snapshot. They cannot override
the paced path above or attest present completion.

The official deadline is9November11:59UTC (8November23:59AoE). A prospective
rate-continuation admission limit07:56UTC targets08:00drain and reserves the
remaining3h59 for actual validation/paper/QA and then the four queued reviews.
This corrects our earlier05:59internalbuffer assumption without changing older
freezes. Nothing in this schedule bypasses actual-data proof or permits early
outcome scoring, automatic submission, or a false paper-completion claim.

Current admitted lineage is the six-batch rate continuation, tagged at a2f8bfa.
Use runs/swarm-ledger-rate-v1-driver and runs/rate-resume-postprocess-driver,
rate-resume-analysis-v1 and swarm-ledger-rate-resume-release-proof.json.
All earlier lineage descriptions below are historical. The result-blind
handoff-20261108T191100Z and rate-preflight-20261108T191200Z artifacts passed
engineering checks; both explicitly keep scientific validation, paper
integration and visual QA false until actual completed-data gates pass.

Working reserve after the08:00drain target: up to60minutes for the seven strict
offline stages and candidate proof;60minutes for verified-result interpretation
and authoring;30minutes for native export and every-page inspection;60minutes
for the four queued reviews, repairs and final CI; and20minutes for the user's
submission/receipt step. These budgets total3h50, leaving9minutes of nominal
reserve. They are planning targets, not observed runtimes or permission to skip
a failed check. A material review finding can consume more time and must be
reported honestly. Earlier completion creates additional reserve.

The new authoring input asks: **does a swarm auditor lack necessary evidence,
or fail to use evidence that is already sufficient?** Track 4 is explicit.
The draft follows a concrete handoff example, separates acquisition/delivery/
reasoning, defines the experiment, then leaves results visibly pending. This
uses the 20-rules-of-learning skill for clarity, not as scientific evidence.

`paper/prepare_complete.py` reads only the existing author/reference metadata
when preparing a draft. It does not inspect unfinished empirical answers,
alter a registration or trigger inference. It writes a separate new JSON file
with an unmistakable non-submission label; it never replaces `content.json` or
the current report. The current PDF remains historical until actual integration.

## Prepare now

### Historical operational lineage after the HTTP500 stop

**Latest addition: HF availability amendment.** The v2 batch subsequently stopped
with4,901 terminal readings, including two504s and twoHF429 `engine_overloaded`
responses. The v3 registration preserves every failure and collects only33,834
remaining MAIN readings plus480 auxiliary calls. Final readiness now requires
the actually complete and terminated `runs/provider-resume-postprocess-driver`
and the provider-resume four-batch analysis/proof/figure receipt. The candidate
contract binds `swarm-ledger-resume-v3-freeze.json`,
`provider-resume-analysis-v1-freeze.json` and
`swarm-ledger-provider-resume-release-proof.json`. Earlier lineage below remains
historical; neither stopped waiter can satisfy the latest gates. See
[provider recovery operations](PROVIDER_RESUME_OPERATIONS.md). The four queued
reviews retain their order after actual validation and paper integration.

The v1 router continuation stopped after15,025 reader terminals, including one
unknown-usage HTTP500. The prospectively registered
`swarm-ledger-resume-v2` collects only the38,735 unstarted MAIN readings and480
auxiliary calls, retaining that failure and its reservation. All six conditions
and original scientific analysis remain. See
[server continuation operations](SERVER_RESUME_OPERATIONS.md).

For this lineage, `paper/prepare_complete.py candidate` requires the actual
complete and terminated `runs/server-resume-postprocess-driver/state.json`,
the new server-resume analysis and strict three-batch proof, and its verified
figure-input receipt. The old stopped waiter cannot satisfy readiness. The
candidate contract binds both new freezes and
`research/swarm-ledger-server-resume-release-proof.json`. Instructions below
about the original router waiter describe the earlier lineage; use these new
actual gates for final integration. The old excluded serving pilot remains
blocked/unrun and must not be presented as empirical evidence.

From the repository root, with the primary Python 3.12 runtime:

```
python -m paper.prepare_complete draft --output paper/complete-draft.json
python -m unittest discover -s paper/tests -v
```

The draft covers the five-role bounded fake-data workflow, all six readers,
matched acquisition populations, frozen estimand/bootstrap, always-NONE and
always-ABSTAIN baselines, controlled influence, no training, finite oracle-domain
limits, preexisting work, retained failures, and required ethical considerations.
All workload counts describe the registered design, not interim discoveries.
The stable `paper/complete-reference-basis.json` preserves historical citation
numbering before the prepared draft selects and renumbers its sources. This
keeps regeneration and tests working after a reviewed candidate is promoted;
the current manuscript is used for author identity, not unstable citation IDs.

## Wait for actual scientific completion

The existing offline waiter must complete and terminate after both actual
collectors complete and terminate. Its seven stages export original HF recovery,
export MAIN, verify continuation provenance, verify plotting input, generate
figures, verify figure provenance, and export generator-knowledge sensitivity.
No preparation tool fakes those states. The optional secondary serving pilot is
not required for scientific candidate generation; it must not delay authoring.

After the waiter actually completes:

```
python -m paper.prepare_complete candidate --output paper/complete-candidate.json
```

This command fails before reading aggregates unless the real postprocessor has
all seven completed stages and no child, and process-creation-aware termination
proof succeeds. It then requires complete MAIN replay through
`complete_report_contract.load_completed(..., replay=True)`, completed HF
scientific reconstruction through `router_resume_analysis.verify_hf()`, figure
provenance, and the registered sensitivity export. A nonfrozen companion check
verifies the sensitivity registration, complete input and derived-file inventories,
original-primary commitment, and every scientific field and derived row against
the frozen `summarize` implementation. Existence or a newly computed report hash
alone cannot establish readiness. It derives all six-reader
table cells, denominators and primary interval from the verified report. It
does not invent a directional interpretation, select favorable findings, or
claim final visual QA.

## Explicit remaining authoring work

1. Read all actual report/figures and sensitivity results. Add calibrated,
   result-specific interpretation, actor outcome/class composition, all relevant
   counterexamples, calibration and controlled-influence findings. Keep the old
   192-source study and completed original HF recovery separate from MAIN;
   repeated readings are not extra independent sources. The candidate generator
   is a time-saving scaffold, not the final scientific discussion.
2. Register actual PNG hashes, public source hashes, captions and alternative
   text in the candidate. Put the clearest workflow and matched-effect plots in
   the main paper; balance remaining plots/tables against the eight-page cap.
   `paper/figure_build.py` now selects the opt-in completed-study table adapter;
   the legacy builder remains unchanged. Registered supporting figures can use
   appendix slots, with the same source/hash checks and unique-marker rule.
   A synthetic Word preflight with two main figures and two appendix figures
   fit six main pages; actual findings and every final page still need review.
   After incorporating the talk-context synthesis, a second clearly labeled
   synthetic probe fit seven main pages and eleven total pages. This leaves
   one main page of nominal headroom, not a guarantee for the final actual data.
3. Review the candidate, archive the historical content/artifacts, and explicitly
   promote the reviewed candidate to `paper/content.json`. Build using
   `python paper/figure_build.py`, preserving the retained official template.
   Do not modify the frozen legacy builder or attest a figure review in advance.
4. Export DOCX to PDF with a new hidden owned Word instance; do not attach to or
   terminate a user's unrelated Word instance. Verify the actual PDF text,
   abstract length, references, appendix, template fonts and page cap. Render
   and visually inspect **every actual page**. Only then create the required
   hash-bound figure-review receipt and run `python paper/verify.py` and
   `python -O paper/verify.py` against the integrated artifacts.
5. Commit the validated paper/data/provenance changes and let the integrity CI
   pass. Complete the four queued post-integration investigations/reviews in
   their preserved order. Do not equate a generated candidate or green metadata
   check with those completed reviews. Submission remains a separate user action.

## Eight-page narrative allocation (editorial addition, 8 November)

The main text has a **maximum of eight pages, excluding references and
appendices**. Eight pages are a ceiling, not a target to fill. Preserve the
official template rather than shrinking fonts or margins. The seven-page
synthetic context probe is only a feasibility check; final pagination depends
on actual findings, captions and figures.

Use one question throughout: **which part of oversight needs repair—evidence
acquisition, verdict delivery, or use of sufficient evidence?** This is an
editorial diagnostic frame, not a new estimand or an outcome selected after
inspection. These layers can fail together and must not be presented as an
exhaustive causal partition. In particular, receiving sufficient evidence does
not establish that a model used it, and an instruction effect does not identify
an internal reasoning mechanism.

| Approximate main-text budget | Reader's question and essential evidence |
| --- | --- |
| 1 page | Title, abstract, concrete handoff example, Track 4 problem and contribution. Introduce the three repair choices before technical terms. |
| 0.75 page | Prior work and the precise gap: matched stateful diagnosis, with explicit credit to the talk/source overlap. |
| 1.75 pages | Workflow diagram; trusted records versus peer claims; fixed-evidence instruction and matched-trajectory restoration contrasts; independent blocks, primary estimand and denominators. |
| 2.5 pages | Complete six-reader results, primary estimate and uncertainty, acquisition/answerability contrast, delivery accounting, actual actor label mix and baseline comparison. Main plots must identify denominators and uncertainty. |
| 1 page | Interpretation by repair layer, null/adverse effects, practical implications, core trust/domain/generalization limits and conclusion. |
| Up to 1 page reserve | Expand only where verified results require explanation; retain the main findings and decisive limitations in the main text. |

The 7-page working allocation plus up to 1 page reserve is not a pagination
guarantee. Results should follow the causal contrasts in the design, not rank
readers by whichever score looks most favorable. Keep the prospectively
registered primary prominent regardless of its sign or significance.

Use a compact worked example to connect the layers: a hidden authentic grant
may require acquisition; a request that returns no usable verdict requires
delivery accounting; a wrong parsed verdict on a sufficient packet raises the
evidence-use question. This is an illustrative explanation, never an empirical
case unless bound to an actual reviewed record. Preserve supported abstention
as distinct from both a correct unsupported guess and a wrong definite verdict.
State where output admission changes the analyzed subset; report all-request
delivery outcomes so conditional accuracy cannot hide failures.

Place full per-policy/per-arm tables, detailed calibration and controlled
influence results, generator-domain sensitivity, prior-iteration comparisons,
serving diagnostics and reproducibility details in appendices, with specific
main-text pointers. Still summarize any sensitivity or counterexample that
materially changes the conclusion in the main text. Retain the required
Limitations and Dual-Use / Ethical Considerations appendix. Keep earlier
all-NONE results, scripted cases and MAIN separate rather than pooling them.

Apply 20-rules-of-learning as an editorial method: concrete example before
definitions; one claim per paragraph; stable terminology across methods,
tables and discussion; visual comparison of confusable layers; and explicit
links from each finding to its matched contrast and limitation. This skill
does not supply scientific evidence or authorize adding confirmatory tests.
Final authoring remains gated on complete strict replay, then actual PDF
page-count verification and visual inspection of every page. The existing
monitoring and four deferred reviews keep their current order.

## Historical efficient final-data lineage

The efficient operational continuation uses the exact five-batch union:
original, router-v1, server-v2, provider-v3 and efficient-v1. The previous v3
collector was intentionally drained without replacing failed identities.
Current readiness requires the actually complete and terminated efficient
collector and the seven-stage efficient waiter, its registered analysis,
release proof and verified figure receipt. A stopped older waiter cannot
satisfy readiness. `python -m paper.completion_handoff diagnose --output ...`
creates a private result-blind authoring runbook; it is not an empirical report.

The historical report remains unchanged until complete strict replay permits
verified-data authoring. Retain the acquisition/delivery/use-of-evidence framing,
all six conditions, adverse/null findings, eight-main-page limit and official
template. Actual manuscript integration and every-page visual inspection precede
the four queued reviews. No preparation receipt substitutes for those actions.

## Primary conventions and unchanged protocol

- [Apart sprint guidelines and judging](https://apartresearch.com/sprints/swarm-alignment-2026#guidelines):
  report findings clearly, preserve limitations/ethics, distinguish preexisting
  work, and meet the official template/page limit.
- The prospectively frozen `SWARM_LEDGER_COMPLETE_PROTOCOL.md`,
  `SWARM_LEDGER_RESUME_PROTOCOL.md` and `ROUTER_RESUME_ANALYSIS_PROTOCOL.md`
  own sampling, request identities, estimands and release rules. Preparation
  does not amend them or justify dropping a reader.
- [Python exclusive-create file mode](https://docs.python.org/3.12/library/functions.html#open)
  makes accidental output replacement fail rather than overwrite an artifact.

</details>
# Offline recovery binding — 9 November

Complete collection is preserved. The old paced waiter failed its first HF
export at the private-to-public transport boundary and remains stopped. After
prospective registration/tag/push, the separately named offline recovery owns
the same seven strict stages, with state
`runs/offline-release-recovery-driver/state.json`, figure receipt
`runs/offline-release-recovery-driver/verified-public-input.json`, and HF
projection proof `research/hf-offline-release-recovery-proof.json`.

The nonfrozen paper readiness and handoff commands select that registered owner
and require its actual successful termination, source/freeze identity, companion
proof, original scientific replay and current figure/sensitivity receipts.
Historical stopped waiters cannot admit the final candidate. No paper findings,
visual attestation or queued review is complete merely because collection ended.
All remaining page/template/slot/review requirements below remain in force.

## Second offline boundary correction — prospective V2

The first offline recovery stopped before writing outputs because its top-level
allowlist omitted the recorded scheduler field `next_delay_seconds`. Its source,
freeze, tag, failed state and logs remain preserved. The separately registered
`offline-release-recovery-v2` validates finite nonnegative scheduler metadata,
removes only that private field, and then uses the frozen V1 projection and
unchanged scientific validators. Admission includes an exact metadata-only
projection of all 1,898 validated HF records before registration; no scoring or
release writing occurs in that preflight.

When its prospective freeze/tag/push exists, the authoritative offline owner is
`runs/offline-release-recovery-v2-driver/state.json`, with its own
`verified-public-input.json` receipt and
`research/hf-offline-release-recovery-v2-proof.json` companion. Paper gates require
its successful seven-stage completion and actual termination, both failed
predecessors stopped and dead, source/freeze identities and original strict
scientific replay. The four reviews remain after validation and integration.
