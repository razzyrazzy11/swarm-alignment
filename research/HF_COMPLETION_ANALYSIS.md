# Completed original-reader analysis

This is a new reporting wrapper for the original three-reader experiment. The
scientific requests, endpoints, score, source groups, estimands and bootstrap are
unchanged: `factorial_analysis.build_cases` and `factorial_analysis.analyze` are
called directly. The later Ollama extension remains a separate historical study.

The original results were known when this wrapper was written. HF operational
completion was already collecting when the wrapper was specified. Freeze this
wrapper's source and tests before inspecting any supplemental HF answer. This is
not a retrospective claim that a new scientific hypothesis was preregistered.
The original scientific protocol predates the original observations; the
completion operational amendment separately fixes which requests may be started.

## Inputs and admission

The immutable `results-v3` report, context plan, 576 actor records, trajectories,
manifest and public cases are source anchors. Keep their bytes unchanged. Select
the 9,742 terminal `original_*` cases and exclude every later extension condition.
The only added public artifact is a sanitized supplement of the 1,898 originally
unstarted HF identities. Its request-body hash must equal the reconstructed
original request. No request is repeated, substituted, imputed or dropped because
it failed. All 11,640 original identities must occur exactly once.

Private export first requires stopped original/completion drivers and children,
absence of collector locks, the original raw-prefix hash checks, and an exclusive
collection lock. Replay completion starts/terminals, native normalization,
returned-model aliases, body hashes and exact known-token costs or unknown-usage
reservations. Public fields exclude native IDs, headers, error bodies, private
error receipts, reasoning and native responses. An unknown usage reservation is
not zero usage; a known zero-token response remains known.

## Analysis and interpretation

Terminal completeness means every planned identity has a terminal receipt. It
does not mean every call served successfully or produced a valid decision. Keep
the historical five HTTP 429 terminals and all new terminal failures as INVALID
under the original scoring. Report successful serving, strict-schema validity,
and terminal completeness separately. The operational allowance of 256 new
transient terminals is not a license to replace failed observations.

Rebuild the complete original cases and run the unchanged frozen analysis for
all three original readers. The original Gemma-26B primary estimate and interval
must remain identical. Preserve all original raw/gated, calibration, acquisition,
baseline, cost and bootstrap outputs; do not select results by favorability.
Multiple readers and packet views do not increase the 192-source denominator.

## Release and verification

The root session commits these wrapper sources, invokes `freeze`, commits the new
registration, and creates `hf-completed-original-analysis-v1` before unblinding.
Only then may it explicitly invoke `export --publish-after-collection`. Export
refuses an incomplete source grid, unresolved starts, active drivers, changed
prefixes or mutable source anchors. It writes new
`research/hf-completed-original-results.json` and
`data/hf_completed_original_supplement.jsonl`; it never overwrites the historical
partial report or its artifacts.

`python -m experiments.hf_completion_analysis verify` uses only Git, committed
sources and public artifacts. It needs no credentials, run folders or network.
It reconstructs every original point estimate and bootstrap interval from the
unchanged old public data plus the new supplement. Private journal commitments
support provenance but cannot make privately stored native responses publicly
auditable; that limitation is explicit in the new report.
