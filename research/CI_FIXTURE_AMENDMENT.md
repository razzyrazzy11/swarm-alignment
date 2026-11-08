# Synthetic CI fixture portability amendment — 8 November 2026

The five notification screenshots identify Report integrity runs 42461703249
(tag push), 42461703228 (branch push), 42461707366 (PR), 42461864964
(branch push), and 42461870808 (PR), at commits 470a946 and 6888c1d.
The failed Ubuntu job runs synthetic unit tests; it is not the local inference
collector. The two failures are `test_failed_delivery_kept_once_full_reservation_no_retries`
and `test_analysis_replays_native_cost_and_retains_failure_counts`.

The frozen test helper appends a fake request to a shared list under a lock,
sleeps, then decides whether to inject its one HTTP 504 from the current list
length. If two calls overlap before either returns, both can see length two:
neither injects the intended failure. The assertions correctly reject that
fixture. This defect is in synthetic failure injection, not response collection
or the analyzer's counting of actual HTTP failures.

## Correction and reproducibility

Use `python -m experiments.test_runner` for the complete experiment test suite.
It discovers every original test and preserves every assertion. Within the test
run only, it replaces `PilotTests.run_fixture` with a transparent synthetic
adapter. Each fake request receives its immutable ordinal while holding the
same lock used to append the call. The first ordinal therefore injects exactly
one 504 irrespective of completion order. An additional regression forces both
calls to start before either can return. The original assertions still check
the failure count, full unknown-cost reservation, retained identity and no retry.

The adapter fails closed unless the normalized original test-file hash equals
`58340e8ed2b58e34af88ae611377a61960f19e9769ff605b6ce1d3fdb909ac8d`.
This is a prospective test-only amendment: the original test file, collector,
transport, supervisor, registration, tags, request plans and scientific analysis
remain unchanged. Running raw discovery against the historical frozen fixture
can still reproduce the historical scheduling defect; CI explicitly uses the
documented runner. No assertion is skipped or turned into an expected failure.

## Effect on the study

These CI failures prevented later steps in the Ubuntu job from running; their
checks must pass on the repaired branch before claiming current CI validation.
They did not stop the independent local collectors, dispatch requests, change
records or reveal empirical answers. This diagnosis is not evidence that all
scientific results are correct: complete collection, strict replay, paper
integration and final visual review remain separate gates. No inference request
is repeated to repair this test failure. The original failed tag is preserved.

## Primary references

- [Python 3.12 lock objects](https://docs.python.org/3.12/library/threading.html#lock-objects):
  protect the shared operation that assigns the ordinal, rather than relying on
  thread scheduling or a sleep to order requests.
- [Python 3.12 mock patching](https://docs.python.org/3.12/library/unittest.mock.html#patch-object):
  the synthetic adapter is scoped to the test run and restored afterward.
- [GitHub Actions status expressions](https://docs.github.com/en/actions/reference/workflows-and-actions/expressions):
  subsequent steps normally require earlier success. The fix keeps that failure
  behavior; it does not use `continue-on-error` or suppress downstream guards.
