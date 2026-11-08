# Prospective collection connectivity helper

This helper is an operational dependency of the separately registered router-reset
continuations. It is not a new experiment, an analysis amendment, a retry policy,
or a claim that the incomplete cohorts are complete. It makes no provider call at
import and does not load credentials. Each continuation must bind this source,
its tests and this protocol before fresh inference. Earlier frozen transports,
records, generic failures and unknown-cost holds remain unchanged.

The user confirmed that their router resets at 05:00 GMT. For this November
collection the operational window is UTC. New inference dispatch is forbidden
from 04:55 inclusive through 05:05 exclusive, every UTC day; this leaves five
minutes before the known reset to drain already submitted requests with the
registered socket timeouts of at most 180 seconds. A timeout is not proof of an
absolute end-to-end deadline, and the caller must still drain every actual future.
The collection cutoff remains 9 November 2026 at 05:59 UTC. The helper never
changes a system power, router, network, billing or model setting.

## Gate contract

`ConnectivityGate(probe, clock=..., sleep=..., deadline=..., pause_seconds=900)`
begins with health verification required. `dispatch_allowed()` is a nonblocking
metadata-only check: it is false before initial health verification, after a
reported connection failure, during the reset window and at/after cutoff. A
reset-window check also requires a new health pair after the window.
Crossing the scheduled reset since the last verified pair requires a new pair
even if a long cooldown skipped every check inside the blackout window.

`before_dispatch(force_health=False)` permits new dispatch only after two
successful authenticated catalog checks at least 15 seconds apart, initially and
after any connection fault/reset window. A false probe resets the pair. The
injected probe must be a bounded read-only GET to one of the original catalog
endpoints: Adaption `/api/v1/models?type=hosted`, HF router `/v1/models`, or Ollama
`/api/tags`. It validates HTTP 200, bounded JSON and the required unchanged model
catalog before returning a literal true. The provider/credential owner supplies
this callback; the helper cannot attest an arbitrary callback's behavior.
Authentication, authorization, funding, invalid catalog/model or other validation
exceptions must propagate and stop, rather than masquerade as an outage. A false
result is reserved for the caller's safely classified connectivity unavailability.

A single recovery wait is capped at 900 seconds including the reset wait and
probe time, and at the registered collection cutoff. Individual probes must also
have bounded timeouts. Sleep is bounded in intervals no greater than 15 seconds.
The gate raises a safe `ConnectivityUnavailable` when its budget or cutoff is
reached. A caller must retain all records and stop without automatically
restarting after an exhausted wait. Wall-clock jumps are an operational limit;
the helper also accounts for its requested sleep budget to prevent unbounded
waiting under a nonadvancing injected wall clock.

`connection_failed()` marks health verification required. It does not send,
retry, relabel, remove or replace a request. The continuation drains submitted
futures before waiting and calls the gate before reserving/journaling a *new*
attempt. The gate serializes its own health operations but does not submit
requests or claim to make a whole collector atomic. The collector owns dispatch
coordination, capacity limits and crash-safe journals.

Existing provider cooldown and Retry-After rules remain separately binding. A
successful connectivity probe does not erase a cooldown or mean an inference
request is safe to repeat. Read-only metadata checks may repeat within the bound;
inference POSTs do not.

## Single-attempt transport contract

`safe_request(opener, request, timeout=..., max_bytes=...)` calls `opener.open`
exactly once and returns `(public_status, native_json_or_none, private_receipt)`.
It records HTTP status immediately upon receiving the response, before reading,
size validation or JSON decoding. It separately classifies `open`, `read`,
`size_check`, `json_decode` and successful `complete` stages. The caller owns
subsequent native normalization and durable `receipt_write`; a receipt-write
failure must remain fatal and be diagnosed separately by that caller.

Safe public diagnostics contain stage, exception/reason class, numeric errno or
winerror when present, start/end UTC timestamps, latency, bounded body byte count
and SHA-256, and sanitized MIME/content-length metadata. They exclude exception
messages, URLs, request IDs, raw headers, credentials and response fragments.
Only numeric reset fields, a parsed numeric/date Retry-After, MIME and content
length are returned as a private header allowlist. Native JSON or a bounded
16-KiB HTTP error body is returned privately solely for the frozen normalizer,
overload classifier and scrubbed private receipt capture; it is never public
diagnostic text. Raw body hashes establish commitments, not semantic validity.

Only network-like `URLError`, `OSError`, timeout or incomplete-body-read failures
during open/read can set `connection_fault`. Incomplete reads retain only a
bounded partial-body hash/count, never a partial response fragment. Recognizable
TLS errors are excluded; malformed HTTP status lines are fatal protocol errors.
JSON/size failure,
HTTP authorization/funding failure, model mismatch, semantic failure or receipt
capture failure is not a connectivity recovery. HTTP error-body capture failure
sets `capture_failed` and must stop the caller. An HTTP 200 followed by malformed
JSON retains status 200 and remains a validation failure, not a successful answer.

No request is automatically retried. A failed inference remains a terminal
operational failure, with the continuation's full unknown-cost reservation and
original identity preserved. A connectivity pause governs only untouched future
requests. The helper cannot recover whether a remotely accepted request completed
when its reply was lost.

## Verification and sources

Synthetic tests exercise exact window boundaries, the healthy pair, reset of a
pair after failure, finite pause/cutoff, fatal catalog checks, preserved HTTP
status on malformed JSON/read failure, size caps, safe errno-only diagnostics,
TLS exclusion, incomplete-body/malformed-status handling, HTTP error/Retry-After
capture and exactly one opener invocation.
They use no provider, credentials or empirical answers.

[HTTP semantics section 9.2.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2)
warns against automatic retries of non-idempotent requests without knowledge that
they are safe or were not applied.
[Python urllib.error](https://docs.python.org/3.12/library/urllib.error.html)
documents the underlying `URLError.reason` that can supply a safe exception class.
[Adaption's Python library](https://docs.adaptionlabs.ai/api/python) documents
automatic retry defaults; these continuations do not adopt those SDK defaults.
The unchanged Track 4 question concerns evidence versus reasoning, not router
reliability. Connectivity metadata must not be reported as model behavior or an
experimental evidence-restoration intervention.
