# Development serving diagnostic, before main collection

Checked 7 November 2026 while the registered development reader phase was
still running. These are operational metadata from the **completed reporter
phase**, not reader accuracy, actor validity, incident yield or a main result.
No model answers were inspected for this diagnostic. Every terminal remains in
the immutable development journal; failures are not retried or replaced.

| Actor serving profile | Assigned / terminal | HTTP 200 | HTTP 504 | Mean client latency, seconds |
|---|---:|---:|---:|---:|
| G26 | 80 / 80 | 80 | 0 | 0.670 |
| GLM53 flash | 80 / 80 | 80 | 0 | 5.693 |
| Q27 | 80 / 80 | 80 | 0 | 9.358 |
| Q397 | 80 / 80 | 57 | 23 | 46.524 |

The 23 Q397 gateway errors averaged 60.339 seconds. This timing is consistent
with a gateway timeout boundary, but does not establish which internal
component timed out or why. HTTP 200 also does not establish a valid action or
verdict. A neutral capability check therefore cannot substitute for task-like
serving validation. The final reader-phase diagnostic must be assessed
separately, after its complete terminal graph is admitted.

The [Adaption Responses request reference](https://docs.adaptionlabs.ai/api/resources/responses/methods/create)
documents `max_output_tokens` and `temperature`; its displayed request schema
does not document a thinking-effort or thinking-budget control. Upstream model
documentation alone does not establish that an additional field is supported
by this hosted gateway. No such field, endpoint, prompt or output limit is
silently changed in the registered study. A gateway failure cannot be labeled
as inability to reason from sufficient evidence.

The prospective scheduling amendment investigates offered concurrency with
task-like, excluded pilot requests. Its capacity decision uses serving
metadata rather than verdict accuracy. All candidates remain constrained by
the provider-wide client ceiling, dispatch spacing, financial reservations,
backoff and no-retry rules. More offered concurrency is neither a documented
provider entitlement nor a guarantee that the errors disappear.

The main workload forecast must include observed transient backoffs and full
reservations for unknown usage. When measured pilot throughput already includes
cooldowns, an additional projected cooldown can be conservative; disclose that
possible overlap rather than call the projection an exact runtime prediction.
No main cohort should launch merely because sufficient credit remains if the
complete registered comparison is already forecast to miss its cutoff.
