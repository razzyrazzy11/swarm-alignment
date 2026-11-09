"""Paper/figure checks for the new disclosure route, with frozen pure helpers.

This does not call the original full private/source admission wrappers, alter an
artifact, export Word, or fabricate a new visual review. The exact submitted PDF
and its existing all-page review are retained.
"""
from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import re
import sys
import zipfile

from .admission import CANONICAL_DOCX, CANONICAL_PDF, PRIVATE_ADMISSION, require

_RESEARCH_BINDINGS = (
    'offline-release-recovery-v2-freeze.json', 'hf-offline-release-recovery-v2-proof.json',
    'offline-release-recovery-v1-freeze.json', 'hf-offline-release-recovery-proof.json',
    'paced-resume-analysis-v1-freeze.json', 'swarm-ledger-paced-v1-freeze.json',
    'swarm-ledger-paced-resume-release-proof.json',
    'rate-resume-analysis-v1-freeze.json', 'swarm-ledger-rate-v1-freeze.json',
    'swarm-ledger-rate-resume-release-proof.json',
    'efficient-resume-analysis-v1-freeze.json', 'swarm-ledger-efficient-v1-freeze.json',
    'swarm-ledger-efficient-resume-release-proof.json',
    'provider-resume-analysis-v1-freeze.json', 'swarm-ledger-resume-v3-freeze.json',
    'swarm-ledger-provider-resume-release-proof.json',
    'server-resume-analysis-v1-freeze.json', 'swarm-ledger-resume-v2-freeze.json',
    'swarm-ledger-server-resume-release-proof.json',
    'router-resume-analysis-v1-freeze.json', 'swarm-ledger-resume-v1-freeze.json',
    'swarm-ledger-resume-release-proof.json', 'hf-completion-v3-freeze.json',
    'hf-completed-original-results-v3.json', 'adaption-serving-pilot-v1-freeze.json',
    'adaption-serving-pilot-results.json',
)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _normalized_sha(path):
    return _sha(path.read_bytes().replace(b'\r\n', b'\n'))


def _module(root, name, files):
    module = importlib.import_module(name)
    path = Path(module.__file__).resolve()
    require(path.is_relative_to(root) and path.relative_to(root).as_posix() in files,
            'Artifact helper loaded outside admitted source')
    return module


def compare_docx_parts(path, expected):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)) and set(names) == set(expected),
                'DOCX package inventory differs')
        for name, raw in expected.items():
            require(archive.read(name) == raw, 'DOCX package part differs')


def disclosed_source_bindings(root):
    """Hash the disclosed copies; this is not original Git/protocol admission."""
    directory = root / 'data/swarm-ledger-v1-public'
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    result = {name: _sha((directory / name).read_bytes()) for name in (
        'manifest.json', 'report.json', 'registration.json', 'operational-registration.json',
    )}
    result.update(scientific_registration_sha256=manifest['registration_sha256'],
                  operational_registration_sha256=manifest['operational_registration_sha256'])
    for name in _RESEARCH_BINDINGS:
        path = root / 'research' / name
        if path.exists():
            result[name] = _sha(path.read_bytes())
    return result


def verify_text_order(pages, paragraphs, title, note_texts, compact):
    """Retain the original strict extra/stale/reordered-text check."""
    text = compact('\n'.join(pages))
    for paragraph in paragraphs:
        if paragraph.strip():
            require(compact(paragraph) in text, 'PDF source paragraph absent')
    require(len(note_texts) == 1, 'Official title footnote contract differs')
    title = compact(title)
    require(text.count(title + '1') == 1, 'PDF title footnote marker differs')
    note = '1' + note_texts[0]
    require(text.count(note) == 1, 'PDF event footnote differs')
    body = text.replace(title + '1', title, 1).replace(note, '', 1)
    require(body == compact(''.join(paragraphs)), 'PDF has stale, extra or reordered text')
    starts = [i for i, page in enumerate(pages)
              if re.search(r'(?m)^\s*References\s*$', page)]
    require(len(starts) == 1 and 1 <= starts[0] <= 8, 'Main-page ceiling differs')
    return starts[0]


def verify_artifacts(root, verify_admission, main_result):
    root = Path(root).resolve()
    before = verify_admission(root)
    require(main_result.get('valid') is True
            and main_result.get('canonical_commit') == before['canonical_commit']
            and main_result.get('disclosure_manifest_sha256') == before['disclosure_manifest_sha256']
            and main_result.get('main_blocks') == 640
            and main_result.get('main_reader_terminals') == 53760,
            'Artifact checking requires the current successful MAIN reconstruction')
    files = before['files']
    paper = root / 'paper'
    for folder in (root, paper):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    verify = _module(root, 'verify', files)
    builder = _module(root, 'figure_build', files)
    contract = _module(root, 'complete_report_contract', files)
    figures = _module(root, 'analysis.ledger_complete_figures', files)
    from lxml import etree as E
    from pypdf import PdfReader
    content = json.loads((paper / 'content.json').read_text(encoding='utf-8'))
    report = json.loads((root / 'data/swarm-ledger-v1-public/report.json').read_text(encoding='utf-8'))
    require(verify.source_hash(report) == main_result['mathematical_report_sha256'],
            'MAIN report changed between mathematics and artifact checks')
    contract.validate_report(report)
    contract.validate_manuscript(content, report)
    verify.validate_source(content)
    require(_sha((paper / 'official-template.docx').read_bytes()) == verify.SHA,
            'Official template bytes differ')
    require(len(content['abstract'].split()) == 196, 'Submitted abstract length differs')
    docx = paper / 'out/swarm_audit_scoping.docx'
    pdf = paper / 'out/swarm_audit_scoping.pdf'
    require(_sha(docx.read_bytes()) == CANONICAL_DOCX
            and _sha(pdf.read_bytes()) == CANONICAL_PDF,
            'Submitted artifact bytes changed')
    expected = builder.assemble(content, paper / 'official-template.docx')
    compare_docx_parts(docx, expected)
    doc = E.fromstring(expected['word/document.xml'])
    paragraphs = [''.join(p.xpath('.//w:t/text()', namespaces=verify.NS))
                  for p in doc.xpath('//w:p', namespaces=verify.NS)]
    with zipfile.ZipFile(paper / 'official-template.docx') as archive:
        notes = E.fromstring(archive.read('word/footnotes.xml'))
    note_texts = [verify.compact(''.join(n.xpath('.//w:t/text()', namespaces=verify.NS)))
                  for n in notes]
    note_texts = [t for t in note_texts if t]
    require(pdf.stat().st_size <= 25_000_000, 'PDF exceeds the submission size bound')
    reader = PdfReader(pdf)
    require(not reader.is_encrypted, 'PDF requires a password')
    pages = [page.extract_text() or '' for page in reader.pages]
    main_pages = verify_text_order(pages, paragraphs, content['title'], note_texts, verify.compact)
    require(len(pages) == 16 and main_pages == 8, 'Submitted page inventory differs')
    for page in reader.pages:
        require(abs(float(page.mediabox.width) - 612) < 1
                and abs(float(page.mediabox.height) - 792) < 1,
                'Official-template PDF geometry differs')
    visual = verify.figure_pdf_evidence(paper, content, reader, pdf)
    build_record = json.loads((paper / 'out/build-check.json').read_text(encoding='utf-8'))
    pdf_record = json.loads((paper / 'out/pdf-check.json').read_text(encoding='utf-8'))
    bindings = disclosed_source_bindings(root)
    preparation = dict(bindings, generator_sensitivity_report_sha256=_sha(
        (root / 'data/swarm-ledger-generator-sensitivity-v1/report.json').read_bytes()))
    require(content['preparation_bindings'] == preparation,
            'Disclosed manuscript preparation bindings differ')
    for record in (build_record, pdf_record):
        require(record['abstract_words'] == 196
                and record['template_sha256'] == verify.SHA
                and record['content_sha256'] == verify.source_hash(content)
                and record['builder_sha256'] == verify.builder_hash(paper)
                and record['docx_sha256'] == CANONICAL_DOCX
                and record['complete_report_contract_sha256'] == _normalized_sha(paper / 'complete_report_contract.py')
                and record['ledger_layout_sha256'] == _normalized_sha(paper / 'ledger_layout.py')
                and record['figure_builder_sha256'] == _normalized_sha(paper / 'figure_build.py')
                and record['ledger_sources'] == bindings
                and record['evidence_status'] == content['evidence_status'],
                'Disclosed paper artifact commitments differ')
    require(pdf_record['pdf_sha256'] == CANONICAL_PDF
            and pdf_record['pages'] == 16 and pdf_record['main_pages'] == 8
            and pdf_record['pdf_bytes'] == pdf.stat().st_size
            and all(pdf_record[key] == value for key, value in visual.items()),
            'PDF review/painting commitments differ')
    require(build_record['figures'] == builder.figure_manifest(content, paper),
            'Scientific figure registry differs')
    delta = builder.package_delta(expected, paper / 'official-template.docx')
    require(all(build_record[key] == value for key, value in delta.items())
            and build_record['figure_verifier_sha256'] == _normalized_sha(paper / 'verify.py')
            and pdf_record['figures'] == {value['id']: value['sha256'] for value in content['figures']},
            'Template package or figure verifier commitment differs')
    directory = root / 'data/swarm-ledger-v1-public'
    receipt = root / 'research/paper-public-figure-input.json'
    figure_dir = paper / 'figures/swarm-ledger-complete-v1'
    figure_provenance = figures.verify_only(directory, receipt, figure_dir)
    cases, figure_report = figures.load_cases(directory, receipt)
    require(figure_report == report, 'Figures reference a different MAIN report')
    composition = figures.composition(cases)
    acquisition = figures.acquisition(cases)
    effects = figures.procedure_effects(report)
    require(len(composition) == 12 and len(effects) == 6
            and acquisition['n'] == 1280 and acquisition['blocks'] == 640,
            'Figure scientific population differs')
    after = verify_admission(root)
    require(after == before, 'Disclosure changed during artifact checking')
    for name, module in list(sys.modules.items()):
        if name.startswith(('experiments.', 'analysis.', 'paper.')) or name in {
            'verify', 'build', 'figure_build', 'ledger_layout', 'complete_report_contract',
        }:
            path = getattr(module, '__file__', None)
            if path:
                path = Path(path).resolve()
                require(path.is_relative_to(root) and path.relative_to(root).as_posix() in files,
                        'Unadmitted project module was loaded')
    return dict(valid=True, scope='snapshot paper/figure checking under explicit disclosed admission',
                private_original_protocol_admission=PRIVATE_ADMISSION,
                pdf_sha256=CANONICAL_PDF, docx_sha256=CANONICAL_DOCX,
                total_pages=16, main_pages=8, abstract_words=196,
                carried_forward_actual_all_page_review=True,
                figure_provenance=figure_provenance,
                figure_composition_groups=len(composition), figure_procedure_effects=len(effects))
