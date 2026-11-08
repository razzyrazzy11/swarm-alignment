# Result-blind paper preparation and completion gates

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

### Current operational lineage after the HTTP500 stop

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
