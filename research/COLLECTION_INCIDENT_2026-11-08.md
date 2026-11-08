# Collection incident: 8 November 2026

Status: investigated operational stop; continuation proposed, not registered or
started. The complete MAIN and original HF recovery remain incomplete. The
historical paper is unchanged. No empirical reader outcomes were inspected to
choose this recovery, and no inference request was made during investigation.

## What happened

At 05:00:34.222 UTC Windows WLAN AutoConfig recorded event 8003, explicitly
reporting disconnection from a wireless network. NetworkProfile recorded
`Network Disconnected` at 05:00:34.277. Successful WLAN reconnection was recorded
at 05:02:07.223, followed by `Network Connected` at 05:02:07.351.

Six Adaption reporter requests ended with `transport_or_json_error` at approximately
05:00:34; their recorded latencies range from 15.765 to 69.078 seconds. The HF
request started at 05:00:31.085 and ended at 05:00:38.143 with the same generic
classification. The aligned local network events strongly support a shared
client connectivity interruption as the trigger. They do not establish why the
wireless connection dropped, whether each POST reached its provider, or whether
generation completed remotely. This is an inference from the correlated records,
not a reconstructed exception trace.

Read-only authenticated model-catalog checks at 06:35:52 UTC subsequently returned
HTTP 200 and valid JSON from all three services: Adaption, HF and Ollama. These
checks establish restored metadata access, not inference reliability, credit
entitlement or success of future calls. No inference or training was requested.

## What the collector did and what its diagnostics lost

The MAIN transport in `experiments/swarm_ledger_study.py` and the HF capture path in
`experiments/factorial_continue.py` combine network, timeout, operating-system and
JSON/value exceptions into one generic error. HTTP status is assigned only after
reading and parsing the response. Consequently, `http_status: null` does not prove
that no HTTP response arrived. It can also represent an unreadable or malformed
response, or a failed response-size check. Original exception details were not
retained, so this distinction cannot be repaired retrospectively.

The collectors durably write request attempts before submission. They retained
the failed terminals, kept full reservations where usage was unknown, stopped new
dispatch and drained in-flight work. The stop was a conservative protocol guard,
not a credit-limit or transient-error-allowance stop. Existing resume commands
intentionally reject a fatal stopped prefix; deleting stop files or changing
driver PIDs would bypass the registered rules.

## Coverage at the stop

| Population/phase | Terminal / planned | HTTP outcomes |
|---|---:|---|
| MAIN principal | 640 / 640 | 640 successful HTTP responses |
| MAIN coordinator | 640 / 640 | 640 successful HTTP responses |
| MAIN X | 2,560 / 2,560 | 2,560 successful HTTP responses |
| MAIN Y | 2,560 / 2,560 | 2,517 HTTP 200; 43 HTTP 504 |
| MAIN reporter | 1,752 / 2,560 | 1,695 HTTP 200; 51 HTTP 504; 6 generic transport/JSON failures |
| Original HF recovery v2 | 1,732 / 1,889 | 1,657 HTTP 200; 73 overload HTTP 429; 1 HTTP 503; 1 generic transport/JSON failure |

The nine earlier HF completion terminals remain separate and retained. They are
not part of the v2 denominator above. Successful HTTP delivery is not synonymous
with semantic validity or a correct audit decision. MAIN readers, calibration
readers and the influence extension had not started.

Every started identity in the stopped reporter and HF v2 journals has a terminal
record. This does not resolve whether a provider executed a request whose reply
was lost. Prefix-hash, unique-identity, terminal-subset, source-hash, pacing and
reservation-cap checks found no journal mutation or duplicated identity. This is
operational integrity evidence, not certification of scientific correctness.

## Consequences for this project

The seven generic failures are recorded operational failures, not successful
answers and not unstarted requests. Preserve them in the final denominators and
uncertainty/accounting disclosures. Preserve all earlier 429/503/504 failures too.
Unknown provider completion must not be converted into a new answer by retrying.

The local shared interruption is different from the experiment's manipulated
evidence loss. Do not describe it as an experimental restoration intervention,
adversarial behavior, model reasoning failure or proof of corruption/leakage.
The frozen host logic already treats invalid worker deliveries as no operation;
reporters produce notes rather than host actions. Retaining failure flags is
necessary to distinguish delivery, evidence sufficiency and reasoning later.

The main Track 4 objective remains: does an auditor lack evidence, or fail to use
sufficient evidence? Completing the same matched cohort is more informative than
replacing failed conditions, changing families, or introducing fine-tuning during
recovery. The independent unit remains 640 base blocks. A collection interruption
does not create a new independent sample or justify changing the primary endpoint.

## Recommended next steps, in order

1. Preserve and hash the stopped plans, attempt/terminal journals, native receipts,
   summaries, operational records and driver states. Verify original request/body,
   model, native-receipt and cost commitments before admitting a continuation.
2. Implement separate prospective continuation collectors and a strict union
   verifier. MAIN has 808 unstarted reporter calls, followed by 53,760 MAIN reader,
   240 calibration and 240 influence calls: 55,048 remaining MAIN calls in total.
   Original HF recovery has 157 unstarted requests. Derive these complements from
   the frozen plans and the union of all started identities; never hard-code a
   replacement list from successful responses alone.
3. Keep endpoints, request bodies, ordering commitments, sampling, decoding,
   scoring, budgets and existing failure reservations unchanged. Record the new
   collection batch/time. Never overwrite the stopped archives, edit their states,
   remove their stop files, or recycle a started request identity. Any change to
   stopping behavior must be explicitly registered as an operational amendment.
4. Add safe prospective transport diagnostics: response status before JSON parsing,
   failure stage, exception class, numeric errno/winerror, timestamps, bounded body
   byte count/hash and allowlisted content metadata. Exclude exception strings,
   credential-bearing headers and raw response fragments. Distinguish transport,
   parsing, size-limit and receipt-write failures. Retain unknown-cost holds.
5. Before every new inference batch, verify connectivity and the unchanged model
   catalog using bounded read-only checks. On connection loss, pause *new* dispatch
   and drain already submitted requests; do not replay those requests. Define
   finite wait/stop behavior, accounting for observed outage and existing cutoff.
   Do not silently inherit an SDK's default automatic retries.
6. Test duplicate-send rejection, byte/body parity, disjoint journal union,
   preservation of failed terminals, unknown-cost reservations, diagnostics,
   cooldowns, fatal guards and synthetic-analysis parity. Reforecast remaining
   cost and duration with the actual stopped-prefix metadata and remaining time.
7. Commit, freeze, tag and push the continuation protocol and union analysis before
   fresh inference. Then collect only the registered complement. Restore periodic
   health checks for the new actual processes. The previous heartbeat was deleted
   after its monitored collectors and postprocessors exited.
8. Release only after full union verification. Integrate all conditions and failures
   into the official-template paper with plots and explicit batch/provenance limits.
   Then complete the four previously queued investigations/reviews. No complete
   release or final-paper claim is justified at this incident checkpoint.

## Primary sources and interpretation

- [Python urllib.error](https://docs.python.org/3.12/library/urllib.error.html)
  documents that `URLError.reason` can retain the underlying exception. The local
  code discarded that detail; future safe classification can retain its type.
- [HTTP semantics, section 9.2.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2)
  cautions against automatically retrying non-idempotent requests without knowing
  they are safe or that the original was not applied. This supports preserving
  ambiguous POST outcomes rather than assuming a failed send.
- [Adaption Python library](https://docs.adaptionlabs.ai/api/python) documents two
  default retries for connection errors and selected HTTP errors. This study uses
  its own urllib transport; those SDK defaults were not active. A recovery must
  not accidentally introduce them by changing clients.
- [Adaption Responses](https://docs.adaptionlabs.ai/api/resources/responses) supports
  retrieval by response ID. The failed requests retained no usable response ID;
  this is not a documented recovery mechanism for these seven unknown outcomes.
- [Microsoft wireless troubleshooting](https://learn.microsoft.com/troubleshoot/windows-client/networking/wireless-network-connectivity-issues-troubleshooting)
  recommends correlating disconnect times and event logs before changing client
  configuration. The local event timeline above is the direct incident evidence;
  no SSID, interface identifier or account information is published.
- [Apart guidelines and Judging and results](https://apartresearch.com/sprints/swarm-alignment-2026#guidelines)
  remain the project reference. Transparent provenance, unchanged comparisons and
  clear limitations support execution quality and clarity; more requests or a
  hidden retry do not themselves establish research impact.

The 20-rules-of-learning skill guides this explanation's ordering: concrete event,
failure mechanism, implications and next actions. It supplies no empirical evidence
for the experiment or guarantee of judging scores.
