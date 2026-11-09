# Final review 4: narrative, remaining sections and visual publication check

This is a historical record for the edition and review time described below. The current publication edition has a separate [source-bound paper QA record](editorial-paper-qa-v1.json). Its updated presentation does not change the experimental data or results.

9 November 2026. **Status: review 4 complete within the narrative, template and visual coverage recorded below.** The coordinator completed the actual revised native export and inspected every rendered page; this reviewer checked the corresponding source/receipt identities and attributes that visual inspection to the coordinator. This reviewer did not run a build/verifier/export, interact with Word, or independently inspect all 15 revised page images. Final revised-artifact verification, exact-commit CI and submission remain separate gates.

## Reviewed version and scope

Read the three completed review-3 memos (`FINAL_REVIEW_3_MATH.md`, `FINAL_REVIEW_3_CODE_PROVENANCE.md`, `FINAL_REVIEW_3_PAPER_SOURCES.md`), the new `PUBLIC_VERIFICATION_SCOPE_ERRATUM.md`, current manuscript sections, appendices, references and captions, and the prose diff against artifact snapshot `49027a8dd4b0cca320d7d803d32262d1c5d694fb`. Inspected the actual unchanged acquisition PNG and its frozen provenance description. The current source raw SHA-256 is `6535bbeaf60ebbcd767b60c0cb73f364bc6d8ca90347709d82f58cb7a031ff26`.

The primary-source access and arithmetic coverage are those explicitly recorded by review 3; this narrative review does not constitute a fresh literature audit or full statistical replay. No external cross-model opinion was obtained.

Read-only checks and hashes are in `runs/final-review-4-narrative/narrative-source-checks.json`. No paper, data, figure, frozen source, registration, output or historical artifact was edited by this reviewer.

## Material review-3 findings: source corrections assessed

| Issue | Current manuscript disposition | Assessment |
| --- | --- | --- |
| Figure 2 named supported correctness including abstention, but plots correct-definite decisions | Results now says Figure 2 compares answerability with correct-definite verdicts excluding abstentions. Caption explicitly separates dashed oracle answerability, solid correct-definite reader lines and Table 3's supported-correct column. Alt text names the same endpoint. | Correct in source and the coordinator-inspected revised PDF: acquisition body on page 6, caption on page 7. Frozen provenance says “DIRECT supported-correct definite decisions,” with 1,280 matched trajectories/640 blocks and no independent-call intervals. The actual PNG has dashed finite-domain answerability and solid reader lines. No scientific figure/data change was needed. |
| Default paper verification could imply a fresh full native-journal audit | Appendix B and E now distinguish export-time native admission from later private failed-waiter/provenance checks and public reconstruction. The separate erratum explains the preserved frozen wording and public receipt limits. | Matches the targeted code review's actual coverage. Neither mode is described as freshly authenticating providers. Preserve the protocol/source/receipts; the erratum corrects interpretation without weakening a validator. |
| Closest prior work was credited too generically | Related work explicitly credits Syscon's observability/detection distinction and lack of first-pass monitoring gain from receipts. ActionLens remains a pre-execution probing precedent. | More precise novelty boundary; no unsupported field-first or replication claim introduced. The primary-source support comes from review 3's stated access, not a new source fetch here. |
| Abstention literature and logical support could be conflated | Risk–coverage tradeoffs are separated from justified abstention under the declared finite evidence domain. | The two meanings are distinguishable. The study claims no selective-risk guarantee. |
| Duplicate oracle-domain paragraph increased repetition | Appendix A retains the exact mandatory oracle-domain anchor while removing the redundant paragraph. Main-text limitations and Appendix D retain the sensitivity and unchanged-primary interpretation. | No decisive limitation lost. |

All four referenced PNG byte hashes match their registered manuscript hashes. Comparing the revised source with `49027a8`, these fields are exactly unchanged: abstract, author/affiliation, all references, Tables 1–3, embedded `ledger_results`, evidence status and preparation bindings. Every figure's file/path/hash, source commitments and width are unchanged; only Figure 2 caption/alt wording changes. These comparisons establish preservation of those fields, not a new proof of every original scientific claim.

## Narrative and previously less-prominent sections

The opening worker-update scenario gives a concrete reason to audit before introducing the formal oracle. The Methods example separates an authentic write receipt from continuing permission under revocation, then defines finite compatible histories. This is an adequate context-to-definition sequence for an eight-page research paper. Figure 4 supplies a later schematic of the five roles and evidence boundary. An additional worked numeric packet could help a tutorial, but is optional here and does not justify destabilizing a nearly full template layout.

The main distinctions remain stable: evidence availability, usable verdict delivery, and correct interpretation of sufficient evidence. NONE and ABSTAIN are explicitly distinguished. The text says these layers can coexist and do not causally partition errors. The new Figure 2 explanation now prevents a large correct-definite restoration gain from being confused with a much smaller gain that already credits required abstention.

The result-preservation check found no favorable-only rewrite:

- The abstract and results retain the adverse G26 primary, its interval and 640-block denominator. All six readers remain in Table 1; the unchanged DeepSeek-off result and adverse DeepSeek-low procedure result remain explicit in Interpretation.
- Schema/text intervals spanning zero, varied low/off effects, and the warning that computation/serving changes do not identify an internal mechanism remain. Contract-versus-metadata has no clear advantage; shorter receipt packets are qualified because content and length change together.
- Incident prevalence, always-NONE/ABSTAIN references, assigned-arm versus realized-attack distinction, and FULL16 error composition remain. Appendix C keeps the important tradeoff: fewer false accusations can coexist with more unsafe NONE answers and a worse primary.
- Appendix D retains actor intention-to-treat effects, nonpositive/uncertain interaction, scripted calibration rather than population recall, and peer-note influence intervals crossing zero. None is promoted into emergent collusion, covert language or an additional independent MAIN sample.
- Generator-domain sensitivity remains in main-text limitations and Appendix D. It preserves the original adverse primary, qualifies “insufficient” relative to a declared domain, and supplies finite-cohort counts without new sensitivity intervals or model calls.
- Appendix A retains synthetic/finite scope, authentic-host assumptions, model drift, event-versus-group-blame limits and dual-use/selective-deletion concerns. The manuscript makes no containment or deployment-safety guarantee.
- Appendix B retains the earlier all-NONE sample and its incident-recall limitation, separate original HF recovery, failed offline attempts and operational amendments. These are not pooled into MAIN. The optional serving pilot stays blocked/unrun.
- Code/data access is described as a currently private repository with judge access and submission left to the author. Appendix E distinguishes hosted route identifiers from immutable weight hashes, fixed request bounds from reproducible provider behavior, final answer scoring from private thinking, and public replay from full native-archive revalidation.

The source remains information-dense, especially in the paired schema/thinking contrast paragraph and operational Appendix B. These are genuine reading-cost tradeoffs under the page ceiling, rather than omissions requiring more claims or tables. No further material narrative blocker was identified in this coverage. This is not a guarantee of judging outcome, exhaustive originality or universal comprehensibility.

## Template comparison and layout constraints

Independently compared the actual downloaded `Apart Research hackathon submission template.docx` with `paper/official-template.docx`:

| Template | Raw SHA-256 |
| --- | --- |
| Downloaded file | `ae234397c7fd63d707e63dc6088f0f0109aefe0219fe287cfe0c5b721e3420c4` |
| Repository official template | `20bb4d221e722f7eca33c7bd3add4c749ddc76d346b12cdb9ada271083e3a36d` |

Both ZIPs have 15 entries, identical entry-name sets, no duplicate names, and **zero changed entry-content bytes**. The whole-file difference is a ZIP-container representation difference; it does not evidence different OOXML styles, fonts, page geometry, template prose or embedded resources. No template-style modification is justified by that raw ZIP hash mismatch. Keep the repository template and its existing commitment.

The unchanged abstract has 188 words. The required author/affiliation and Limitations and Dual-Use / Ethical Considerations appendix are present in source. The ceiling remains eight main pages before references/appendices, with original template geometry, fonts and run sizes. These source/template checks do not establish corrected-PDF pagination, absence of clipping or readability at actual page scale. Do not shrink fonts/margins to obtain a page-count pass.

## Corrected-artifact visual gate — completed by the coordinator

The coordinator reports the new actual native export completed at 09:47:49 UTC, preserved source bytes, and closed/quit its owned Word instance with the native PID subsequently absent. This reviewer did not perform that process inspection. The source raw SHA-256 remains `6535bbeaf60ebbcd767b60c0cb73f364bc6d8ca90347709d82f58cb7a031ff26`, matching the narrative review above.

The revised artifact identities recorded in the actual visual-review receipt are:

| Artifact | Identity |
| --- | --- |
| Corrected PDF | SHA-256 `15b9676156bbe73d198a7202e42bde169ff4afef4457b6aa9bed18b3b3955f20`; coordinator-reported size 512,748 bytes |
| Corrected DOCX | SHA-256 `7c38f220321a4794870006b81b847b5012ffe316a0977c19b81c667d5a101631` |
| All-page figure QA receipt | `paper/out/figure-review.json`, raw SHA-256 `6892d74ad17d20cc8bdc63c0b3f0a98d84cf556ae3c0f67a23e35e93b369f369` |
| Detailed actual inspection record | `runs/paper-review4-20261109T094000Z/actual-visual-review.json`, raw SHA-256 `f19a4d245bb236fd62327ef5db460d77a098ed9c0c19ddb432b69196cce439d8` |
| Actual page rendering record | `runs/paper-review4-20261109T094000Z/render-result.json`, raw SHA-256 `716ce11e5ddcfa0228968a642fa3c62df9684ed9b1cdd4523811f467ef4b4d4a` |

The renderer produced all 15 pages at 110 dpi. At 09:51:07 UTC the coordinator recorded actual visual inspection of pages 1–15, in five image batches. The coordinator observed no clipping, overlap, missing figures, illegible table text or other layout blocker. The corrected Figure 2 explanation is visible in the acquisition body on page 6 and caption on page 7. Main text ends with Code and Data on page 8; references occupy pages 9–10 (page 10 is sparse); appendices occupy pages 11–15. A sparse references page is not an eight-main-page violation. The 188-word abstract remains within the stated bound.

This reviewer read the actual render, detailed review and figure QA receipts. Their PDF hashes agree, both inspection inventories enumerate every page 1–15, and the detailed review's QA hash matches the actual figure QA receipt bytes. The renderer deliberately leaves its own visual-QA flag false; the separate later inspection receipt supplies the human/agent page-inspection attestation. Rendering alone is not presented as inspection, and the old artifact's page review was not reused.

The revised source, template equivalence, actual native export, coordinator all-page inspection and hash-bound receipt now support closing this narrative/visual review. This is neither an independent second all-page visual pass nor a new scientific/native-archive audit. The coordinator's final ordinary private record/verify run was still running when this update was authorized; optimized/private and public checks plus final exact-artifact CI remained separate pending validation. No success is asserted for those pending gates here.

Current CI repair of the separately observed synthetic clock/scheduling failure is also a separate engineering gate. This memo does not call that run green or authorize relaxing its guards. Official submission/access/receipt remain separate author actions. **Review 4 is complete within the explicit coverage above; project completion and submission are not claimed.**
