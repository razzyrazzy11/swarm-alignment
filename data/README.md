# Current live and weight release

| File | Records | Meaning |
|---|---:|---|
| `live_actors.jsonl` |720|Actual origin/receiver final outputs and exact public task/history inputs |
| `live_trajectories.json` |528|Replayed main and influence fake states, worlds and decisions |
| `live_cases.jsonl` |9,360|Actual reader outputs with evidence views, support and scores |
| `live_contexts.json` |192 main + 6 qualification contexts|Previously committed random context design, released after collection |
| `weight_cases.jsonl` |144|Actual numeric artifacts, admission, finite behaviors and conditional controls |

`research/live-results.json` and `research/weight-results.json` bind hashes and recomputed aggregates. Run `python -m experiments.live_analysis verify` and `python -m experiments.weight_study replay` offline. The live continuation is explicitly declared in the report. Known-usage truncations and transport failures remain invalid outcomes; request count does not imply successful inference. Qualification outputs remain excluded. Source contexts, not dependent branches/views, are the live unit; representation variants, not truth-table rows/random draws, are the weight unit. No hosted base weights or trained adapters were modified. The earlier release below remains separate.


## Earlier scripted release (results-v1)

These files publish mechanically executed fake workflows and actual final model answers. They are not incident data or generated numbers presented as model observations. Native provider request/response IDs, headers, keys and reasoning traces remain in ignored local storage and are not needed for public replay.

| File | Records | Meaning |
|---|---:|---|
| `stateful_main_episodes.json` |192|Source seed, family/cohort, public context, hidden-world configuration, replayed host state and true executor/NONE |
| `stateful_main_cases.jsonl` |3,840|Ten dependent task views × two readers for each main source |
| `stateful_hf_cases.jsonl` |240|Llama/Novita answers on ten views of 24 selected **shared main sources** |
| `stateful_influence_cases.jsonl` |216|24 origin reads plus 192 receiver decisions under scripted exposure/warning interventions |
| `development_episodes.json` |20|Earlier same-grammar development sources; excluded from main inference |
| `development_reader_cases.jsonl` |120|Earlier fixed development reader batch; never pooled with main data |

The aggregate [stateful-results.json](../research/stateful-results.json) records artifact hashes, source/config hashes, by-view model counts, denominators, cost estimates and paired effect intervals. The top-level `main`, `hf` and `influence` objects alias the corresponding `arms` objects. Earlier qualification/provider failures remain documented separately; their omitted native reasoning is not reconstructed from these public files.

## Read a case

Core/HF rows contain a `task` with episode/task IDs, family, clean/violation cohort, naming condition, loss mechanism, restoration policy, visible fake packet, packet hash, compatible labels and added record IDs. The complete hidden source configuration is released separately after evaluation for reproducibility; it was not supplied to readers. All readers and the exact comparator use the same packet within a condition.

`attempted` and `returned` distinguish planned, journaled and terminal-record states. A returned record can contain a failed transport or INVALID answer; it does not imply successful inference. `response` contains only normalized status, final text and allowed usage fields. `scored` preserves the declared supported-finding/abstention logic and raw strict-schema validity. Fences accepted under the frozen v2 parser remain identifiable. Token counts can include billed reasoning tokens even though native reasoning text is excluded.

Influence rows identify source, origin/receiver phase, exposure arm and warning. Their fake packet and replayed score distinguish reads, refusals, attempted writes and actual state changes. Scripted message substitution is the exposure intervention; it is not evidence that agents spontaneously created those messages. These 24 contexts are separate from the main source set.

Costs retain their units and interpretation: per-record token-rate estimates are not invoices, and optional `provider_reported_cost` fields are not final account balances. A zero reported-cost total when no field was supplied means no amount was reported, not that service was free. The main gateway failure remains an INVALID terminal record with conservative estimated liability. There are no journal-only or unattempted calls in the three completed current arms.

## Verify offline

From the repository root, using Python 3.12+ and the registration tags:

```powershell
python -m experiments.stateful_release verify
python -m experiments.verify_stateful_results
python -m experiments.verify_release
```

The first checks file hashes, permitted fields and case replay. The second recomputes aggregates, aliases, frozen main baselines/paired bootstrap effects, HF secondary effects and influence costs/contrasts using temporary fake records. The third checks the separate development release. No credentials, provider calls or ignored native logs are needed. This validates consistency with the finite specification, not arbitrary-world completeness or final billing.

UTF-8 JSON/JSONL uses LF newlines so committed hashes match across platforms. Views are dependent within source; repeated labels or aliases do not create additional independent observations. Do not pool the 240 HF views with main episodes as fresh independent trials. See [RESULTS.md](../research/RESULTS.md) for findings, operational deviations and limitations.
