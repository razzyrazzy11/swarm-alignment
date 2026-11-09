# Historical paper fixture isolation

The legacy integrity and toy-figure tests read the live manuscript and its output
directory. Promotion of the completed six-reader ledger paper changed table
shapes, introduced four registered figures and required a different public-replay
lineage. Legacy tests then failed before reaching their intended stale-artifact,
tampering, marker or figure guard assertions.

The fixture at `paper/tests/fixtures/results-v3` preserves the historical
results-v3 manuscript as it existed at exact green pre-promotion commit
`166da1cd1d5b725455b03fb9a47aaf1e2b8dabe5`. These are that commit's exact Git
blob bytes, **not** a claim that they are bytes from the older results-v3 tag.
The manifest pins the source commit and all five artifact hashes; its own hash
is pinned in the fixture loader. A local `.gitattributes` preserves those bytes
across checkouts. Missing or modified fixture inputs fail closed.

Only legacy fixture setup and the toy figure test's baseline output path change.
All original assertions remain. The figure baseline now refers to its isolated
fixture output rather than the live manuscript's different package. New tests
check exact source/hash pins, independence from live content/output copies, and
rejection of missing, altered or manifest-tampered fixtures.

No production builder, verifier, public validator, scientific code, registration,
score or cutoff changes. The existing completed-ledger contract/layout and
negative tests remain active. The actual current paper must still pass
`python paper/verify.py` (and optimized verification), including its own complete
public replay, aggregate contract, actual PDF and every-page inspection receipt.
A historical fixture pass is not current-paper clearance.
