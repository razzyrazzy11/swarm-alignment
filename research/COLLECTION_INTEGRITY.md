# Collection integrity and sprint requirements

Reviewed 6 November 2026. This is a retrospective integrity map, not a change to a frozen protocol. Main collection, HF replication and the influence arm have finished. Offline checks do not make new API calls.

## Keep service errors separate from scientific outcomes

The [Adaption Responses API](https://docs.adaptionlabs.ai/api/resources/responses/methods/create) documents response status, usage, model identifiers and fresh response inputs. The frozen runners use explicit model IDs, fresh context, temperature zero, a 4,096 output-token allowance, empty tools, tool choice none, memory off and storage off. An API key is loaded locally; it is never a command-line argument or a released field. HTTP requests have a 120-second timeout and same-origin redirect checks.

Before dispatch, a durable start journal records the planned identity and a conservative cost reservation. Bounded concurrent batches limit requests already in flight when a stop gate triggers. Terminal responses are flushed to the journal; in-flight requests are drained on a detected failure. Unknown usage retains the reservation. The runners refuse existing output directories and provide a STOP-file control. Token estimates are client accounting controls, not provider-enforced monetary caps.

Authentication/payment/rate-limit errors, unexpected models or usage, missing usage and repeated incomplete outputs halt collection under the applicable registration. There are no automatic retries that could silently replace a failed scientific observation. A transport failure is INVALID, not ABSTAIN, NONE or a successful monitor decision. Presentation envelopes are accepted only by the declared v2 decoder; semantic answers are not repaired. Raw bare-JSON validity remains separate.

One HTTP 502 halted the original main phase at 3,028 terminal records. It remains INVALID with unknown-charge reservation. The separately tagged `stateful-main-v2-continuation-v1` authorized only the exact 812 originally unstarted identities, with an explicit bounded gateway-error allowance. Its registration preceded those calls. It did not retry the 502 or change the scientific grid, prompts, outcomes or sample size. This is an operational amendment and must not be described as an uninterrupted, unamended confirmatory study.

The combined main data contain exactly one terminal record for each of 3,840 planned identities. HF-v3 has 240/240 terminal records and influence has 216/216. Prior HF serving failures and excluded Adaption qualifications remain separate. Software cannot guarantee an external service never fails. The purpose of these controls is to retain failures and protect interpretation when it does.

## Recheck the released evidence without credentials

```console
python -m experiments.stateful_study verify-freeze
python -m experiments.hf_stateful verify-freeze
python -m experiments.stateful_continue verify
python -m experiments.stateful_release verify
python -m experiments.verify_stateful_results
python -m unittest discover -s experiments/tests -v
python paper/verify.py
```

Registration checks require Git history/tags. Public release checks reconstruct fake states and packets, recompute answer support, counts, cost arithmetic and source-clustered estimates. Local `python -m experiments.stateful_release verify --raw` additionally checks retained private native archives; it is not required for a public checkout. None of these checks reconciles the provider's final billing ledger.

## Map the finished work to the governing rubric

The [live Swarm Alignment Hackathon guidelines and Judging and results](https://apartresearch.com/sprints/swarm-alignment-2026#guidelines), rather than the earlier collusion sprint, govern this submission. The common rubric covers impact potential/innovation, execution quality, and presentation/clarity.

| Requirement or dimension | Concrete evidence and boundary |
|---|---|
| Track 4 oversight, with Track 3 relevance | An executable stateful audit testbed compares evidence support, reader decisions and authentic-record preservation. It does not claim spontaneous collusion detection. |
| Impact and innovation | Related-work comparison distinguishes supported attribution from true guesses and causal blame. Stateful permission and paired restoration are narrowly scoped extensions; broad originality is not certified. |
| Execution quality | Two oracle implementations, 19,648 prescribed stateful projection checks, real Adaption/HF outputs, matched controls, baselines, frozen source hashes, source-level confidence intervals and retained failures. |
| Presentation and clarity | A worked permission-revocation example precedes definitions, measurements and implications. Independent sources and dependent views have separate denominators. The null primary result and smaller HF restoration non-replication are explicit. This applies 20-rules-of-learning editorially, not as scientific evidence. |
| Official report | Current guidelines-linked template; main text within eight pages; abstract within 150–250 words; named author/affiliation; references; required Limitations and Dual-Use / Ethical Considerations appendix; AI usage disclosure. PDF checks bind source, DOCX and rendered PDF. |
| Prior work and new work | October trusted-agent-sting is declared preexisting; its code/data/results were not imported. Development, qualification, main, influence and HF serving amendments are distinguished. |
| Responsible evidence release | Synthetic task data with genuine API decisions. Keys, native provider IDs, headers and raw reasoning remain excluded. No human-subject or live-security experiment. |

The remaining submission actions are human author review, ensuring judges can access the chosen code/data link, and submitting the PDF through the official form before the deadline. No submission or visibility change is implied by this integrity check. The organizer judges eligibility and scores; these checks do not guarantee either.
