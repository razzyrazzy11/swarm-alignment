# Swarm Ledger: review provenance and dispositions

Date: 7 November 2026. This is an engineering/design review record, not new
experimental evidence or a guarantee of correctness. Main-study results must
come from retained empirical records under the registered protocol.

## What was actually reviewed

A completed OpenCode cross-model **design** critique used the enabled
`security-reviewer` agent with the exact discovered model
`ollama-cloud/deepseek-v4-pro`.

- Task: `5ca45d05-e6de-47c2-a18a-6f3feaceb6db`.
- Run: `488bbd1e-73cf-4583-b815-8ffd205824a3`.
- Result: completed, with a written critique; zero tool calls.
- Payload: a compact abstract description of the sampling, estimands, bootstrap,
  spending guards, unknown-send handling and journal design. No source files,
  credentials, study contexts, raw receipts or experimental outcomes were sent.
- Runtime provenance: `.opencode-recovery/ledger_cloud_result.json` outside the
  research repository. The owned server and bridge were stopped afterwards.

The fresh locally saved Ollama credential was supplied only through a child
process environment and task-local `{env:OLLAMA_API_KEY}` configuration. No global
authentication setting was changed. Configuration support was checked against
the [official environment-substitution documentation](https://opencode.ai/docs/config/)
and the versioned
[v1 provider schema](https://github.com/anomalyco/opencode/blob/v1.19.5/packages/core/src/v1/config/provider.ts).
The provider/model identifier came from the running server's actual catalogue.

Earlier free-GLM discovery and OpenCode-Go Qwen design-review attempts produced no
text or tool calls and were cancelled after bounded waits. They are **not**
successful reviews and do not establish a particular quota or authentication
failure. The later fresh-key Ollama design review did produce a result.

A subsequent request for an actual source-code review was blocked by automatic
approval review **before launch or upload**. Its stated reason was that uploading
private repository source files to Ollama Cloud required authorization for that
payload and destination beyond experiment access. Three allowlisted files were
copied locally, but no source-code payload was sent. This restriction was not
bypassed. At that point no external code review had completed.
The user subsequently replied, “Authorize these three files for Ollama Cloud
review,” authorizing exactly `swarm_ledger_study.py`, `swarm_ledger.py` and
`SWARM_LEDGER_PROTOCOL.md`, excluding credentials, raw runs and account data.
The retry passed automatic approval. A fresh isolated review was then requested
using the same discovered Ollama model and child-environment credential route.
Its source snapshot is:

| Authorized file | SHA-256 of supplied local copy |
|---|---|
| `swarm_ledger_study.py` | `54f587b6f3a6fd610829d7839bdfe4db96162ce136c5c46d823b83bd949439cf` |
| `swarm_ledger.py` | `79ca3d15d57c315f1c6eca39cadcec400ccff49957395955b9041c97dc706aab` |
| `SWARM_LEDGER_PROTOCOL.md` | `79334ba3f14244bd40b8ad312a0829263358acd954d87d39cfa7b552836dd668` |

Task `d5754529-df0d-4841-85aa-59d6fb7762fb` is the separate actual-code review.
Initial run `69b88444-aca5-4d96-9926-075477a22c99` completed four read-tool calls
but returned no final text. One text-only continuation, run
`e16dd7dc-81ff-49f4-9738-0cd3cc9db8bd`, returned a written review using the
already-read files and no further tools. The reviewer reported reading the
collector through line 863, the complete finite engine, and the complete
protocol. The whole review finished within approximately four minutes. Final
runtime provenance is `.opencode-recovery/ledger_code_result_final.json`, outside
the research repository. The owned server and credential-bearing child process
were stopped afterwards.

### Actual-code findings and dispositions

| Finding | Disposition before registration |
|---|---|
| Medium: `influence_worlds` retained the original X note rather than the replacement actually shown to the fresh Y receiver. | Fixed. It records the registered replacement at `notes[2]`, the fresh receiver note at `notes[3]`, and an explicit no-reporter marker at `notes[4]`. `actor_valid=[]`, `receiver_valid` remains separate, and `reporter_present=false` prevents an inherited main reporter from appearing newly executed. A regression checks all fields. Labels and main-study calls are unchanged. |
| Low: `drain()` silently swallowed receipt/future exceptions behind another stop reason. | Fixed. Drain and normal completion paths retain only sanitized `{id,error_class}` diagnostic entries. Exception text is excluded. An ambiguous start stays unresolved, financially held and ineligible for automatic retry; no fake terminal is created. |
| A crash can leave an exclusive collector lock and recovery was not documented. | Accepted as an operational limit. Lock removal must follow explicit process/receipt reconciliation under the protocol; no lock is automatically deleted and no protection is relaxed. Protocol recovery guidance belongs to the final operating instructions. |
| Reservation arithmetic, native replay, durable start-before-send, unknown-send blocking and finite engine/contract consistency. | No blocking defect found by the reviewer in the three authorized files. This is a finite review, not a proof. |
| Absolute budget figures, gateway allowance and profile catalogue values. | Outside the external review scope: config and catalogue were deliberately not uploaded. They require the separate local validation and technical gates. |

The targeted fixes were tested locally after the external review; the changed
source was not sent again. Their resulting raw-file SHA-256 values are:

- Collector: `3324c24ff88ca02ac0f79083bf40ce44fd95a823beaf0a162a939072ab76a83a`.
- Collector tests: `d573c0f2a5e1359e87d77b46f17e5d4c929a37ae9251344bdc19b70eec35f7b4`.

## Cross-model design findings

| Finding | Disposition |
|---|---|
| The reviewer conflated four actor profiles with four threat arms and proposed reducing the number of strata/blocks. | Rejected. Actor profile, policy and layout define 40 strata. The four actor profiles come from three families: Gemma, Qwen and GLM. Each of the 640 independent base blocks separately contains all four assigned threat arms. Actor profile and threat-arm assignment are distinct factors. |
| Resample the dependence unit rather than treating descendants as independent observations. | Accepted and already specified: resample whole base blocks within each fixed stratum, retaining every descendant arm and paired reader condition together. |
| Invalid/refused monitor answers need an explicit scoring rule. | Accepted. Invalid verdicts score incorrect; they remain in assigned denominators. A valid ABSTAIN is supported-correct when evidence is ambiguous, but does not count as correct-definite. Under FULL evidence the compatible label is definite. |
| The factorial contrast measures actual-action interaction. | Clarified: it estimates interaction of **assigned instructions** on realized incident yield/utility. Actual actions are outcomes/mediators, not inclusion criteria. No conditioning on successful attacks or inference of spontaneous collusion is justified. |
| Identical X receipts cannot be ensured because X is stochastic. | Rejected for the registered extension: first realize X, then clone that authentic state for three fresh honest-Y receiver calls. This does not establish effects on adversarial receivers. |
| Multiple contrasts need a hierarchy. | Accepted and already specified: one new primary; secondary intervals are descriptive individual intervals, without a familywise significance claim. |
| A request hash should permit provider-side recovery without resending. | Not assumed. No such recovery guarantee has been established for these endpoints. Unknown sends remain unresolved and block continuation; they are not replaced with new observations. A failure may leave an incomplete cohort, which must be reported honestly. |
| Reservations must be released after reconciliation. | Already implemented under the collector lock: remove the in-flight reservation and add actual known cost; retain the full conservative reservation for unknown usage. Fatal drains use previously held reservations. |
| Unknown reservations need finite per-request bounds. | Already implemented using the fixed input ceiling, output limit and registered published rates. These are conservative estimates, not invoice guarantees. |
| A cached balance is a provider-enforced hard spending floor. | Not claimed. The study subtracts spending since its poll plus in-flight reservations, polls at most once per minute and stops at its floor. Provider billing lag or concurrent unrelated account usage can limit this protection. |

The stratified interval assumes independent/exchangeable base blocks within each
fixed stratum. Fixed endpoint aliases do not establish identical hidden weights
or independence from provider-wide temporal effects. The interval targets this
registered synthetic design, not an unrestricted real-world swarm population.

## Local code checks and fixes before registration

The local review checked collector, finite engine and protocol consistency.
Material fixes completed before fresh study data include:

1. Five-role actions use bounded mutations of fresh fake dictionaries. Y receives
   the actual X local receipt; the reporter receives claims. Notes cannot create
   authority or substitute for authentic evidence in the oracle.
2. Own A–E verdict/schema handling prevents reuse of the older three-worker
   decoder. A schema constrains enumerated output shape; it does not establish
   the correct worker binding, correct logic, or an accurate verdict.
3. A complete private-context validator checks the registered actor-profile/policy/
   layout/repetition grid, opaque identities, role permutation, lease width of
   three time units, settlement-time policy and revocation policy before paid calls.
4. Native receipts are stored and hashed. On replay, the collector re-normalizes
   the hashed receipt, compares usage, model/format anomaly and normalized output,
   and then reconciles cost. HTTP error bodies cannot become completed responses.
   Altering normalized usage and estimated cost alone cannot reduce replayed cost.
5. Starts are durably reserved before dispatch. Ambiguous sent requests cannot be
   reissued. Fatal stops are persisted, and another phase cannot bypass an
   unresolved send or fatal stop to discard an outstanding financial reservation.
6. The overload classifier uses structured error fields or a leading recognized
   message; an arbitrary occurrence of the words “server overload” is not enough.
7. Config caching is bounded and keyed by resolved path and file metadata. No
   mutable cached object escapes; same-size file edits invalidate the cache.
   An explicit verified snapshot enables bulk replay without repeated file I/O:
   entry reads and hashes actual config bytes, exit checks actual bytes and
   snapshot integrity, and nested contexts are reentrant. Paid collection also
   checks the real config hash at metadata checkpoints after draining in-flight
   requests. Registration hashes actual source bytes independently of the cache.

The collector test module passed **26 offline tests** after these hardening
changes. These cover schema/encoding, ambiguous evidence, bounded invalid actions,
   handoffs, reader projection, development/calibration scope, influence matching,
native usage/model checks, reserve-before-send, budget denial, unknown-send
restarts, cross-phase stops, context drift, native-cost tampering and config-cache
invalidation, verified-snapshot file drift, mutable-copy protection and faithful
influence-state replay. They are
finite checks, not exhaustive correctness evidence. Reader comparisons cover
eight profiles from five families: Gemma, Qwen, GLM, Llama and DeepSeek; profiles
are not counted as independent source blocks.

## Remaining gates before collection claims

Commit and tag the complete registered source/config/protocol set before each
fresh cohort. Verify technical service gates without selecting models by task
accuracy. Use development usage—not held-out outcomes—to check whether the entire
registered workload fits each provider budget before starting main collection.
The runner's `cost_forecast` covers reader calls and scripted calibration only;
actor/influence costs require a separate development-usage forecast.

Published rates and token projections do not guarantee invoices or a complete
cohort. Do not launch a workload already projected to exhaust its cap, silently
change endpoints, hide stopped conditions, or describe a partial condition as
complete. Any operational continuation preserves previous terminals and requires
its own prospective amendment. Main results, graphs and paper claims remain
pending until actual empirical collection and independent public replay pass.
