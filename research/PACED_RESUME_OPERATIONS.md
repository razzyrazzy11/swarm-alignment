# Prospective paced continuation: preserve all six conditions

This is preparation, not a registered launch. The live rate version remains
unchanged until a documented controlled STOP fully drains it and the new exact
complement, access, cost and deadline gates pass. No prior failure is retried.

## Operational evidence

Both MAIN HF conditions reached5,120terminal records at approximately19:31UTC
on8November. The subsequent native-only bursts coincided with repeated precise
Adaption rate-limit errors and long registered global waits. At the first429,
rolling60second actual network starts were35G26+22G31,57combined; later waves
followed24/25 and26/27 starts. Metadata GETs are not included in those POST
counts. These observations do not identify a provider quota, its scope, or a
per-model limit. All failed receipts, original flags and full reservations stay.

## New prospective behavior

The operating choice is a minimum3.2seconds between starts of one native model
and1.6seconds globally between native starts. Both are stricter than the prior
one-second global minimum; all original concurrency/spending caps remain.
These are conservative client settings, not claimed provider limits. Endpoint,
body, output allowance, decoding, normalization and scientific scoring remain
unchanged. Pacing claims are atomic; clock locks are released while waiting,
and the scheduler rechecks readiness on a bounded clock rather than waiting
indefinitely behind a slow call from another provider.

Only exactly recognized Adaption rate429s receive provider-scoped cooldown.
Eligible never-started Ollama work may continue during that long cooldown.
Two native health checks15seconds apart and the literal global metadata checks
precede native resumption. These checks are synchronous: they briefly block
new dispatch when healthy and can block longer during metadata trouble. This
does not claim uninterrupted provider isolation. Router/network handling,
non-rate errors, periodic100completion global drain/health barriers, fatal
authentication/funding/capture guards and all failure allowances are retained.
Historical failure counts, streaks, reservations and old cooldown/episode
evidence are preserved. This handoff may not evade an actually exhausted old
episode or a fatal stop. The old cooldown must elapse and fresh all-provider
readiness must pass before new inference; the new live episode then starts on
its first NEW failure. It is not the old timer carried across engineering time.
Within the paced version, unresolved native holds/episodes persist across its
phases. No failed identity is retried,
replaced or silently omitted; all six conditions and480auxiliary calls remain.

## Admission and timeline

The new freeze must bind the exact seven-batch union and never-started
descriptors. The predecessor must have actually stopped and drained, with its
registered controlled STOP, no fatal stop/capture/unresolved records and no
remaining owned lock. Older sources, tags, registrations and states remain
immutable. The source, collector/analysis freezes and tags must be pushed
before any new inference. Both fresh cost/access and deadline gates must pass.

The unchanged current deadline policy is07:56UTC last scheduler admission on
9November,08:00target drain,11:59official submission. Native pacing can follow
admission; socket timeout/drain allowance is not a whole-request completion
bound. The forecast adds the actual new reader pacing resource maxima and any
positive auxiliary pacing increment to the previous shared-capacity model,
retaining25%headroom,3300seconds overhead,32default500pauses,900HF and900native
availability sensitivities. It assumes no benefit from avoiding future429s or
from provider-scoped waiting. A preview is not a full admission gate.

Current paths after an admitted launch will be
runs/swarm-ledger-paced-v1-driver/state.json and
runs/paced-resume-postprocess-driver/state.json. The strict seven-stage waiter
requires actual complete terminated paced/HF collection and all immutable
predecessors. Historical paper content remains unchanged until full scientific
replay, actual verified-data authoring and every-page QA. All four queued
reviews remain after that integration. No automatic submission is authorized.

## Primary conventions

[Adaption error handling](https://docs.adaptionlabs.ai/api/python/) identifies
429 as rate limiting; SDK retry defaults are not used. The registered transport
issues one POST per identity. [RFC6585 section4](https://www.rfc-editor.org/rfc/rfc6585#section-4)
does not determine a quota's scope from a429status. The implementation and its
synthetic clock/scheduler tests are the primary source for the pacing claim;
live throughput and eventual scientific results require separate validation.
