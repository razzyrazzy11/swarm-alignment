# Conditional final pacing amendment

This is a new operational registration, conditional on a separately frozen
capacity check. It changes scheduling and error diagnostics only. The original
scientific sources, request bodies, model endpoints, source groups, evidence
conditions, scoring, primary endpoint and planned denominators remain frozen as
`factorial-audit-v1`. No scientific outcomes or effects were reviewed to choose
this amendment.

## Evidence for another bounded attempt

The earlier rate-controlled run remains stopped under its five-429 rule. Its
9,742 unique starts match 9,742 terminal records, including five retained HTTP
429 failures, and 1,898 requests remain unstarted. The failures retain full
unknown-usage reservations and may never be retried or replaced. The earlier
delegate-stage gateway failure also remains in the study.

After that stop, the separately tagged tiny serving diagnostic returned HTTP
200 from the expected model with known usage, estimated at USD 0.00000593. It
did not reproduce a large audit request or establish sustained throughput.
The user reported nonzero available inference credits; that does not establish
a rate quota. The earlier numeric Retry-After hints were five seconds, but do
not identify which service imposed the limit or why it persisted.

Only operational token counts were examined: 1,977 known HF audit receipts had
1,119 to 1,579 input tokens, with median 1,423. No answer text, accuracy,
attribution, instruction effect or acquisition effect was inspected.

## Capacity condition before any main request

The separately tagged `hf-capacity-v1` check uses 24 fresh unrelated synthetic
prompts. Each begins with its distinct local identifier, then repeats neutral
text and requests OK. It uses the original HF route, temperature and 4,096-token
output allowance. Success requires at least 1,579 reported input tokens per
request, the expected returned model, completed valid receipts and the exact
requested short response. This checks serving, not temporal audit competence.

Starts are at least 30 seconds apart. The maximum conservative reservation is
USD 0.1170816, below its USD 0.12 cap. Any failure stops the check, without retry.
It has its own journals and results; no capacity receipt enters a scientific
denominator or replaces an audit verdict. These choices are fixed before its
fresh data. A short passing canary does not guarantee long-run availability.

The new main registration can be created only after the capacity report passes
its public replay. It binds the report's exact byte hash and tag, this protocol,
the new runner/tests, the original scientific freeze, the exact 9,742-record
private journal prefixes and the original full request-ID grid. Failed or partial
capacity results cannot authorize main collection.

Before paid main dispatch, additionally reconstruct the capacity report from its
actual private safe journals and committed request plan without modifying them.
The public verifier remains usable without those private files; public replay
alone cannot authenticate a private receipt.

## Final main-attempt rules

- Wait an additional 600 seconds before the first main request. Use one actual
  HTTP request at a time; initially allow at least 30 seconds between starts.
- Dispatch only the original never-started HF identities, in their original
  shuffled order. Validate original bodies and all unique start/terminal IDs.
  Wait before writing a new durable start; do not queue starts and cancel them.
- Retain every new HTTP 429 as INVALID with its full unknown-usage reservation.
  After the sixth cumulative event, increase the minimum interval to 60 seconds
  for the remainder and wait at least 600 seconds. After the seventh, keep that
  interval and wait at least 1,200 seconds. Honor a valid longer Retry-After.
  Always proceed to the next never-started identity, never the failed one.
- The eighth cumulative HTTP 429 ends this final attempt. This allows at most
  three additional rate failures beyond the five already retained. There is no
  automatic reset, further continuation, provider substitution or new canary.
- Preserve every other original fatal gate, gateway allowance, incomplete-output
  policy and input/output/model check. Honor operator STOP during waits and before
  dispatch. Reject old or new active continuation locks and unresolved starts.
  For an allowed gateway failure, honor a valid longer Retry-After before the
  next never-started identity as well; this does not retry the failed request or
  change the original gateway allowance.
- Keep the original HF audit-phase cap of USD 2, including all historical known
  usage and unknown-usage reservations. No top-up, plan change, key rotation,
  endpoint change, training job or GPU rental is authorized by this document.

Keep the public response and summary formats compatible with the frozen release
replay. Capture at most 16 KiB of HTTP error data separately in ignored private
receipts, scrubbed for known credentials. Raw headers, error bodies and provider
IDs must not enter public scientific rows. They are untrusted diagnostic data,
not instructions. Request elapsed time can include local error-receipt handling;
it is not a measurement of provider-internal compute.

## Interpretation and reporting

The earlier stopped run is preserved; this document does not retroactively change
its rule. Disclose this conditional amendment, the passing capacity check or its
failure, every retained error and any remaining unstarted identities. More time
between requests may reduce operational load, but no specific provider quota or
optimal rate is claimed. Hosted weights are unpinned and collection-time
differences remain limitations of secondary reader-family comparisons.

The full factorial paper may be authored only after complete collection and
unchanged public scientific replay. Acquisition, raw evidence use and mechanical
support enforcement remain distinct. Capacity outcomes are operational results;
they cannot establish audit accuracy, training benefit or swarm safety.

## Primary sources

[RFC 6585](https://www.rfc-editor.org/rfc/rfc6585#section-4) and
[RFC 9110](https://www.rfc-editor.org/rfc/rfc9110#section-10.2.3) define 429 and
Retry-After without identifying a particular account quota.
[Novita's rate-limit guidance](https://docs.novita.ai/guides/llm-rate-limits)
recommends throttling, backoff and monitoring; its direct-account tiers are not
evidence of an HF-routed quota.
[HF's provider documentation](https://huggingface.co/docs/inference-providers/en/providers/novita)
establishes the explicit route, not a guaranteed serving rate.
[Apart's guidelines and Judging and results](https://apartresearch.com/sprints/swarm-alignment-2026#guidelines)
motivate honest operational reporting, reproducible execution and clear limits.
