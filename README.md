# When Can a Swarm Be Audited?

An empirical, bounded swarm-audit testbed for the Apart Swarm Alignment Hackathon, November 6–8, 2026. **Track 4: Multi-Agent Oversight and Control** anchors the work. The main new question is: **Does a swarm auditor lack necessary evidence, or fail to use evidence that is already sufficient?** Track 3 identity and provenance support that question. The checkpoint below identifies completed earlier results and the pending matched comparison.

Start with the [official-template PDF](paper/out/swarm_audit_scoping.pdf), [measured results](research/RESULTS.md) and [offline reproduction](research/REPRODUCING_RESULTS.md). This is a research report and executed experiments, with nulls, failures and scope limits retained.

The subsequent [direction and rubric assessment](research/NEXT_STUDY_DECISION.md) ranks new structural transfer and evidence-use controls above more model endpoints or training. Its [post-release diagnostic](research/restoration-diagnostic-posthoc.json) decomposes the existing restoration gain descriptively; it is not a new confirmatory endpoint and does not change the `results-v2` paper or frozen experiments.

The new [factorial Track 4 protocol](research/FACTORIAL_PROTOCOL.md) is prospectively frozen as `factorial-audit-v1`. The earlier account-cushion checkpoint paused collection after 576 worker requests and 9,706 of 11,640 reader requests, including the separately scripted calibration bank. At that checkpoint all started reader identities had terminal records and 1,934 HF requests were unstarted. An operator credit cushion stopped and drained the queue without changing endpoints, prompts or the sample. One earlier delegate-stage gateway response remains retained without retry and could not execute an action. The [metadata checkpoint](research/factorial-collection-status.json) preserves counts and journal-prefix hashes; no interim scientific effects have been reviewed. The PDF continues to report completed prior studies until full collection and public replay finish. [Implementation review](research/FACTORIAL_REVIEW.md) and [primary sources](research/FACTORIAL_SOURCES.md) record validation and scope.

The operator confirmed funding, and the tagged [exact-unstarted continuation](research/factorial-account-resume.json) completed four more requests before one HTTP 429 stopped collection safely. There are now 9,711 reader terminal records and 1,929 unstarted requests; the failed request remains INVALID and will never be retried. A prospective [rate-controlled operational continuation](research/FACTORIAL_RATE_CONTINUATION.md) changes scheduling only and must be tagged before further requests. Original endpoints, request bodies, sample, analysis and phase ceilings remain unchanged. These checkpoints are operational history, not completed factorial findings.

## What actually ran

| Study | Completed calls | Independent unit and scope |
|---|---:|---|
| Earlier scripted audit | 3,840 Adaption + 240 HF + 216 influence | 192 scripted sources; HF shares 24; influence has 24 separate contexts |
| Live handoffs/actions and audits | 720 actor + 9,360 reader | 192 new source groups; paired continued/delegated branches; seven dependent views; three endpoints/two families; 48-source influence subset |
| Tiny weight-policy programming | 144 numerical proposals | 24 representations of three defects; repair/synthesis; three endpoints/two families; 32 dependent Boolean contexts per artifact |

The live workflow includes actual model-chosen handoffs and write/read/refuse decisions executed against new fake dictionaries. Complete evidence, random loss and selective loss are paired. Metadata-selected and random add-back each retrieve at most two authentic records; they do not match bytes, tokens or information. An independent reference checker validates finite evidence support. Solo/delegated changes identity and context boundary together; it is not an agent-count-only experiment.

The new registered primary restoration contrast is **+5.73 pp (95% source-bootstrap +1.04 to +10.42; n=192)**. Full reader, action, influence, invalidity and baseline results are in [LIVE_RESULTS.md](research/LIVE_RESULTS.md). The older accusation primary remained null, and its smaller HF restoration comparison did not clearly replicate the Adaption gain. All original results remain visible.

The weight writers supplied numeric tensors for two tiny composed controllers, not edits to hosted LLMs. Gemma 31B returned exact in-budget repairs for 16/24 variants; the other writers returned none. Constructed harmful changes can preserve an upstream handoff; all 24 harmless reparameterizations alter the checkpoint hash. This motivates **behavioral contract checks with checkpoint provenance**, not weights-only intent inference. See [WEIGHT_RESULTS.md](research/WEIGHT_RESULTS.md) and the [conditional training follow-up](research/WEIGHT_FOLLOWUP_DECISION.md). No SFT, joint policy training, GPU rental or top-up was performed.

## Reproduce and inspect

```console
python -m experiments.live_analysis verify
python -m experiments.weight_study replay
python -m experiments.stateful_release verify
python -m experiments.verify_stateful_results
python -m unittest discover -s experiments/tests -v
python -m pip install -r paper/requirements.txt
python paper/verify.py
python -O paper/verify.py
python -m unittest discover -s paper/tests -v
```

Use Python 3.12+ and registration tags. These are offline checks, not collection commands; no credentials or native archives are required. [data/README.md](data/README.md) describes sanitized actual answers and fake-data artifacts. [REPRODUCING_RESULTS.md](research/REPRODUCING_RESULTS.md) lists freeze verification and explains units. PDF/DOCX retain legacy filenames. Paper verification checks committed content, hashes, template fidelity and page limits; intentional revisions also require Word export and visual inspection.

## Protocols, costs and limits

[LIVE_AUDIT_PROTOCOL.md](research/LIVE_AUDIT_PROTOCOL.md) and [WEIGHT_SPACE_PROTOCOL.md](research/WEIGHT_SPACE_PROTOCOL.md) were tagged before their fresh calls. Live v1 qualification failed; a prospectively clarified v2 passed fresh qualification. The audit phase stopped at 204 requests after its third known-usage truncation. A [separately registered continuation](research/LIVE_CONTINUATION.md) retained all started outcomes and collected only the unstarted complement with bounded sliding concurrency. Gateway failures/truncations remain INVALID and are never retried. Earlier scripted/HF serving amendments remain distinct. This is not an uninterrupted unamended confirmatory run.

Live actor/audit estimates: 1.0315761365 Adaption credits and $0.687000460 HF. Weight main estimates: 0.0170366750 credits and $0.010478120 HF. Qualifications, older studies and development are separate. Estimates are not reconciled invoices or hard account caps. No inference credit balance implies reserved training hardware.

Only two workers, known synthetic workflows, trusted originals and tiny finite numerical policies were tested. Dependent views/truth rows do not increase independent n. No spontaneous collusion, intent inference, collector compromise resistance, scalable neural verification or deployment safety is claimed. Current [Apart guidelines and Judging and results](https://apartresearch.com/sprints/swarm-alignment-2026#guidelines) govern; selected winning-project lessons inform validation and clarity rather than guarantee a score. [The source audit](research/SOURCE_AUDIT.md) records reading depth and gaps; originality is not universally certified.

## Prior work and release history

Razvan Sacara's [trusted-agent-sting](https://github.com/razzyrazzy11/trusted-agent-sting) is preexisting October 2026 work. Its code/data/results were not imported; reproducibility practices informed this project. The GitHub-created initial commit is `bbed9cd`; first task commit `69172e8` contains secret/raw-output exclusions only. Citation/security files followed in `818653d`. No history was rewritten.

`results-v1` preserves the original report/data; `results-v2` integrates the completed extensions. [REVIEW.md](research/REVIEW.md), [LIVE_REVIEW.md](research/LIVE_REVIEW.md), [DEVIATIONS.md](research/DEVIATIONS.md), [SOURCE_AUDIT.md](research/SOURCE_AUDIT.md) and [TRANSCRIPT_REVIEW.md](research/TRANSCRIPT_REVIEW.md) preserve iterations. Frozen source memos retain registration-time wording; current findings live in results documents. The 20-rules-of-learning skill guides concrete examples, definitions and distinctions, not scientific evidence.

Keys, native IDs, headers, raw reasoning and raw runs remain excluded; see [SECURITY.md](SECURITY.md). The repository remains private and its PR remains a draft. Human author approval, judge access and official submission remain separate actions.
