# Public verification scope: corrective clarification

9 November 2026. This erratum preserves the immutable `paper-public-verification-v1` protocol, source, registration and issued receipts. It corrects their interpretation; it does not amend the scientific analysis, weaken a validator or authorize another export or model call.

The frozen protocol and several source comments describe the default local path as retaining private/native admission. That wording can imply a fresh validation of every native journal. The actual source has a narrower distinction:

- During the successful offline V2 **exports**, HF `hf_completed()` called `collection.private_completed()` before projection, and MAIN `export_main()` called `admission_main()` before serialization. The retained seven-stage owner, export outputs and release proofs bind that execution and its artifacts.
- Later default paper verification checks registered lineage, retained private failed-waiter evidence and termination/provenance, then reruns public reconstruction and mathematics. It does **not** repeat full native-journal admission.
- Explicit public verification checks the registered source/artifact/receipt commitments and reruns public mathematics without reading the private failed-waiter evidence. It does not freshly authenticate native records, the host or a provider. Neither mode turns a hash into provider-signed truth.

The public receipt records the admitted release and its lineage. The issuing `prepare_complete.ready()` gate checks completed ownership, provenance and replay; it does not itself repeat all native-journal checks previously performed during export. Full native-journal revalidation requires the private archive and the corresponding native-admission path.

The owning code paths, line references, proof hashes and review limits are documented in [final code/provenance review](FINAL_REVIEW_3_CODE_PROVENANCE.md). No specific omitted export-time native check or data corruption was found in that targeted review. It was not a fresh audit of every private record.

The public figure receipt also retains limited executable-path metadata. The packet must not be described as fully anonymized. This erratum does not reproduce that path or silently alter its hash-bound bytes.
