# Final review 2: historical screenshot CI failures

Reviewed 9 November 2026. This memo covers queued review 2 only: the five screenshots for commits `7a00899acc4890dd384270c8cc0b339cfb651e5e` and `a9354055f79c2edba09ab5fa0f30a94addbabd92`. It does not perform reviews 3 or 4, rerun CI, modify frozen code, or change collection.

## Finding

All five screenshot notifications map to real failed GitHub Actions runs. Their owning logs show the **same two Windows-specific synthetic process-fixture assertions running on Ubuntu**, not failed empirical model collection or a failed paper check. A sixth branch-push run for `a935405`, not shown in the supplied screenshots, has the same failure.

The prospective correction in `4d4a8f647329ae0d03c8ca850e2364b73bd6ad87` moved the unchanged process-creation tests to a dedicated Windows job. This resolves the identified platform mismatch without editing the frozen tests, production process guard, registrations or historical tags. The old six runs remain failed. A separate, newer synthetic fixture race remains recorded for the final artifact's push run; it must not be conflated with these historical failures or described as green.

## Screenshot-to-run mapping

The screenshots were visually inspected from the supplied attachment folder. Run metadata and failed-step logs were retrieved using read-only `gh run list` and `gh run view --json ...` / `--log-failed`. All six historical runs are attempt 1 and completed with `failure`.

| Screenshot | Commit/ref and trigger | Actual run | Failure completed, UTC |
| --- | --- | --- | --- |
| `1-Screenshot_20261107-174446.jpg` | `7a00899`, `research/scoping` push | [42397325759](https://github.com/razzyrazzy11/swarm-alignment/actions/runs/42397325759) | 7 Nov 17:41:07 |
| `2-Screenshot_20261107-174441.jpg` | `7a00899`, pull request | [42397330428](https://github.com/razzyrazzy11/swarm-alignment/actions/runs/42397330428) | 7 Nov 17:43:05 |
| `3-Screenshot_20261107-174433.jpg` | `7a00899`, `swarm-ledger-dispatch-v2-pilot` tag push | [42397325757](https://github.com/razzyrazzy11/swarm-alignment/actions/runs/42397325757) | 7 Nov 17:43:00 |
| `4-Screenshot_20261107-183759.jpg` | `a935405`, `swarm-ledger-complete-dispatch-v1-main` tag push | [42401895869](https://github.com/razzyrazzy11/swarm-alignment/actions/runs/42401895869) | 7 Nov 18:37:11 |
| `5-Screenshot_20261107-184105.jpg` | `a935405`, pull request | [42401900953](https://github.com/razzyrazzy11/swarm-alignment/actions/runs/42401900953) | 7 Nov 18:39:25 |
| Additional owning history | `a935405`, `research/scoping` push | [42401895662](https://github.com/razzyrazzy11/swarm-alignment/actions/runs/42401895662) | 7 Nov 18:40:04 |

The notification text “All jobs have failed” describes the job conclusion. It does not mean every step failed. Each historical workflow had one `report-integrity` job, and all six logs show the following steps **passed before the failure**: ordinary paper verification, optimized paper verification, paper unit tests, and experiment unit tests.

The failed step was `Test PID-safe release orchestration when present`. Subsequent registration, release and replay steps were **skipped**, not passed. This matches GitHub's documented default `success()` step condition; a failed earlier step normally prevents later ordinary steps from running. See [GitHub status-check functions](https://docs.github.com/en/actions/reference/workflows-and-actions/expressions#status-check-functions).

## Exact cause in the owning code

Every historical failed log reports:

1. `test_absent_parent_and_child_accept_without_changing_actual_toy_state`: `AssertionError: 0 != 2`, at `analysis/test_ledger_release.py:41`.
2. `test_live_equal_older_and_unknown_processes_fail_closed`: `AssertionError: ValueError not raised`, at `analysis/test_ledger_release.py:55`.

The fixtures create temporary `toy-science` state with synthetic parent/child PIDs 101 and 102. They patch `r.dispatch.subprocess.run` to simulate Windows PowerShell process lookups. The production `experiments/swarm_ledger_dispatch_v2.py:142–161` selects that subprocess path only when `os.name == 'nt'`. On Ubuntu it instead uses `os.kill(pid, 0)`; an absent synthetic PID is accepted as terminated. Consequently the mocked Windows lookup is called zero times, and changing its mocked return value cannot force the intended Windows failure cases. The assertions correctly detect that their intended branch was not exercised.

`analysis/ledger_release.py:25–42` calls this process guard for both recorded PIDs, verifies unchanged state bytes, and rejects unrelated collector locks. The historical CI failure is therefore in **where Windows-specific fixtures were scheduled**, not evidence that a live Windows collector was mistakenly accepted or that the process guard should be weakened. Another Windows-oriented test iterates the captured subprocess calls with `all(...)`; on the wrong platform its empty-call iteration can pass vacuously. The two failing assertions are valuable coverage guards.

Source comparison confirmed the following LF-normalized SHA-256 identities are identical at both screenshot commits and the reviewed current working copy:

| Frozen source | SHA-256, CRLF normalized to LF |
| --- | --- |
| `analysis/test_ledger_release.py` | `61d396c19c69d2dc9da0933b43e1f19484efb0d78caa59653d79382ba293913f` |
| `analysis/ledger_release.py` | `e944ca0274ed30acb30dcd704c6e74549e73b3f4f0c6495fd3b82c60f4aa883e` |
| `experiments/swarm_ledger_dispatch_v2.py` | `aca160fabd9eff96a9f4b4054b4ba44c2dc076bf3f19d78cd13baa32e10e47c9` |

## Prospective correction and scientific effect

[Commit 4d4a8f6](https://github.com/razzyrazzy11/swarm-alignment/commit/4d4a8f647329ae0d03c8ca850e2364b73bd6ad87), dated 7 November 18:53 UTC, removed the Windows-fixture command from the Ubuntu job and added `windows-release-guards` on `windows-latest`, executing the same `python -m unittest analysis.test_ledger_release -v` command. It did not replace the assertions, mark them expected failures, add `continue-on-error`, alter OS dispatch in the frozen guard, or rewrite the historical tags. GitHub documents `runs-on` as selecting the machine type in [workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idruns-on).

The current workflow still executes these original tests in its Windows job. The final-artifact CI receipt discussed below records that job as successful. This is a concrete prospective remedy for the identified platform mismatch, with actual subsequent Windows execution, rather than a request to suppress the failed check.

The historical workflow commands execute synthetic tests and offline verification. They do not issue the local scientific collector's requests, modify its terminal journals, or retry failed provider identities. The failure prevented downstream **CI validation** from being completed in those runs; it did not itself stop, corrupt or authorize empirical collection. Conversely, the paper checks passing at those historical commits validate the paper then present, not a later final empirical report. Neither a tag name containing `pilot`/`main` nor a green unit-test step is evidence that inference completed.

The serving-history investigation is separate in `FINAL_REVIEW_1_SERVING_HISTORY.md`. Its retained failures and exclusions must not be attributed to these CI assertions. Similarly, `CI_FIXTURE_AMENDMENT.md` discusses additional notifications at other commits; that document is not the owning explanation for these five supplied screenshots.

## Separate current-artifact status and pending repair

The coordinator's actual queried receipt at **9 November 09:23:16 UTC**, `runs/paper-production-20261109T072000Z/artifact-49027a8-ci-status.json`, records these distinct outcomes for the exact final-artifact commit `49027a8dd4b0cca320d7d803d32262d1c5d694fb`:

- [PR run 42591409383](https://github.com/razzyrazzy11/swarm-alignment/actions/runs/42591409383): **success**, including report-integrity and Windows release guards.
- [Push run 42591399764](https://github.com/razzyrazzy11/swarm-alignment/actions/runs/42591399764): **failure**, while ordinary and optimized explicit public paper replay checks passed.

The retained push log identifies one different failure, `FixtureClockTests.test_all_named_original_methods_pass_with_all_assertions`. Its nested paced synthetic scenario expected `gate.checks >= 2` but observed 1 in `test_connection_failure_is_retained_once_and_only_unstarted_continue`. That is a test-observation scheduling issue under separate operational repair/review, not either historical Windows-fixture assertion. At the cited receipt time the deterministic repair was pending independent review. This memo does not claim that pending change is verified, committed or green, and does not duplicate its implementation.

Disposition of any later repair must be added as a separate evidence-backed follow-up with its own commit, test results and CI run IDs. It cannot erase these retained red histories or change the conclusion of the exact-artifact push. A successful PR run and a failed push run of the same source are compatible with a scheduling-sensitive fixture; they are not grounds to report both green.

## Evidence coverage and limitations

Private `runs/final-review-2-ci/actions-evidence.json` records all six run/job/step summaries, selected traceback lines, and complete SHA-256 commitments for each downloaded metadata JSON and failed-step log. Corresponding `{run}-metadata.json` and `{run}-failed.log` files preserve the owning read-only API evidence. `source-identity.json` contains the historical/current source comparisons. `provenance-hashes.json` binds all five screenshot bytes, the three historical workflow snapshots, current workflow, and the coordinator's current CI receipt/log.

The coordinator receipt raw SHA-256 is `1aba13d372dce0859439c17bcac8c1571fa40a713381799fb61bb8115a0a99cc`; its retained failed log hash is `40ce506b02a0127ade3d24ebff2de68eb7e15cacef6acfbb20f9c84d7fb6be1d`. Current status is a timestamped observation, not a promise about later commits.

Coverage includes the supplied images, actual metadata and failed-step logs for all six owning historical runs, owning source/control flow, the exact platform correction diff, and the separately supplied current-artifact status/log. Full successful-step logs and unrelated workflow history were not exhaustively audited; their pass conclusions here come from GitHub step metadata. The root's current CI receipt was read without repolling already completed runs. No credentials, provider checks, inference, workflow reruns, source edits, frozen mutations, commits or pushes were performed for this review.

Review 2 is complete. The screenshot cause is explained and the prospective platform correction is supported. Historical runs remain red; the separate final-artifact push fixture repair remains pending at the cited observation time. Reviews 3 and 4 have not been started by this review.
