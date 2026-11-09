# Explicit public paper verification boundary

This is a prospective offline publication-boundary amendment, not an inference,
scientific-score, decoder or native-admission amendment. The unchanged private
`paper.prepare_complete.ready()` gate remains authoritative for actually
complete and terminated owners, exact source/registration lineage, private/native
admission and all seven frozen scientific stages. The default paper verifier
continues to require that private gate. Explicit public mode verifies a preserved
receipt and unchanged public mathematics; it never claims fresh native liveness
or provider authenticity from hashes alone.

## Prospective registration

Commit the implementation, integration, tests, workflow and this protocol before
creating `research/paper-public-verification-v1-freeze.json`. Its exact keys are
`schema_version`, `tag`, `created`, `base_commit`, `source_sha256`,
`parent_registration_sha256`, `public_artifact_sha256`,
`verified_figure_input_sha256`, `owner_state_sha256`, `owner_supervisor_sha256`,
and `method`.

Schema version is integer1. Tag is `paper-public-verification-v1`; method is the
module's exact `METHOD` string. Created is a past/current UTC ISO timestamp;
base commit is a full40-hex ancestor of the tag. `source_sha256` binds exactly
the module's `SOURCES` inventory using LF-normalized SHA256: public replay,
integration contract/verifier, both focused tests, workflow, `.gitattributes`
raw-byte checkout protections and this protocol.
`parent_registration_sha256` binds exactly V2 recovery, V1 recovery and paced
analysis freezes. Both private failed waiter logs/states remain private and
immutable: only their already-frozen hash commitments are preserved publicly.

`public_artifact_sha256` is the exact raw-byte map returned by
`public_artifact_hashes(root)`: all current MAIN public shards/registrations,
report and manifest; HF report/supplement/proof; MAIN proof and public lineage;
all generated figure/provenance files; and registered sensitivity outputs.
This pre-issuance freeze pins the completed release itself, preventing a changed
receipt from rewriting its own artifact commitments. The figure-input hash
pins the existing successful private verified-public-input receipt, and the
owner-state hash pins the actual completed V2 seven-stage state. The owner
supervisor hash separately pins the RAW source-byte hash preserved in that
state, which can differ from LF-normalized registration source hashes after a
CRLF Windows checkout. Issuance requires the preserved state, prospective raw
owner commitment and local raw supervisor bytes to match. Consumers compare
against that frozen raw commitment while source/tag checks remain independently
LF-normalized; no frozen state or supervisor is rewritten. These fields are
hash-only registration inputs; private state/log contents are not exported.
No PDF, build manifest or admission-receipt hash creates a circular dependency.

Commit the freeze, create the tag and push source/freeze/tag before issuing or
consuming real admission. Consumer registration checks local tag bytes and
ancestry offline; issuer additionally checks the remote tag object matches.

## One-shot issuance

`python -m paper.public_replay issue` refuses existing public outputs, verifies
the pushed prospective registration, then calls the unchanged full private gate
before writing anything. It rechecks source and artifact stability, the exact
complete owner source/freeze/state hash, and its actual private termination proof.
The existing figure input is strictly allowlisted, including successful scientific
runtime metadata, before an exact byte copy is emitted at
`research/paper-public-figure-input.json`.

The new `research/paper-public-release-admission.json` has exactly:
`schema_version`, `kind`, `issued_at`, `scope`, `registration_tag`,
`registration_freeze_sha256`, `public_artifact_sha256`,
`verified_figure_input_sha256`, `preserved_owner`, `provenance`, and
`ledger_sources`. Scope explicitly limits public verification to source/artifact
commitments and frozen mathematics. The owner attestation contains completion,
the ordered seven stages, absent child, zero exit/inference counts, source/freeze
and state hashes, and termination verified at issuance. It contains no PID,
native timestamp/response identifier, private log, model answer, credential or
account information. Provenance crossmatches exact MAIN/HF driver hash maps and
both preserved failed waiter commitment sets against their public frozen proofs.
Ledger bindings equal those returned by the unchanged private gate.
The fully assembled admission candidate is checked in memory by the same pure
metadata validator used by the fixed-path public consumer before either public
file is opened. A source/owner/provenance/schema mismatch therefore leaves both
new targets absent; no consumer bypass or filesystem-existence fallback exists.

Issuance never retries a POST, restarts a processor, changes a failed identity,
rewrites an old source/freezetag/state/log or edits the scientific validator.
Partial issuance fails closed and is preserved for diagnosis rather than silently
overwritten. No automatic inferred success or alternate owner is permitted.

## Public consumer

`verify_public_admission(paper)` first verifies exact receipt schemas, source and
tag bytes, ancestry, parent registration hashes, frozen artifact/input maps,
preserved owner attestation, driver/failed-waiter hash crossmatches, MAIN and HF
proofs, figure input and ledger source bindings. Unknown fields, proofs, sources,
paths, missing files and drift fail closed before mathematical replay.

It then calls the unchanged frozen paced HF reconstruction, unchanged figure
provenance checker using the safe input copy, and unchanged generator sensitivity
reconstruction. The common completed-report loader still performs the original
MAIN companion checks, complete public statistical replay, report validation and
source binding. No private waiter state/log or native process query is read by
the explicit public path. Public hashes do not newly authenticate providers or a
compromised host; the preserved local private archive remains necessary for that
claim. Normal and optimized verification and actual every-page PDF QA remain
separate required gates.

Synthetic negative tests cover artifact-map substitution, source/tag/receipt
drift, missing/unknown/private fields, owner/stage/exit mutations, exact input
copy, fail-closed ordering, no private reads and unchanged frozen replay calls.
They do not issue or replay the actual empirical release.
