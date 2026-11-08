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

## Primary conventions

- [Apart sprint guidelines and judging](https://apartresearch.com/sprints/swarm-alignment-2026#guidelines):
  report findings clearly, preserve limitations/ethics, distinguish preexisting
  work, and meet the official template/page limit.
- The prospectively frozen `SWARM_LEDGER_COMPLETE_PROTOCOL.md`,
  `SWARM_LEDGER_RESUME_PROTOCOL.md` and `ROUTER_RESUME_ANALYSIS_PROTOCOL.md`
  own sampling, request identities, estimands and release rules. Preparation
  does not amend them or justify dropping a reader.
- [Python exclusive-create file mode](https://docs.python.org/3.12/library/functions.html#open)
  makes accidental output replacement fail rather than overwrite an artifact.
