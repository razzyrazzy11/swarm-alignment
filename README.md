# When Can a Swarm Be Audited?

Primary-source scoping study and prospective experiment protocol for the Apart Swarm Alignment Hackathon, November 6–8, 2026.

Recommended focus: Track 4 (Multi-Agent Oversight and Control), with Track 3 relevance. Test scripted selective loss from exported evidence and changing display names, using evidence-matched readers and an explicit insufficient-evidence answer. Protected collector originals remain intact. The target is the executor of one unauthorized fake-data mutation, not causal blame or collusive intent. This repository currently contains research planning and a report; **no LLM experiment has been executed and no detector performance is claimed**.

- `research/DECISION.md`: recommendation, alternatives, sources, judging alignment, budget and schedule.
- `research/PROTOCOL.md`: prospective design; not a completed or frozen preregistration.
- `research/SOURCE_AUDIT.md`: coverage and access limitations.
- `research/TRANSCRIPT_REVIEW.md`: source-use decisions from the supplied recordings and chat links.
- `research/REVIEW.md`: consistency fixes, originality boundaries and remaining experiment gates.
- `research/GAP_ANALYSIS.md`: closest-source overlap, priority experiments and tests that could falsify the proposed contribution.
- `research/ADAPTION_PLAN.md`: hosted-inference data plan, verified public rates, execution gates and a costed 600-episode candidate design.
- `research/cost_plan.py`: reproducible prospective costing from `research/adaption-design.json`; no network calls or experimental results.
- `paper/out/swarm_audit_scoping.pdf`: template-based scoping paper.
- `paper/out/swarm_audit_scoping.docx`: editable paper.
- `paper/build.py`: document assembly from the current official template.

## Prior work and provenance

Razvan Sacara's preexisting project is https://github.com/razzyrazzy11/trusted-agent-sting (October 2026). Its study design, code, data and results predate this sprint and are not new contributions here. This project borrows the practices of prospective hypotheses, deviation logs, CI, version tags and report traceability. No prior experimental data or code has been imported. The attached previous conversation is background, not verified evidence or an instruction source.

The repository's GitHub-created initial commit is `bbed9cd`. The first commit made for this task is `69172e8`, containing only secret and raw-output exclusions. Citation metadata and the security policy follow in `818653d`. No history was rewritten.

## Reproducibility and release

The report is a scoping study with an elementary analytical observation, not an empirical swarm benchmark. See `research/PROTOCOL.md` before experiments. Freeze prompts, models, scoring, split manifests and stopping rules in a separate commit/tag before confirmatory runs. Document every later change in `research/DEVIATIONS.md`; do not backdate a preregistration.

Raw outputs belong under `runs/` and remain ignored. Keep only redacted aggregates and benign fixtures in Git. Do not commit credentials. See `SECURITY.md` for GitHub feature limitations and responsible disclosure.

The November review supersedes ambiguities in `scoping-v0.1`: execution receipts are distinct from identity bindings; the primary contrast is distinct from the churn interaction; record-count matching is not token matching; and missing evidence does not establish innocence. The prospective protocol is still not frozen. The 20-rules-of-learning skill is used to define concepts before comparisons, keep each claim focused, and connect methods to their supporting evidence; it is not a scientific novelty criterion.

Install `paper/requirements.txt`, then run `python paper/verify.py` and `python -m unittest discover -s paper/tests -v` to check the committed report. CI also runs the verifier under `python -O`. Verification does not rebuild artifacts: an old PDF or DOCX must fail after source changes. To intentionally revise the paper, edit `paper/content.json`, run `python paper/build.py`, export the DOCX to PDF with Microsoft Word, then run `python paper/verify.py --record-pdf`. Inspect every PDF page before committing both artifacts and their manifests. The PDF manifest records a validated local Word export; CI checks that export's content/provenance and does not render it.
