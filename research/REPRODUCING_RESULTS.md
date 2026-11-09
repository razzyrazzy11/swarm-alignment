# Reproduce the released experiments

<!-- factorial-results-v3:start -->
## Amended offline replay

Run python -m experiments.factorial_reporting verify, python -m unittest discover -s experiments/tests -v and python paper/verify.py. Use original, reporting and Ollama registration tags. The sibling reconstructs actual outputs and missing states, complete primary bootstrap, incomplete Novita logical bounds and extension contrasts. It never fills unknown responses or launches inference. The original primary is complete on 192 source groups; the original reader plan is NOT complete: 9,742/11,640 terminal records and 1,898 UNSTARTED. The actors have 576 terminals. Registered Ollama collection has 4,728/4,728 terminal readings, extension_plan_complete=True. No extension substitutes for a missing Novita call.

Earlier release narrative below is preserved historical context. Its collection-time wording and counts describe those earlier studies; the current factorial status is the explicit actual/planned status described above.
<!-- factorial-results-v3:end -->

## Historical funding checkpoint: 7 November, 04:18 UTC

At that checkpoint, the factorial study was waiting for HF funding; [the recorded status](factorial-collection-status.json) described a drained operator STOP, not completed scientific results. Factorial contexts/cases and an aggregate had not been released then. The amended sanitized package is now included in the repository; use the sibling-report command above for current results. The commands below reproduce the separately completed prior studies. Do not launch paid collection to reproduce existing results.

For any new collection, check actual remaining account funds after earlier runs and other compute. A client phase ceiling does not reserve account credits. [HF's official pricing](https://huggingface.co/docs/inference-providers/en/pricing) lists $2 in monthly PRO compute credits and purchased credits for extra routed usage. No automatic purchase or plan change is authorized by the collection code. An operator continuation requires sufficient funds, drained journals and the exact unstarted identities; it must never retry a started call to conceal a billing failure.

Use Python 3.12+ from the repository root and a checkout containing all registration tags (`git fetch --tags` when needed). These commands are offline checks: they do not load credentials, submit inference requests or launch training. Published JSON/JSONL contains final answers and bounded fake-data artifacts, not native reasoning or account identifiers.

```console
python -m unittest discover -s experiments/tests -v
python -m experiments.stateful_study verify-freeze
python -m experiments.hf_stateful verify-freeze
python -m experiments.stateful_continue verify
python -m experiments.stateful_release verify
python -m experiments.verify_stateful_results
python -m experiments.verify_release
python -m experiments.live_study verify
python -m experiments.live_continue verify
python -m experiments.weight_study verify
python -m experiments.weight_study replay
```

For `research/live-results.json` and its four public artifacts, also run:

```console
python -m experiments.live_analysis verify
```

The live verifier reconstructs the actual origin/receiver choices, continued-history versus fresh-worker boundary, fake post-state, evidence views and answer support. It checks the complete main/influence request grid, final responses, costs and whole-source effects. The weight verifier reconstructs numerical admission, edit budgets, all 32 Boolean contexts, model artifacts, symbolic/random/benign controls and representation-level estimates. Neither requires the ignored native archives.

Registration checks bind source hashes to the tags that preceded their corresponding fresh calls. The live continuation is a separate operational registration; it retains the first 204 audit outcomes and uses the exact 7,860 previously unstarted identities. Known-usage incomplete outputs remain INVALID. The source, protocol and analysis of the scientific grid remain at `live-audit-v2`. A failed request is never silently retried.

## Verify the paper separately

```console
python -m pip install -r paper/requirements.txt
python paper/verify.py
python -O paper/verify.py
python -m unittest discover -s paper/tests -v
```

These checks inspect committed artifacts without rebuilding them. They bind paper tables and denominators to the released aggregates, check the official template's preserve-only parts and section geometry, and check the recorded PDF hash/page limits. A source edit requires rebuilding DOCX, exporting through Word, recording the PDF and visually inspecting every final page. CI cannot substitute for that visual inspection.

## Keep the units and histories separate

The earlier scripted study has 192 source draws; its HF subset shares 24 of them. The live study has 192 new source groups, paired receiver branches and dependent evidence views. Its influence subset shares 48 main source groups. The tiny-weight experiment has 24 representation variants of three defect templates, each with 32 dependent truth-table contexts. Calls, views, random control draws and truth-table rows are not fresh independent tasks.

Adaption credits and HF dollar estimates retain their separate units. Token-rate arithmetic and known usage do not reconcile final account debits or authenticate a provider independently. Public replay establishes consistency with the finite specification, not arbitrary-world completeness or deployment safety.

Do not rerun `run`, `qualification`, `export` or any one-shot collection command to reproduce a public paper. Those commands can spend credits or alter a local release. The original `results-v1` tag preserves the earlier paper and data; registration tags preserve the prior protocols. [WEIGHT_FOLLOWUP_DECISION.md](WEIGHT_FOLLOWUP_DECISION.md) scopes future adaptation without claiming any training was conducted.
