# When Can a Swarm Be Audited?

> **Housekeeping — 9 November 2026.** Changes after 11:59 UTC remove unrelated
> references and process notes and update repository verification. The submitted
> paper, experimental data, results and conclusions are unchanged.

**Multi-Agent Oversight and Control.** Which part of oversight needs repair:
acquiring authentic evidence, delivering a usable verdict, or using sufficient
evidence correctly?

We study these distinctions in a controlled, matched experiment with a five-role
fake-data delegation workflow. Authentic host records are separated from
untrusted agent claims. The contribution is the matched experiment and its
measurements; the underlying distinctions build on existing work.

## Findings

The MAIN study contains **640 independent blocks, 2,560 matched trajectories and
53,760 planned reader calls**, all terminal, across six serving profiles.
Scripted calibration (240 calls) and exploratory peer influence (240 calls) are
separate. Repeated arms, views and readers do not increase the independent sample.
Failed calls remain in their assigned denominators and are never replaced.

The primary Gemma 26B PROCEDURE-minus-DIRECT effect on identical sufficient
FULL16 packets is **−2.07 percentage points [−4.06, −0.12]**, a 95% stratified
block-bootstrap interval. Correct-definite verdicts fall from 1,497/2,560 to
1,444/2,560. The proposed procedure did not improve the primary endpoint.

| Reader | Correct definite DIRECT / PROCEDURE, each /2,560 | Difference, pp [95% CI] |
|---|---:|---:|
| Adaption Gemma 26B, primary | 1,497 / 1,444 | −2.07 [−4.06, −0.12] |
| Adaption Gemma 31B | 2,075 / 2,330 | +9.96 [+8.55, +11.37] |
| HF Llama text | 834 / 900 | +2.58 [+1.72, +3.44] |
| HF Llama schema | 838 / 908 | +2.73 [+1.88, +3.63] |
| Ollama DeepSeek off | 1,689 / 1,689 | 0.00 [−0.55, +0.59] |
| Ollama DeepSeek low | 2,357 / 2,308 | −1.91 [−3.01, −0.82] |

Secondary intervals are descriptive, without familywise adjustment. Contract-record
restoration raises finite-domain answerability from 452/1,280 to 1,280/1,280.
Supported-correct gains, including required abstention, are 3.44, 15.31 and 10.31
percentage points for Gemma 26B, Gemma 31B and DeepSeek low, respectively.

Delivery and correctness remain distinct: DeepSeek off returns valid bare JSON
throughout FULL16 but makes 871 false executor accusations in 2,560 DIRECT
readings. The 788 actual target violations imply an always-NONE baseline of
69.22%. These results do not identify a universal repair policy or causally
partition failures into independent components.

## Report and data

- [Research report (PDF)](paper/out/swarm_audit_scoping.pdf).
- [Complete MAIN report](data/swarm-ledger-v1-public/report.json) and [study protocol](research/SWARM_LEDGER_COMPLETE_PROTOCOL.md).
- [Generator sensitivity](data/swarm-ledger-generator-sensitivity-v1/report.json) and [figure provenance](paper/figures/swarm-ledger-complete-v1/ledger_figures_provenance.json).
- [Current paper QA](research/editorial-paper-qa-v1.json) and [publication revision protocol](research/PUBLICATION_EDITORIAL_REVISION_V1_PROTOCOL.md).

Protocol and review documents are publication copies. Original registrations and
Git history remain preserved; these edited documents are not presented as the
original registered bytes. The [revision manifest](publication_revision/manifest.json)
records the reviewed changes against the earlier verified snapshot. Current
verification uses the explicit route below.

## Reproduce the results

Use a fresh checkout and Python 3.12. Obtain the manifest and launcher SHA-256
values from the [author-controlled verification section of the housekeeping PR](https://github.com/razzyrazzy11/swarm-alignment/pull/5). Values inside this checkout
are not independent trust anchors. Check the launcher before executing it or
installing dependencies; replace the two placeholders with those external pins.

```text
python -I -B -c "import hashlib,pathlib,sys; p=pathlib.Path('publication_revision/verify.py'); sys.exit(0 if hashlib.sha256(p.read_bytes()).hexdigest()==sys.argv[1] else 'Launcher pin mismatch')" EXTERNAL_LAUNCHER_SHA256
python -I -B publication_revision/verify.py --expected-manifest-sha256 EXTERNAL_MANIFEST_SHA256 --preflight-only
python -m pip install -r paper/preparation-requirements.txt
python -I -B publication_revision/verify.py --expected-manifest-sha256 EXTERNAL_MANIFEST_SHA256 --tests-only
python -I -B -O publication_revision/verify.py --expected-manifest-sha256 EXTERNAL_MANIFEST_SHA256 --tests-only
python -I -B publication_revision/verify.py --expected-manifest-sha256 EXTERNAL_MANIFEST_SHA256
python -I -B -O publication_revision/verify.py --expected-manifest-sha256 EXTERNAL_MANIFEST_SHA256
```

This route checks the file inventory, reviewed editorial changes, host simulation,
parsing, scores, bootstrap statistics, sensitivity results, paper and figures.
Original private-protocol admission is separately attested. Public replay does not
independently authenticate provider-native records, immutable model weights or a
host's truthfulness. Hashes detect changes to retained files; they do not establish
that every relevant event was recorded.

CI uses the author-controlled `PUBLICATION_MANIFEST_SHA256` and
`PUBLICATION_LAUNCHER_SHA256` repository variables before importing project code.
The original whole-tree commands and workflows preserved under `provenance/`
describe earlier editions and are not the current reproduction route.

## Earlier studies and limits

The earlier 192-source natural sample contained only NONE labels; its procedure
gain concerns false accusations and cannot establish incident recall. Original
HF completion recovers original identities and is not substituted into MAIN.
Earlier [scripted](research/STATEFUL_RESULTS.md), [live](research/LIVE_RESULTS.md),
[weight-policy](research/WEIGHT_RESULTS.md) and [factorial](research/FACTORIAL_RESULTS.md)
studies remain separate.

The ordered reviews cover [serving history](research/FINAL_REVIEW_1_SERVING_HISTORY.md),
[CI history](research/FINAL_REVIEW_2_HISTORICAL_CI.md),
[mathematics](research/FINAL_REVIEW_3_MATH.md),
[code and provenance](research/FINAL_REVIEW_3_CODE_PROVENANCE.md),
[primary sources](research/FINAL_REVIEW_3_PAPER_SOURCES.md), and
[narrative and visual checks](research/FINAL_REVIEW_4_NARRATIVE_VISUAL.md).
They are scoped, AI-assisted checks rather than independent empirical
replications or certification of originality. Current artifact status is bound
by the new QA receipt linked above. AI assistance and author responsibility are
disclosed in the report.

A synthetic role graph, authentic-host assumption, generator-relative oracle,
dependent views and unpinned serving limit transfer. No internal mechanism,
spontaneous collusion, general swarm safety or deployment guarantee is established.

Recorded final responses to the bounded fake-data tasks support parser replay;
credentials, private provider records and hidden reasoning are excluded from the
publication snapshot. See [SECURITY.md](SECURITY.md). Cleaning the current files
does not rewrite historical commits or remove previously downloaded copies.
