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

## Additional atomic-snapshot fixture amendment

Branch run 42521622069 at commit 327d582 failed in
`DispatchCollectorTests.test_pilot_preserves_reservation_and_does_not_gate_json_accuracy`.
The original fake worker reads the entire attempts journal to assert its own
start was persisted. The dispatcher can append another request concurrently;
the strict parser may then encounter that unfinished append. The CI log retains
only the collector's outer integrity-stop exception, so the historical inner
exception cannot be recovered from that log alone. A controlled synthetic split
append reproduces the same outer stop with `JSONDecodeError` captured inside.
The other three runs of the same source passed; this is consistent with the
scheduling-sensitive explanation, rather than proof of a production defect.

The existing nonfrozen runner now wraps only this one original test method.
Within that method, a shared reentrant lock protects the synthetic dispatcher
append and the fake worker's snapshot. The original method, strict parser,
assertions, test count and collector source are retained; both wrappers restore
on every exit. The frozen file hash must equal
`32ac534ceecf2ffe2cfc0abff882b64f6419a6f326ec28072400fb3b8fd3683e`.
The real transport does not perform this synthetic concurrent journal read,
and no live collector is patched or serialized. New regressions force a partial
append, verify rejection without the adapter and complete parsing with it,
check that malformed-record/disk failures still propagate, and execute the
unchanged original test method. No CI assertion is skipped or retried.

## Effect on the study

### Explicit scenario clocks after the collection cutoff

Runs 42570952592 (PR), 42570945270 (branch push) and 42570945149 (tag push)
at 964dfde ran after the original 9 November 05:59 UTC collection cutoff.
Their synthetic experiment suite encountered wall-clock-dependent fixtures:
three metadata-availability methods in each of the efficient/resume-v3 tests
and one wallet-cache method in each of the forecast/v2 tests. The metadata
fixtures reached the real cutoff guard before their intended mocked
transient/funding/wait scenarios; the forecast fixtures used a real generated-at
timestamp after the cutoff. This is a test-clock defect, not permission to
extend collection or evidence that offline processing needs inference.

The nonfrozen runner now gives only those eight named methods an explicit
8 November 00:00 UTC synthetic scenario time. Metadata tests receive a
module-local clock proxy: the process-global clock is untouched, and the
original tests' nested cutoff/wait clock patches still override the baseline.
Forecast tests pin only the generated-at helper; wallet-cache freshness retains
the original clock and fresh/stale assertions. All four original fixture files
are SHA-pinned and unchanged. Missing methods or changed files fail closed.
The adapter restores both references even if an assertion fails. New focused
regressions execute every original assertion, verify restoration/nested patches,
and verify that the unmodified real cutoff guard still rejects a late request
before calling even a mocked transport. No deadline, frozen policy, live
process, empirical record or failed CI run is changed.

These CI failures prevented later steps in the Ubuntu job from running; their
checks must pass on the repaired branch before claiming current CI validation.
They did not stop the independent local collectors, dispatch requests, change
records or reveal empirical answers. This diagnosis is not evidence that all
scientific results are correct: complete collection, strict replay, paper
integration and final visual review remain separate gates. No inference request
is repeated to repair this test failure. The original failed tag is preserved.

### Rate and paced synthetic scenarios after the final admission cutoff

The public-verification source/freeze commit `bd9e713` failed in PR run
42583659194, branch run 42583653014 and tag run 42583653036. The retained
experiment log reports 1,022 tests with 12 failures and 8 errors at 08:13 UTC,
after both rate/paced scheduler admission cutoffs. All twenty failures are
the same ten scenario methods in each of the rate and paced fixture files:
three metadata-availability methods and seven union-execution methods. They
reach the real ambient cutoff before their intended mocked recovery, fatal
capture/parse or provider-cap assertion. This is distinct from the earlier
eight-method fixture amendment; the failed runs remain visible.

The nonfrozen runner extends its exact method inventory by these twenty
methods, for 28 named scenario methods across six SHA-pinned original files.
The three metadata methods in each file use the existing module-local time
proxy. The seven execution methods use only a module-local `datetime`
subclass overriding `now()` to the same 8 November 00:00 UTC scenario time.
Their original fixtures mock the shared dispatch module's time gate but the
newer rate/paced implementations also have their own admission gate; the
method-scoped scenario clock lets those unchanged original assertions run.
Explicit `at` arguments and nested clock patches retain precedence. The real
process-global `time` and `datetime` behavior, live/production clock references,
cutoff values, policies, caps, assertions and original fixture bytes are unchanged.

The additional original-file pins are:

- `test_swarm_ledger_rate.py`:
  `7594d160b120e5a60994b414190bad1b45ad34b16021dc277994bf4c7415f692`
- `test_swarm_ledger_paced.py`:
  `6e7b820fd140814ef45135b01e39e23c32d2db967f5a8d16cf600cf11871c4c5`

Focused regressions execute all 28 named original methods with every original
assertion, reject missing/changed fixtures, check module-local clock isolation,
verify nested override/restoration even after exceptions, and prove explicit or
nested future clocks still trigger the real rate/paced cutoff guards. No full
local experiment rerun or inference is needed for this test-only repair.
Green synthetic checks do not replace current empirical public replay, actual
PDF verification, final exact-commit CI or the separately queued reviews.

### Scripted connection completion order

The artifact commit `49027a8` has a retained failing push run 42591399764 and
a successful PR run 42591409383. The push's only failure among 1,024 tests is
the nested original paced connection fixture's `gate.checks >= 2` assertion.
The same artifact's successful PR is consistent with an intermittent fixture
schedule, not a deterministic cutoff failure or permission to ignore the red run.

That fixture supplies three never-started fake jobs with a per-model cap of
two. If a success is observed before the connection failure, the third job can
be admitted before the failure is observed. Once every job is admitted, there
need not be pending work that requires another health cycle. The original
assertion implicitly assumes the connection failure is observed while a later
job remains never started. Production recovery behavior and caps are unchanged.

Only the existing SHA-pinned
`test_swarm_ledger_paced.UnionTests.test_connection_failure_is_retained_once_and_only_unstarted_continue`
now receives a scoped fixture adapter controlling observed completion order.
It uses the genuine original `wait` on the scripted `new-connection` future
first; other real fake futures remain in flight and their results are consumed
after the fault. No future, result, health call, reservation, cap or assertion
is invented, altered or skipped. The production collector and process-global
executor/wait functions are untouched. The owning module's alias is restored
even on failure; nested adapters retain the same observation semantics.

A deterministic adversarial order observes good and later successes before the
failure and reproduces the original `checks == 1` assertion failure. The same
order with the adapter passes every unchanged original assertion, including
one retained failure, full unknown reservation, exactly-once calls and unchanged
old journal bytes. Regression coverage checks normal/nested wrapping and
exception restoration. This repairs a synthetic scenario assumption, not a
production outage or empirical observation. Eleven focused regression tests
pass normally and under optimized Python. The deterministic failure/control
test also passed 25 consecutive repetitions in each mode; this exercises the
original failing ordering and normal/nested adapted controls each time, rather
than rerunning the entire experiment suite or retrying a failed CI job.

## Primary references

- [Python 3.12 lock objects](https://docs.python.org/3.12/library/threading.html#lock-objects):
  protect the shared operation that assigns the ordinal, rather than relying on
  thread scheduling or a sleep to order requests.
- [Python 3.12 mock patching](https://docs.python.org/3.12/library/unittest.mock.html#patch-object):
  the synthetic adapter is scoped to the test run and restored afterward.
- [GitHub Actions status expressions](https://docs.github.com/en/actions/reference/workflows-and-actions/expressions):
  subsequent steps normally require earlier success. The fix keeps that failure
  behavior; it does not use `continue-on-error` or suppress downstream guards.
