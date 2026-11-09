# Analysis registration correction: v2 supersedes incomplete v1

The published `hf-completed-original-analysis-v1` tag points to source commit
`bd7af08dd1ca987d97391849214c553a3554fd80`. The registration command had created
`research/hf-completed-original-analysis-freeze.json`, but an operator attempted
to stage a different, nonexistent filename containing `v1`. The shell continued
to tag and push the source commit without the registration artifact. The v1 tag
therefore does not contain the required freeze and is **not a valid completed
analysis registration**. It must not authorize supplemental-answer inspection or
a completed-results publication.

Keep the published tag unchanged. Preserve the original generated registration
bytes as `hf-completed-original-analysis-v1-incomplete-freeze.json`; this artifact
records the attempted registration rather than repairing the old tag. The root
session reported that no supplemental HF outcomes were inspected before this
correction. Original historical outcomes were already known, and supplemental
collection had already started, as disclosed in the original wrapper protocol.

The corrected source uses `hf-completed-original-analysis-v2`. Commit its source,
tests, protocol, this correction and the preserved incomplete registration;
generate a new registration at the normal freeze filename; commit that artifact;
then create and verify the new v2 tag before unblinding supplemental answers.
The v2 registration binds this correction and the preserved v1 artifact along
with the wrapper sources. Do not move or recreate the published v1 tag.

Before v2 registration, the wrapper also adds explicit stopped-child process
verification and reconciles completion summary cost/transient counts against
terminal receipts. The scientific requests, original scoring, estimands and
bootstrap remain unchanged. No empirical result is inferred from this
registration correction.
