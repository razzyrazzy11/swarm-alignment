# PID-safe release of the completed original HF condition

This is a prospective operational release amendment, registered while recovery
collection is ongoing and before supplement answer unblinding. Original outcomes
were already known. It changes no hypothesis, endpoint, request body, model,
parser, evidence oracle, scorer, statistical unit, bootstrap, cost accounting,
terminal identity, collection allowance, or stopping rule. It is not a new
scientific preregistration and does not turn failed serving into successful serving.

## Why this wrapper exists

The frozen release path requires an operating-system PID to be absent. Windows can
reuse a terminated driver's PID for an unrelated process after collection ends.
The new wrapper accepts absence or proof that the currently occupying process was
created strictly after the driver's unchanged final UTC timestamp. A process
created earlier, unavailable creation metadata, failed process lookup, active
collection, changed state bytes, or a relevant collector lock blocks publication.
It never modifies driver state, invents a PID, removes another owner's lock, or
terminates a process.

The unchanged original factorial driver must be stopped or complete. The first
completion driver must be stopped or complete (its preserved contribution is the
nine terminal prefix). The recovery driver must be complete; its contribution
must be exactly 1,889 terminal responses. Both completion parent and child process
identities are checked, and any recorded collector PID is checked. The original
driver schema records only its parent PID; no missing child identity is fabricated.
Final timestamps must be aware UTC and not future. Raw state hashes are checked
again before and after serialization.

## Source registration before private admission

After committing the new source, test, protocol and frozen PID-helper dependency,
the root operator runs:

```powershell
python -m experiments.hf_completion_release freeze
# Commit the new freeze and create the recorded tag hf-completion-release-v1.
python -m experiments.hf_completion_release verify
```

The new freeze binds those sources and the existing completion, recovery and
analysis registrations. Source verification checks the recorded tag and ancestry.
Freeze and verify inspect public registration/commitment metadata, not supplement
answers, and make no provider calls. Changing this wrapper after registration
requires a new disclosed amendment, never replacement of a frozen source.

## Admission and unchanged scientific reconstruction

Only after both completion processes have ended does the root operator explicitly
request publication:

```powershell
python -m experiments.hf_completion_release export --publish-after-collection
```

The flag is required. The wrapper reuses the frozen original ledger, recovery
ledger, native normalization, request-body validation, historical checkpoint
commitments, terminal accounting and numerical analysis. It copies only the nested
orchestration that previously called PID-absence-only guards. No production
monkeypatching or replacement scientific helpers is used.

Admission requires the immutable 9 + 1,889 disjoint terminal union, all 1,898
registered original identities, no unresolved starts or unstarted identities,
reconciled known costs/full unknown reservations, all historical errors retained,
and unchanged original primary estimate and interval. Failed requests remain
terminal failures. No request is repeated or imputed. Raw plan, attempt, response,
summary and error-receipt bytes are committed and checked across publication.
Only relevant original/HF collector locks are checked; unrelated MAIN collection
is a separate registered experiment and its locks are not removed or bypassed.
The wrapper holds the original continuation lock and recovery collector lock
through final verification and companion proof creation.

The frozen serializer writes exactly the existing paths and schemas:
`data/hf_completed_original_supplement.jsonl` and
`research/hf-completed-original-results.json`. The frozen
`hf_completion_analysis.verify_public()` remains the final scientific authority.
Existing outputs are never overwritten. A serialization-parity test compares
both report and supplement bytes with the frozen exporter under synthetic inputs.

## Separate operational proof and limits

`research/hf-completed-original-release-proof.json` is a new companion, outside
the old strict report schema. It records the release-registration hash, actual
raw driver-state and private-archive commitments, public-output hashes, the frozen
verifier result, and zero inference calls. It contains no credentials, account
balances, native answer bodies, or substituted scientific statistics. The
companion does not make private native authenticity publicly reproducible; that
still requires the retained private journals. Public reconstruction remains
available through the unchanged frozen verifier.

Synthetic tests cover active or unproven-reuse rejection, proven later PID reuse,
parent/child and state-byte checks, locks, source/parent-registration drift,
request/native public-allowlist tampering, raw private-byte changes, unchanged
bootstrap use, explicit publication gating, and serializer parity. No test opens
actual completion answer journals or calls an inference service.
