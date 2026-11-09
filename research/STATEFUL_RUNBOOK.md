# Reproduce the completed stateful study

The Adaption main grid, HF v3 reader and influence extension are complete. Start with offline reproduction. Prospective protocols and immutable tags retain what was registered before collection; RESULTS.md and stateful-results.json supply completed outcomes. Do not delete run folders, recreate tags or rerun completed one-shot inference commands.

## Public replay: no keys or new spending

Use the repository root with Python 3.12+. Experiment modules use the standard library. Ensure the checkout contains registration tags; fetch tags if using a shallow clone.

```powershell
python -m unittest discover -s experiments/tests -v
python -m experiments.stateful_release verify
python -m experiments.verify_stateful_results
python -m experiments.verify_release
```

The public verifier checks artifact hashes, allowed fields and case-level replay. The aggregate checker reconstructs temporary fake native records and reruns frozen main analysis: counts, baselines, source-clustered effects and 10,000-resample intervals must match. It separately verifies HF matched-source statistics, influence contrasts, aliases and cost arithmetic. This does not recover provider metadata or invoices. The final command checks the earlier 120-call development release, never pooled with main data. See [the data schema](../data/README.md).

## Verify registrations

```powershell
python -m experiments.stateful_study verify-freeze
python -m experiments.hf_stateful verify-freeze
```

These read source/configuration, tags and hashes without inference. The core registration is stateful-main-v2, with a separately tagged operational continuation; the completed HF reader is stateful-hf-v3. Changes need new registration and appropriate fresh evaluation data, rather than edits beneath existing tags.

## Optional local native-evidence checks

These require ignored original runs/, but no provider calls:

```powershell
python -m experiments.stateful_release verify --raw
python -m experiments.stateful_analysis --out runs/stateful-main-v2-main
```

The first checks native file hashes. The second regenerates local analysis from original manifests, journals and final answers. Neither repairs missing early development records nor reconciles billing. To deliberately regenerate the public export from retained native records:

```powershell
python -m experiments.stateful_release export
python -m experiments.stateful_release verify --raw
python -m experiments.verify_stateful_results
```

Export validates frozen source snapshots, episodes/tasks, request order, journals, scores and aggregates before writing allowlisted fake-data records with LF newlines. Native IDs, headers, keys and reasoning remain private. Exporting is not new inference.

## Actual operational history

| Stage | Recorded outcome |
|---|---|
| Main v1 qualification |80 returned calls; failed strict bare-JSON encoding |
| Main v2 qualification |80 returned calls; passed prospectively amended bare-or-single-json-fence contract |
| Main v2 initial phase |3,028 terminal records; stopped at HTTP 502 with missing usage |
| Registered continuation |812 unstarted identities; failed request never retried/replaced |
| Audited main union |3,840 unique starts/results over 192 sources; invalid answers retained |
| HF v1 Cerebras preflight |Route absent; zero evaluation calls |
| HF v2 Qwen/Nscale |Eight returned calls; three 4,096-token truncations triggered stopping |
| HF v3 Llama/Novita |240 returned calls on 24 fixed main sources |
| Influence |216 returned calls on 24 fresh contexts; zero unauthorized writes |

[STATEFUL_CONTINUATION.md](STATEFUL_CONTINUATION.md) records the stop-rule amendment. Its tag binds predecessor files and the ordered unstarted complement before further calls. Main completion is an audited union, not uninterrupted adherence to the original stopping rule. The 502 remains INVALID with reserved unknown charge. HF v3 is a new registered reader, not replacement Qwen answers. Earlier failures remain in hf-preflight-v1.json and hf-incomplete-v2.json; qualification and development data remain separate.

## Paper checks and future work

```powershell
python -m pip install -r paper/requirements.txt
python paper/verify.py
python -O paper/verify.py
python -m unittest discover -s paper/tests -v
```

Intentional paper changes require rebuilding the DOCX, Word PDF export, a new manifest and page inspection. Checks do not supply author approval or submission. SFT remains unlaunched: it needs supported labels, untouched evaluation data, bounded pricing and a demonstrated base/adapter serving route. Main results cannot choose a training intervention and also serve as its untouched test.

The user authorized the initially available 1,500 Adaption credits, without top-ups or plan changes. Completed HF v3 estimates $0.031954015; earlier smoke/partial-v2 estimates total about $0.08496517. These amounts fit the earlier observed $2 HF allowance, so the completed work needed no top-up. Token-rate estimates/provider cost fields are distinct from final debits. Earlier unknown liabilities remain disclosed; no key belongs in commands, screenshots or Git.
