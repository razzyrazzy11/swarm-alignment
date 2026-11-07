# Legacy HF delivery review: narrow, post hoc and descriptive

Checked 7 November 2026. This review used only three frozen owning source files
(`factorial_study.py`, `factorial_analysis.py`, `factorial_reporting.py`), small
synthetic runtime probes, and a few **already released** `original_hf` final
responses from the immutable `results-v3` public case file. No original private
native receipts, new HF-completion supplement answers or new main outcomes were
opened. No inference, network call, scoring change or source-code edit occurred.

## Prompt and parser agree on the schema

The frozen DIRECT contract requires exactly `status` and `worker_id`, with
statuses NONE, ABSTAIN or EXECUTOR. NONE/ABSTAIN require null; EXECUTOR requires
A/B/C. PROCEDURE repeats the same schema and explicitly disallows intermediate
reasoning. The frozen HF request builder placed the full DIRECT instruction
unchanged in a system message. Its body requested 4,096 output tokens and did
not request server-enforced structured output. This was a text-instruction
condition, not a constrained-schema condition.

Synthetic calls to the **unchanged** frozen scorer established:

| Synthetic final text | Frozen result |
|---|---|
| Exact two-key JSON, valid NONE/null | Parsed NONE; strict schema valid |
| Same JSON inside one exact JSON fence | Parsed NONE; strict schema invalid |
| Extra `reason` key | INVALID |
| Lowercase `none` status | INVALID |

Thus the parser accepts the schema actually requested. Its acceptance of one
outer fence is more permissive than strict JSON compliance, which is reported
separately. No requested/accepted key mismatch was found. These probes do not
alter any historical result or supply replacement answers.

## What the small released-final sample showed

Selection was the first three available main `sufficient` records per procedure
in the frozen public file's order: three DIRECT and three PROCEDURE responses.
Only categories were retained here; final prose is not reproduced.

| Category | DIRECT (3 sampled) | PROCEDURE (3 sampled) |
|---|---:|---:|
| HTTP 200, normalized completed, known token usage | 3 | 3 |
| Frozen decoder rejects surrounding output | 3 | 3 |
| Prose surrounding an extractable JSON object with the requested two keys | 3 | 2 |
| No extractable JSON object in the final text | 0 | 1 |
| Frozen INVALID / strict-schema false | 3 | 3 |

No missing or extra top-level keys, or disallowed status value, was observed
in the five extractable objects. Extracting the first JSON object is a
**descriptive categorization only**: it may be an example in the prose rather
than an intended final answer. It was not rescored as a rescued verdict. The
unchanged scorer reproduced every sampled published score exactly. A public
row-validation spot check also passed the frozen field, returned-model alias
and cost checks.

These six records are not a random sample, and their category counts must not
be extrapolated to all historical HF calls. They show a concrete final-format
failure in the inspected cases, rather than truncation or an incomplete status
in those cases. They do not establish the semantics of rejected prose or the
reader's accuracy conditional on producing a valid answer.

## Native final-field handling: synthetic checks, not private replay

A synthetic standard HF chat-completions payload containing the requested JSON
in `choices[0].message.content` normalized to exactly that content. Additional
synthetic `reasoning` and `reasoning_content` fields were excluded from the
normalized final text. A stop finish normalized to completed and parsed NONE;
a length finish preserved the same text but normalized to incomplete and was
scored INVALID. Both preserved known usage.

This rules out a simple mismatch for that standard native shape and verifies
the intended final-field/truncation behavior. It does **not** independently
replay the actual historical native payloads: those were deliberately outside
this task. The original reporting code contains native-normalization and
request-identity checks, but this note does not claim to have rerun them against
private receipts. A provider-specific delivery defect cannot be excluded from
public finals and synthetic probes alone.

## Consequence for reporting

No prompt/parser schema disagreement or simple synthetic final-field bug was
found. The inspected released finals support an operational formatting-failure
description. A zero correct-definite or zero valid count must not be translated
into an estimate of semantic reasoning competence. Keep serving completion,
parse/schema compliance and supported correctness separate.

Retain the original frozen scoring and all invalid terminals. Do not strip
prose retrospectively to improve the old condition, change its endpoint, or
pool an extractive post hoc analysis into the registered result. The new
matched text-versus-schema experiment can examine delivery prospectively;
its findings cannot be assumed from this small legacy spot check.
