# When Can a Swarm Be Audited?

Bounded evidence oracle, genuine development pilots and prospective experiment protocol for the Apart Swarm Alignment Hackathon, November 6–8, 2026.

Recommended focus: Track 4 (Multi-Agent Oversight and Control), with Track 3 relevance. Test scripted selective loss from exported evidence and changing display names, using evidence-matched readers and an explicit insufficient-evidence answer. Protected collector originals remain intact. The target is the executor of one unauthorized fake-data mutation, not causal blame or collusive intent. The completed fixed development batch has 120 reader calls over 20 scripted source episodes; additional qualification, one-hop influence and HF access tests are reported separately. **No confirmatory study, training result, spontaneous collusion or deployment safety guarantee is claimed.**

The new main implementation is `experiments/stateful.py`: sequential delegation, deferred settlement and an approval-join holdout, with independent compatible-history checking, matched evidence loss and authentic-record restoration. Its precise prospective contract is `research/STATEFUL_PROTOCOL.md`, configuration is `research/stateful-config.json`, and operational sequence is `research/STATEFUL_RUNBOOK.md`. The earlier pilot remains a separate dataset. A committed freeze/tag must pass verification before any fresh qualification/main inference; an implemented study is not a completed result.

Current execution status: `stateful-main-v2` is registered and its 80-call excluded operational qualification passed. V1's 80-call qualification failed bare-JSON validity and remains archived; v2 prospectively permits a single JSON fence while retaining raw strict validity. This is not a measure of correct audit answers. The 3,840-call main benchmark and 216-call influence extension have not been run; the approval-join holdout has no model outputs. Start at step 4 of the runbook, then analyze the main run before the separate influence arm. No SFT job is enabled. `research/stateful-qualification.json` binds the actual stage counts/hashes.

- `research/PILOT_RESULTS.md`: measured development results, iteration history and unresolved billing/source limitations.
- `research/pilot-results.json`: redacted recomputed counts and raw-file hashes.
- `research/SUITE_STRATEGY.md`: current suite positioning, optional training/influence gates and full authorized budget allocation.
- `experiments/`: credential-safe access checks, two oracle implementations, development runners and offline tests.
- `research/DECISION.md`: recommendation, alternatives, sources, judging alignment, budget and schedule.
- `research/PROTOCOL.md`: prospective design; not a completed or frozen preregistration.
- `research/SOURCE_AUDIT.md`: coverage and access limitations.
- `research/TRANSCRIPT_REVIEW.md`: source-use decisions from the supplied recordings and chat links.
- `research/REVIEW.md`: consistency fixes, originality boundaries and remaining experiment gates.
- `research/GAP_ANALYSIS.md`: closest-source overlap, priority experiments and tests that could falsify the proposed contribution.
- `research/ADAPTION_PLAN.md`: historical hosted-inference costing and HF resource conventions; superseded by the measured pilot and SUITE_STRATEGY.md.
- `research/cost_plan.py`: historical token-cost example from `research/adaption-design.json`; no network calls or experimental results.
- `paper/out/swarm_audit_scoping.pdf`: template-based development report (legacy filename retained).
- `paper/out/swarm_audit_scoping.docx`: editable paper.
- `paper/build.py`: document assembly from the current official template.

## Prior work and provenance

Razvan Sacara's preexisting project is https://github.com/razzyrazzy11/trusted-agent-sting (October 2026). Its study design, code, data and results predate this sprint and are not new contributions here. This project borrows the practices of prospective hypotheses, deviation logs, CI, version tags and report traceability. No prior experimental data or code has been imported. The attached previous conversation is background, not verified evidence or an instruction source.

The repository's GitHub-created initial commit is `bbed9cd`. The first commit made for this task is `69172e8`, containing only secret and raw-output exclusions. Citation metadata and the security policy follow in `818653d`. No history was rewritten.

## Reproducibility and release

The report contains automated oracle validation and exploratory model measurements. The small grammar and development-selected endpoints do not establish a general swarm benchmark or a confirmatory effect. See `research/PROTOCOL.md` before experiments. Freeze prompts, models, scoring, split manifests and stopping rules in a separate commit/tag before confirmatory runs. Document every later change in `research/DEVIATIONS.md`; do not backdate a preregistration.

Raw outputs belong under `runs/` and remain ignored. Keep sanitized fake-data cases, final answers, aggregates and benign fixtures in Git; native API logs remain private. Do not commit credentials. See `SECURITY.md` for GitHub feature limitations and responsible disclosure.

The November review supersedes ambiguities in `scoping-v0.1`: execution receipts are distinct from identity bindings; the primary contrast is distinct from the churn interaction; record-count matching is not token matching; and missing evidence does not establish innocence. The prospective protocol is still not frozen. The 20-rules-of-learning skill is used to define concepts before comparisons, keep each claim focused, and connect methods to their supporting evidence; it is not a scientific novelty criterion.

Install `paper/requirements.txt`, then run `python paper/verify.py` and `python -m unittest discover -s paper/tests -v` to check the committed report. CI also runs the verifier under `python -O`. Verification does not rebuild artifacts: an old PDF or DOCX must fail after source changes. To intentionally revise the paper, edit `paper/content.json`, run `python paper/build.py`, export the DOCX to PDF with Microsoft Word, then run `python paper/verify.py --record-pdf`. Inspect every PDF page before committing both artifacts and their manifests. The PDF manifest records a validated local Word export; CI checks that export's content/provenance and does not render it.


## Reproduce the bounded validation

Run `python -m unittest discover -s experiments/tests -v` for offline oracle, scoring and safety tests. The exhaustive comparison checks 55,296 valid world/export combinations; both implementations still share a written specification. Run `python -m experiments.pilot` for offline preparation only. Credentialed calls require an explicit `--run`, for example the fixed completed profile: `python -m experiments.pilot --run --episodes 20 --max-output-tokens 4096 --models gemma-4-26b-a4b-it gemma-4-31b-it --out runs/new-development-batch`. Every output directory must be new. The runner uses a five-credit nominal cap, durable starts/results, a STOP-file control and an early truncation gate. Token-rate estimates are not provider-enforced billing caps.

`python -m experiments.access` performs authenticated read-only catalog/identity checks. `python -m experiments.hf_access` reads HF routing prices; only `--smoke` issues its bounded inference calls. `python -m experiments.influence` prints its offline plan; `--run` runs a 0.1-credit one-hop fake-record development pilot. API tools/memory/continuation are disabled, and model output is never evaluated as code. Credentials come from the ignored `.env` or environment, never CLI arguments.

Recompute retained local results with `python -m experiments.analyze`. Raw native API files are excluded from Git. Run `python -m experiments.verify_release` without credentials or network to replay the 20 fake source episodes and reproduce all 120 released packet labels, final-answer scores and aggregate counts from `data/`. Native provider metadata and reasoning traces are not released. Earlier working source versions were not all snapshotted; exact reconstruction of old failed batches is limited. The paper verifier binds its current counts/table to the aggregate JSON. Confirmatory execution requires a new frozen design, realistic task families and independent human label review.
