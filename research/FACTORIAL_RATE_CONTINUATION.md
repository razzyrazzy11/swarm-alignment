# Prospective operational continuation after HTTP 429

This amendment changes request scheduling only. The scientific protocol remains
`factorial-audit-v1`: the same workers, source groups, packets, prompts, endpoints,
request bodies, scoring rules, denominators and analysis. No interim scientific
outcomes were inspected to choose this amendment.

## Why this continuation is needed

The original account-cushion stop preserved 9,706 audit terminal records and left
1,934 requests unstarted. Following the user's funding confirmation, the tagged
`factorial-audit-v1-account-resume` continuation completed four more requests and
received one HTTP 429. It stopped and drained: 9,711 starts have 9,711 terminal
records, leaving 1,929 requests unstarted. The failed request remains INVALID with
its full unknown-usage cost reservation. It must never be retried or replaced.
The original delegate-stage gateway failure also remains in the study.

The earlier transport did not retain HTTP error headers. Consequently we cannot
identify whether HF or its upstream provider imposed the limit, or recover the
server's requested waiting period for that event. Funding confirmation is not
evidence that a particular rate quota has changed.

## Scheduling and stopping rules, registered before further requests

The separately tagged registration binds this document, the continuation runner
and its tests, the original scientific freeze, the existing journal byte hashes,
and the complete original request-ID grid. Run only the original never-started
HF requests in their original shuffled order. Validate all existing request/body
identities and reject duplicate IDs, unresolved starts or changed prefixes.

Use one HTTP request at a time, with at least 12 seconds between starts. This
five-per-minute ceiling is our conservative operational choice, not a claim
about a documented HF or Novita quota. Wait before journaling a new start; never
create queued starts that are then silently cancelled. Preserve durable start
and terminal writes, original response normalization and the public export
contract. Capture only numeric waiting information in an ignored sidecar;
never release credentials, raw headers or error bodies.

Start this continuation with an additional 300-second cooldown because the
historical error's requested delay is unavailable. An exclusive run lock prevents
two continuation processes dispatching the same unstarted identities; a stale
lock requires investigation rather than automatic recovery. Numeric reset-header
values are not interpreted as delays when their units are unspecified.

For another 429, retain that request as INVALID, reserve unknown usage, and wait
at least 300 seconds before considering the next never-started request. Honor
a valid longer `Retry-After` delay, including HTTP-date syntax. Never retry the
failed request. Stop permanently when the cumulative number of 429 events reaches
five, counting the already retained event. All other original fatal conditions
remain fatal; gateway and incomplete-response handling remain unchanged. Honor
operator STOP files during waits. Keep the original HF phase cap of USD 2,
including historical usage and all unknown-usage reservations. No automatic
top-up, plan change, endpoint substitution, key rotation or training is permitted.

The credential-free source/tag check is:

```text
python -m experiments.factorial_continue verify --registration research/factorial-rate-continuation.json
```

The explicit paid command is `run` with the same registration argument. It also
checks the exact private starting journals and original request bodies before
dispatch. It is not a general restart command: changed journals, unresolved starts
or a stale lock require review, not another invocation around a safety gate.

## Interpretation and reporting

This is a disclosed operational deviation from the original concurrent collector,
not a fresh scientific condition or a repaired observation. All planned requests
retain their original denominators. Report the account pause, 429 failures,
sequential continuation and any remaining unstarted requests. Hosted model drift
and collection-time differences remain limitations; the model weights are not
version pinned. Only after the full collection and independent public replay
may the new findings replace the earlier paper's completed-study results.

## Primary sources

- [RFC 6585, section 4](https://www.rfc-editor.org/rfc/rfc6585#section-4):
  HTTP 429 describes too many requests; it does not specify how a server identifies
  users or counts requests, and may include `Retry-After`.
- [RFC 9110, section 10.2.3](https://www.rfc-editor.org/rfc/rfc9110#section-10.2.3):
  `Retry-After` can contain a delay in seconds or an HTTP date.
- [HF Inference Providers](https://huggingface.co/docs/inference-providers/en/index):
  routed inference uses a provider; HF Hub API/resolver/page limits must not be
  assumed to be this routed inference service's quota.
- [Apart Swarm Alignment guidelines](https://apartresearch.com/sprints/swarm-alignment-2026#guidelines):
  execution quality and clear presentation require reproducible methods and
  honest reporting of failures, limitations and existing work. This study remains
  positioned in Track 4 around evidence acquisition versus evidence use.
