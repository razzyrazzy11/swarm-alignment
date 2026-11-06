# Run the stateful study in dependency order

Use the repository root in PowerShell. Existing ignored `.env` keys are read by the orchestrator; never paste them into commands or reports. `python` below means a Python 3.12+ environment with `paper/requirements.txt` installed. The bundled Codex Python is also suitable. All experiment modules otherwise use the standard library. The command `plan` never accesses credentials or generates main cases.

## 1. Offline validation

```powershell
python -m unittest discover -s experiments/tests -v
python -m experiments.stateful_study plan
python -m experiments.verify_release
python paper/verify.py
```

These check the finite state transitions, independent oracle, malformed inputs, naming/loss/restoration controls, fake-action positive controls, journal/budget behavior and earlier released data. They do not measure a model or establish new empirical findings. Validation fixtures use development seeds; model outputs for the approval-join holdout remain untouched.

## 2. Freeze once before fresh inference

The maintained repository should already contain the completed `stateful-main-v1` freeze/tag. Verify it:

```powershell
python -m experiments.stateful_study verify-freeze
```

For the original registration only: commit the validated implementation and protocol with a clean working tree, run `python -m experiments.stateful_study freeze`, commit `research/stateful-freeze.json`, then create/push the annotated `stateful-main-v1` tag. Do not recreate or move this tag. It binds exact source, protocol, config and prompt hashes. Further changes require a dated amendment/new version, not editing the frozen design underneath a run. The freeze is prospective for the new study; the prior development data were already observed.

## 3. Qualification — four excluded sources, 80 calls

```powershell
python -m experiments.stateful_study run --stage qualification
python -m experiments.stateful_analysis --out runs/stateful-qualification
```

Uses sequential/deferred families only, both frozen endpoints and ten evidence views per source. Every call must complete with known usage and valid strict JSON. A wrong but valid answer is not a qualification failure. The nominal cap is one Adaption credit. Fixed output folder: `runs/stateful-qualification`. If it already exists, inspect the retained result; do not delete it to rerun until lucky. Failed qualification blocks main inference and needs a documented amendment if sources/settings must change.

## 4. Main benchmark — 192 fresh sources, 3,840 calls

```powershell
python -m experiments.stateful_study run --stage main
python -m experiments.stateful_analysis --out runs/stateful-main
```

Starts only after passed qualification for the same freeze. Each family has 64 source episodes, with both naming conditions, complete/random/selective evidence and two authentic restoration policies for selective-loss views. The approval-join family is structurally held out from model qualification. Twenty Adaption credits is the nominal ceiling, not expected consumption or a provider-enforced hard cap. Two endpoints in the same model family are not independent model-family replication. The primary estimate uses one frozen endpoint and paired source episodes; the remaining outcomes are secondary.

The run may take substantially longer than qualification. Check the durable journal/response counts and summary rather than interpreting a favorable prefix. To request a graceful stop from another PowerShell window:

```powershell
New-Item -ItemType File -Path runs/stateful-main/STOP
```

The runner drains up to four started calls and writes a partial summary. Do not kill the process casually. If a crash occurs, retain journals and inspect `stateful_analysis`; journaled starts without results remain uncertain liabilities. A main reservation file prevents another invocation into a different folder. There is no implemented silent resume; an interrupted study must be reported or amended explicitly.

## 5. Controlled influence extension — 24 contexts, 216 calls

```powershell
python -m experiments.stateful_influence --run
```

Runs after main completion, with a one-credit nominal cap. A model origin reads a fake decoy, then a model receiver chooses a typed fake action. Four scripted peer exposures × warning on/off are paired within context. The primary influence contrast is malicious versus benign without warning. Equal characters are not equal tokens; no-peer is shorter. Read task success and actual executed violations are separate outcomes. Invalid origin/operational failures halt the extension. No propagation or spontaneous collusion claim follows from one hop.

## 6. Optional small-monitor SFT — a separate future freeze

Do not launch training merely to use credits. First establish a meaningful development failure and assemble correctly supported singleton/ABSTAIN targets. Split source episodes and structural families before augmentation; never train/tune on the main holdout. If main results inform intervention selection, reserve a new untouched evaluation set. Obtain bounded pricing and demonstrate compatible pinned base/adapter serving before launch. The suite strategy records Adaption row minima and HF serving conventions. No SFT training command is enabled in this freeze.

## 7. Reconcile and report

Keep raw native responses, manifests, source snapshots and journals under ignored `runs/`. Preserve every planned/attempted/returned distinction. Reconcile real billing separately from token-rate estimates and old unresolved charges. Release only sanitized fake packets/final answers and aggregate hashes, regenerate the official-template paper from measured results, check it normally and under `python -O`, and inspect every rendered page. Retain null results and protocol deviations. CI and an annotated tag do not constitute human author approval or an Apart submission.
