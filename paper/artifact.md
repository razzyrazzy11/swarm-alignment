# Template execution contract

Reference: `paper/official-template.docx`, downloaded from the current Guidelines link on 6 November 2026. SHA-256: `20bb4d221e722f7eca33c7bd3add4c749ddc76d346b12cdb9ada271083e3a36d`. Original attached template remains untouched outside this repository. Current reference rendered to `../template-qa/current.pdf`, five pages; all pages inspected.

One portrait US Letter section, 8.5 × 11 inches, 1 inch margins. Preserve final sectPr exactly. Embedded Old Standard TT regular, bold and italic; preserve font parts, font table, theme, numbering and styles byte-for-byte. Body uses normal style with source font and source run size; remove italic guidance emphasis from replacement prose. Preserve heading patterns (Heading2 with explicit 14pt run properties, Heading3 14pt) and title (20pt bold centered). Do not shrink text to fit. Original title borders and footnote are source furniture, retained despite a generic preference against rules. Preserve the event footnote and its hyperlink.

Editable locations: word/document.xml body table 0 title paragraph; author table inside table 0 row 1; abstract guidance paragraph; body paragraphs from Introduction through LLM Usage Statement; body table 1 (remove guidance box). Replace six author placeholders with a single centered source-derived author paragraph, using the provided prior-project name and truthful participant affiliation. Preserve With Apart Research and Abstract headings. Remove optional unused author-contribution heading rather than invent participation. Replace all guidance, examples and placeholder references. Clone source normal and heading paragraphs for expanded content; clear inherited list numbering and bookmarks from clones to avoid duplicate IDs. New table/figure content may use source-derived body text in simple fixed-width cells. References and appendix begin on new pages; extra pages are expected.

Package changes allowed: word/document.xml only. All other zip parts including styles.xml, numbering.xml, settings.xml, footnotes, relationships, embedded fonts and theme must remain byte-identical. The source document contains no image slots or content controls; no drawings added. No existing TOC/REF/PAGE field refresh is needed. Title footnote reference must be retained. Tables and text boxes are inspected through XML, including nested author placeholders.

Fidelity gates: verify original SHA; compare all preserve-only package parts; compare sectPr; no remaining italic guidance/author placeholders; inspect every final rendered page. Use Microsoft Word hidden automation for PDF export because the bundled dependency runtime contains no LibreOffice. Rebuilding docx requires lxml 6.1.1. Rendering requires Word or a separately supplied approved renderer; CI validates committed artifacts without pretending to render. The `../template-qa/current.pdf` path is local visual-review evidence outside this repository, not a downloadable project artifact.

Current evidence status, 7 November 2026: completed original factorial primary and separately registered Ollama reader extension, with the original HF secondary explicitly incomplete. The verifier binds the paper to `research/factorial-report.json`, the original and reporting freezes, the Ollama freeze and the preserved earlier result files. There are 576 actor calls, 14,252 main readings and 218 separate calibration readings; original readers returned 9,742/11,640 and Ollama returned 4,728/4,728. Original unstarted HF calls remain unknown. No training occurred. Artifact integrity does not certify empirical generalization, provider authenticity or final billing.

Historical checkpoint: at 7 November 04:18 UTC the factorial integration had not been authored. That checkpoint preserved 576 worker and 9,706 reader terminals, with 1,934 reader requests unstarted. The then-deferred writer required complete phases. The later disclosed reporting amendment permits complete-primary/incomplete-secondary reporting and logical bounds; it does not turn that historical plan into a completed original study.

Final Word export: 190-word abstract, seven main pages, two reference pages and four appendix/disclosure pages (13 total), 120,809-byte PDF. Normal and optimized verification pass; all 23 paper regression tests pass. The final 13 PDFium-rendered pages were inspected by the assistant for clipping, missing cells, stale text, misplaced headings and source/template fidelity. Only `word/document.xml` differs from the official DOCX package. The four-column Table 1 has a tested layout branch; legacy three-column layouts remain supported. The single document-operation marker was recorded before authoring and retained through layout continuations; it was not repeated. Local visual evidence is `../paper-qa-review/page-1.png` through `page-13.png`, outside the published package.

## Prospective scientific PNG figure extension

The user requested scientific visual aids drawn from retained empirical records.
This extension is opt-in through a `figures` registry; the current manuscript and
historical DOCX, PDF and manifests remain unchanged. Empty/absent registries keep
the legacy table-based FIGURE1 behavior and its original builder provenance.
No new result or illustrative performance figure is created by this pipeline
work. Synthetic test PNGs are toy fixtures only. The root session already
recorded the new authoring marker; this continuation does not repeat it.

For registered PNGs, the permitted package delta expands narrowly to inline
drawing markup in `word/document.xml`, exactly the registered owned PNG media
parts, appended image relationships in `word/_rels/document.xml.rels`, and a PNG
content-type declaration only when required. Existing relationship semantics
remain unchanged; external targets, orphan images and unregistered package
parts are rejected. Every other original part stays byte-identical, including
styles, embedded fonts, font table, numbering, theme, settings, footnotes and
the footnote hyperlink. The exact original final section geometry remains a
required comparison. Figure paragraphs and captions inherit template formatting;
body fonts are not reduced to make content fit.

Each registry entry binds its PNG bytes and public input files by SHA-256, uses
a safe project-relative path, supplies a visible caption and alternative text,
and requests a width no greater than 6.5 inches. Height follows the pixel aspect
ratio and must fit the usable page region. Captions remain real Word paragraphs;
axes and plotted labels are pixels. The manifest lists actual package deltas
and figure/input commitments. A PDF export with registered figures must contain
embedded image objects as well as pass the existing exact text, title footnote,
page geometry, size and page-count checks, including under optimized Python.

PDF image-object checks establish presence, not exact semantic or pixel identity:
Word can recompress or transform images. Before final attestation, the root
session must render and inspect **every page**, confirm each expected scientific
figure against its source PNG and caption, and record that manual inspection.
Neither a caption-only PDF nor a text-only verification is sufficient. Rebuilding
or rendering the actual paper is deferred until its actual-data writer is ready.

Implementation entry point: `python paper/figure_build.py`, only when the registry
is nonempty. The original `paper/build.py` bytes and legacy builder SHA stay
unchanged. The figure branch records both that original builder hash and the
new figure-builder/verifier hashes. Registered captions participate in citation
validation. Before `--record-pdf`, write `out/figure-review.json` after inspecting
all rendered pages: schema version 1, final PDF SHA, a figure-ID-to-PNG-SHA map,
all page numbers in order, `inspected_all_pages: true`, reviewer and review time.
This attestation must never be generated by a tool that has not inspected the
rendered pages. Neither builder invocation nor figure unit tests render Word.

Registry API (all seven entry fields are required; hashes shown here are
placeholders, not evidence):

```json
{
  "figures": [{
    "id": "FIGURE2",
    "path": "figures/actual-data-contrast.png",
    "sha256": "<64 lowercase hexadecimal characters>",
    "source_files": {"research/public-result.json": "<raw-file SHA-256>"},
    "width_inches": 6.0,
    "caption": "Figure 2. A caption describing the retained data and uncertainty.",
    "alt_text": "A plain-language description of the figure."
  }]
}
```

Put the exact `FIGURE2` marker once in a `sections` paragraph list. The builder
inserts the inline image followed by its real-text caption. PNG paths resolve
under `paper/figures`; source paths resolve under project `research` or `data`.
Paths cannot escape those roots. Supported sources are JSON, JSONL, CSV, TSV
and Markdown; hash the actual file bytes. PNGs must be noninterlaced 8-bit
grayscale, grayscale-alpha, RGB or RGBA; palette images are not supported by this
deliberately small validator. Output image parts use their full SHA in the name.
The registry is absent from the unchanged historical manuscript.
