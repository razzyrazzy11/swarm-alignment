# Reproduce the released experiments

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
