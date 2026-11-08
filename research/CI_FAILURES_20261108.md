# Five Report integrity notifications: verified cause and repair

Investigation after the current experiment-feasibility assessment,8November2026.
These are CI environment failures, separate from the18:07G31 rate-limit stop.
No inference, frozen-source edit, tag rewrite or outcome scoring was performed.

## Exact mapping

| Screenshot | Workflow run | Event/ref | Commit |
|---|---|---|---|
|1|[42506396569](https://github.com/razzyrazzy11/swarm-alignment/actions/runs/42506396569)|Push swarm-ledger-efficient-v1|3f41547|
|2|[42506396511](https://github.com/razzyrazzy11/swarm-alignment/actions/runs/42506396511)|Push efficient-resume-analysis-v1|3f41547|
|3|[42506402399](https://github.com/razzyrazzy11/swarm-alignment/actions/runs/42506402399)|Pull request research/scoping|3f41547|
|4|[42506396562](https://github.com/razzyrazzy11/swarm-alignment/actions/runs/42506396562)|Push research/scoping|3f41547|
|5|[42506758345](https://github.com/razzyrazzy11/swarm-alignment/actions/runs/42506758345)|Push research/scoping|01e3047|

All five exact logs show the same failing command:
`python -m unittest discover -s paper/tests -v`. The new
`test_handoff_has_explicit_unknowns_and_no_visual_attestation` called the
preparation dependency diagnosis, which imports PIL.Image. CI installed the
lightweight historical requirements, so each run ended with67tests and one
`ModuleNotFoundError: No module named 'PIL'`.

## Repair and actual use

Commit a92039d added paper/preparation-requirements.txt, composing the existing
requirements via `-r requirements.txt` and pinning Pillow13.0.0 and
pypdfium2 5.14.0. The actual Report integrity workflow installs this preparation
file before running paper checks. The lightweight historical requirements,
all assertions, frozen registrations and empirical data remain unchanged.

Remote [PR42507252283](https://github.com/razzyrazzy11/swarm-alignment/actions/runs/42507252283)
and [push42507247579](https://github.com/razzyrazzy11/swarm-alignment/actions/runs/42507247579)
both completed successfully. The logs confirm the rendering libraries were
installed and the formerly failing test passed, with all67paper tests passing.
This verifies that the fix is used in CI rather than merely present locally.
The newer9c63032 preparation runs42510102807/42510097878 were still running
when checked; dependency installation, paper verification and paper tests had
passed, while the experiment tests remained in progress. Record their final
conclusions separately; do not infer success from an unfinished run.

Historical failed runs remain an honest record. Re-running an old workflow uses
the original commit and ref; it does not apply a later dependency fix. There is
no reason to rewrite frozen tags or erase the original failures to make them
appear green. New-head success does not establish scientific replay, report
integration or final visual QA, which retain their actual-data gates.

## Conventions

- [pip requirements format](https://pip.pypa.io/en/stable/reference/requirements-file-format/)
  supports composing requirement files and pinned dependencies.
- [GitHub rerun semantics](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs)
  preserve the original event SHA/ref.
- The linked exact logs and repository workflow/requirements are primary
  evidence for this defect and repair. This targeted operational check does
  not complete any of the four broader queued post-integration reviews.
