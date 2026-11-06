# When Can a Swarm Be Audited?

A completed, bounded evidence-auditing study for the Apart Swarm Alignment Hackathon, November 6–8, 2026. Track 4 anchors the work; Track 3 concerns identity and evidence preservation.

New prospective extension: [LIVE_AUDIT_PROTOCOL.md](research/LIVE_AUDIT_PROTOCOL.md) specifies genuine model-chosen handoffs/actions, a continued-worker comparison, varied evidence loss, metadata-only restoration and a larger matched HF sample. [The direction decision](research/LIVE_DIRECTION_DECISION.md) maps its priorities to primary sources and selected winning-project lessons. Its own registration and outputs must be distinguished from the completed `results-v1` study below. The released PDF still reports that completed baseline until new data are collected and verified; new code alone is not an empirical result.

The separately frozen [weight-space experiment](research/WEIGHT_SPACE_PROTOCOL.md) has completed 144 proposals with offline replay. [WEIGHT_RESULTS.md](research/WEIGHT_RESULTS.md) reports model-dependent repair success and constructed checkpoint/message controls. Direct tiny-policy weight writing is distinct from LLM fine-tuning; no hosted base-model weights or training jobs were modified. The live-v2 audit phase stopped at three known-usage incomplete outputs after 204 requests; [the prospective continuation](research/LIVE_CONTINUATION.md) retains those failures and specifies the unstarted complement and bounded scheduling. Its registration must precede further live calls.

A finite interpreter executes fake stateful workflows; real model readers receive matched exported evidence. We ask whether selective evidence loss causes unsupported executor accusations and whether restoring authentic records helps. The target is the executor of an unauthorized applied mutation, not causal blame, intent or collusion. Collector originals remain intact.

The completed Adaption grid contains **3,840 calls over 192 source draws**. The primary selective-minus-random accusation contrast was **−1.04 percentage points (95% source-bootstrap interval −6.77 to +4.69)**: the hypothesized increase was not supported. A secondary, schema-informed restoration policy improved grounded correctness on two Adaption endpoints, but its priority-versus-random gain did not carry over clearly to the matched HF reader. A separate model-worker arm observed no unauthorized writes. These results concern a declared finite grammar, not deployment safety or spontaneous swarm behavior.

Start with [measured results](research/RESULTS.md), then [the protocol](research/STATEFUL_PROTOCOL.md) and [offline reproduction](research/STATEFUL_RUNBOOK.md). [stateful-results.json](research/stateful-results.json) supplies current counts, effects and cost estimates. [Earlier pilots](research/PILOT_RESULTS.md) remain separate; frozen documents retain their registration-time prospective wording.

[Collection integrity and rubric alignment](research/COLLECTION_INTEGRITY.md) maps the completed artifacts to the current Swarm guidelines and records how transport errors, durable journals, stopping rules and the no-retry continuation protect interpretation. The completed report/data release is tagged `results-v1`; earlier registration tags retain the pre-collection versions.

## What ran

| Arm | Sources | Calls | Scope |
|---|---:|---:|---|
| Adaption main-v2 |192|3,840|Two Gemma endpoints; ten dependent evidence views per source |
| HF v3 |24 shared main sources|240|Llama 3.3 70B via Novita; secondary matched model/serving comparison |
| One-hop influence |24 fresh contexts|216|24 origin calls plus 192 receiver decisions |

The core families are sequential handoff, deferred settlement after revocation, and approval join. Approval-join model outputs were held out from qualification and prompt selection. Core actions/branch facts are scripted: the core measures model reading. The separate influence arm measures model-chosen typed fake actions. An exact comparator and separately implemented constraint solver check the bounded contract. Coverage, structural answerability, unsupported NONE and invalidity accompany accusations.

Main collection stopped after an HTTP 502 at 3,028 calls. A separately registered continuation issued the 812 unstarted requests; the failed call remained INVALID and was not retried. V1 qualification failed encoding validity; v2 passed. HF v1 lost its Cerebras route before inference; HF v2 stopped after eight Qwen/Nscale calls with three reasoning-budget truncations. Separately registered HF v3 completed. [RESULTS.md](research/RESULTS.md) and [the continuation amendment](research/STATEFUL_CONTINUATION.md) preserve these boundaries. No training was launched.

## Reproduce offline

From the repository root, using Python 3.12+ and a checkout containing the registration tags:

```powershell
python -m unittest discover -s experiments/tests -v
python -m experiments.stateful_release verify
python -m experiments.verify_stateful_results
python -m experiments.verify_release
```

These replay published fake-data cases, scores, aggregates, baselines and paired intervals without credentials, provider calls or ignored native logs. [data/README.md](data/README.md) describes the release. Ten views are dependent within source; HF shares main sources and does not increase independent n.

For the committed official-template paper:

```powershell
python -m pip install -r paper/requirements.txt
python paper/verify.py
python -O paper/verify.py
python -m unittest discover -s paper/tests -v
```

[The PDF](paper/out/swarm_audit_scoping.pdf) and [editable DOCX](paper/out/swarm_audit_scoping.docx) retain legacy filenames. Verification checks committed artifacts without silently rebuilding them. Intentional revisions require a new DOCX build, Word PDF export, recorded manifest and page inspection. The runbook covers optional native-evidence checks; completed one-shot inference commands should not be rerun.

## Limits, costs and provenance

The primary hypothesis was not supported; its interval is not an equivalence or zero-risk proof. Restoration assumes authentic originals and a public schema-index query interface aligned with the constructed deletion policy. The Llama comparison did not establish the same grounded-correctness gain. Narrow influence stimuli produced no write attempts. Two oracle implementations share a specification and do not constitute independent human validation.

Main token-rate costing estimates **0.350667288 Adaption credits**, versus **0.253835568** in summed provider cost fields. Influence estimates **0.0057058035 credits**. Completed HF v3 estimates **$0.031954015**; earlier HF smoke/partial-v2 estimates total about **$0.08496517**. These are not reconciled invoices. The earlier observed $2 HF allowance was sufficient for these measured amounts; no top-up was needed. No top-up, plan change or training job was created. Final account debit and older unknown development liabilities remain unresolved.

Razvan Sacara's [trusted-agent-sting](https://github.com/razzyrazzy11/trusted-agent-sting) is preexisting October 2026 work. Its code, data and results were not imported; reproducibility practices informed this project. The GitHub-created initial commit is `bbed9cd`; the first task commit `69172e8` contains secret/raw-output exclusions only. Citation metadata/security policy followed in `818653d`. No history was rewritten.

[SOURCE_AUDIT.md](research/SOURCE_AUDIT.md), [REVIEW.md](research/REVIEW.md), [DEVIATIONS.md](research/DEVIATIONS.md) and [TRANSCRIPT_REVIEW.md](research/TRANSCRIPT_REVIEW.md) preserve sources, access limits and iterations. Qin, Yun, Syscon, BLADE and BRIDGE already establish the relevant logging, binding, receipt, responsibility and repair precedents. No general collusion-detector or first-logger claim is made. The 20-rules-of-learning skill guides explanation order and distinctions; it does not establish originality. Native IDs, headers, keys and reasoning traces stay outside the public release. See [SECURITY.md](SECURITY.md). Human author approval and Apart submission remain separate from repository checks.
