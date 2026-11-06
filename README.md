# When Can a Swarm Be Audited?

Primary-source scoping study and prospective experiment protocol for the Apart Swarm Alignment Hackathon, November 6–8, 2026.

Recommended focus: Track 4 (Multi-Agent Oversight and Control), with Track 3 relevance. Test coordinated selective evidence loss and identity churn, using evidence-matched monitors and an explicit insufficient-evidence answer. This repository currently contains research planning and a report; **no LLM experiment has been executed and no detector performance is claimed**.

- `research/DECISION.md`: recommendation, alternatives, sources, judging alignment, budget and schedule.
- `research/PROTOCOL.md`: prospective design; not a completed or frozen preregistration.
- `research/SOURCE_AUDIT.md`: coverage and access limitations.
- `paper/out/swarm_audit_scoping.pdf`: template-based scoping paper.
- `paper/out/swarm_audit_scoping.docx`: editable paper.
- `paper/build.py`: document assembly from the current official template.

## Prior work and provenance

Razvan Sacara's preexisting project is https://github.com/razzyrazzy11/trusted-agent-sting (October 2026). Its study design, code, data and results predate this sprint and are not new contributions here. This project borrows the practices of prospective hypotheses, deviation logs, CI, version tags and report traceability. No prior experimental data or code has been imported. The attached previous conversation is background, not verified evidence or an instruction source.

The repository's GitHub-created initial commit is `bbed9cd`. The first commit made for this task is `69172e8`, containing only secret and raw-output exclusions. Citation metadata and the security policy follow in `818653d`. No history was rewritten.

## Reproducibility and release

The report is a scoping study with an elementary analytical observation, not an empirical swarm benchmark. See `research/PROTOCOL.md` before experiments. Freeze prompts, models, scoring, split manifests and stopping rules in a separate commit/tag before confirmatory runs. Document every later change in `research/DEVIATIONS.md`; do not backdate a preregistration.

Raw outputs belong under `runs/` and remain ignored. Keep only redacted aggregates and benign fixtures in Git. Do not commit credentials. See `SECURITY.md` for GitHub feature limitations and responsible disclosure.
