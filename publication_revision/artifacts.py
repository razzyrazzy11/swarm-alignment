"""Check revised paper bytes and fresh actual page-review evidence."""
from __future__ import annotations

from datetime import datetime, timezone
import importlib
import json
from pathlib import Path
import sys
import zipfile

from .verify import QA, SCOPE, hash_value, outside_working_directory, require, sha, strict_json

EDITIONS = {
    'current': ('paper/content.json', 'paper/out/swarm_audit_scoping.docx', 'paper/out/swarm_audit_scoping.pdf'),
    'fixture': ('paper/tests/fixtures/results-v3/content.json',
                'paper/tests/fixtures/results-v3/out/swarm_audit_scoping.docx',
                'paper/tests/fixtures/results-v3/out/swarm_audit_scoping.pdf'),
}
EDITION_KEYS = {'content', 'content_sha256', 'docx', 'docx_sha256', 'pdf', 'pdf_sha256',
                'builder_sha256', 'export_engine', 'export_source_unchanged',
                'export_owned_instance_verified', 'pages', 'main_pages', 'abstract_words',
                'rendered_page_sha256', 'visual_review'}
BUILD_KEYS = {'schema_version', 'kind', 'content_sha256', 'builder_sha256', 'template_sha256',
              'docx_sha256', 'references', 'abstract_words', 'qa_path'}


def validate_qa_record(record, paths):
    require(type(record) is dict and set(record) == EDITION_KEYS, 'Fresh edition QA schema differs')
    require(tuple(record[name] for name in ('content', 'docx', 'pdf')) == paths,
            'Edition QA paths differ')
    require(all(hash_value(record[name]) for name in
                ('content_sha256', 'docx_sha256', 'pdf_sha256', 'builder_sha256')),
            'Edition QA digests differ')
    require(record['export_engine'] == 'Microsoft Word'
            and record['export_source_unchanged'] is True
            and record['export_owned_instance_verified'] is True,
            'Fresh owned native export evidence required')
    require(type(record['pages']) is int and 1 <= record['pages'] <= 100
            and type(record['main_pages']) is int and 1 <= record['main_pages'] <= 8
            and type(record['abstract_words']) is int and 150 <= record['abstract_words'] <= 250,
            'Edition page or abstract bound differs')
    rendered = record['rendered_page_sha256']
    require(type(rendered) is list and len(rendered) == record['pages']
            and all(hash_value(value) for value in rendered), 'Every actual page must be rendered')
    visual = record['visual_review']
    require(type(visual) is dict and set(visual) == {
        'complete', 'reviewer', 'reviewed_at_utc', 'inspected_pages'}, 'Visual review schema differs')
    require(visual['complete'] is True and type(visual['reviewer']) is str and bool(visual['reviewer'].strip())
            and visual['inspected_pages'] == list(range(1, record['pages'] + 1))
            and all(type(page) is int for page in visual['inspected_pages']),
            'Actual inspection of every new PDF page is required')
    require(type(visual['reviewed_at_utc']) is str, 'Visual review time must be explicit')
    try:
        stamp = datetime.fromisoformat(visual['reviewed_at_utc'])
    except ValueError:
        require(False, 'Visual review chronology differs')
    require(stamp.tzinfo is not None and stamp.utcoffset().total_seconds() == 0
            and stamp <= datetime.now(timezone.utc), 'Visual review chronology differs')


def _module(root, name, files):
    module = importlib.import_module(name)
    path = Path(module.__file__).resolve()
    require(path.is_relative_to(root) and path.relative_to(root).as_posix() in files,
            'Paper helper is outside the admitted revision')
    return module


def legacy_fixture_records(root, files, verify, content, paragraphs):
    """Use frozen record builders in their documented temporary fixture layout.

    Only admitted bytes enter an owned temporary directory outside the revision.
    No source module is imported from that directory and no registration wrapper
    is called. This mirrors the preserved integrity test's path layout.
    """
    require(content.get('table2_source') == 'factorial_reporting'
            and not content.get('ledger_registration') and not content.get('figures'),
            'Unexpected historical fixture record branch')
    research = ('pilot-results.json', 'factorial-config.json', 'factorial-audit-v1-freeze.json',
                'factorial-reporting-freeze.json', 'factorial-report.json', 'ollama-reader-v1-freeze.json',
                'live-results.json', 'weight-results.json', 'stateful-results.json')
    with outside_working_directory(root) as owned:
        paper = owned / 'paper'
        (paper / 'out').mkdir(parents=True)
        (owned / 'research').mkdir()
        mapping = {
            'paper/content.json': EDITIONS['fixture'][0],
            'paper/out/swarm_audit_scoping.docx': EDITIONS['fixture'][1],
            'paper/out/swarm_audit_scoping.pdf': EDITIONS['fixture'][2],
        }
        for name in ('official-template.docx', 'build.py', 'verify.py', 'factorial_report_contract.py'):
            mapping['paper/' + name] = 'paper/' + name
        for name in research:
            mapping['research/' + name] = 'research/' + name
        for target, source in mapping.items():
            require(source in files, 'Temporary fixture dependency is not admitted')
            raw = (root / source).read_bytes()
            require(sha(raw) == files[source], 'Temporary fixture input changed')
            (owned / target).write_bytes(raw)
        return verify.build_manifest(paper, content), verify.pdf_manifest(paper, content, paragraphs)


def verify_artifacts(root, verify_admission, main_result):
    root = Path(root).resolve()
    before = verify_admission(root)
    require(main_result.get('valid') is True
            and main_result.get('canonical_commit') == before['canonical_commit']
            and main_result.get('disclosure_manifest_sha256') == before['disclosure_manifest_sha256'],
            'Current successful scientific reconstruction is required')
    files = before['files']
    for directory in (root, root / 'paper'):
        if str(directory) not in sys.path:
            sys.path.insert(0, str(directory))
    from public_snapshot_v3.artifacts import compare_docx_parts, disclosed_source_bindings, verify_text_order
    from lxml import etree as E
    from pypdf import PdfReader
    verify = _module(root, 'verify', files)
    contract = _module(root, 'complete_report_contract', files)
    report_raw = (root / 'data/swarm-ledger-v1-public/report.json').read_bytes()
    report = json.loads(report_raw)
    require(verify.source_hash(report) == main_result['mathematical_report_sha256'],
            'Scientific report changed before paper checking')
    qa_raw = (root / QA).read_bytes()
    qa = strict_json(qa_raw)
    require(type(qa) is dict and set(qa) == {'schema_version', 'kind', 'editions'}
            and type(qa['schema_version']) is int and qa['schema_version'] == 1
            and qa['kind'] == 'publication_editorial_revision_qa_v1'
            and type(qa['editions']) is dict and set(qa['editions']) == set(EDITIONS),
            'New two-edition QA authority is required')
    template = root / 'paper/official-template.docx'
    template_hash = sha(template.read_bytes())
    require(template_hash == verify.SHA, 'Official template bytes differ')
    with zipfile.ZipFile(template) as archive:
        footnotes = E.fromstring(archive.read('word/footnotes.xml'))
    note_texts = [verify.compact(''.join(note.xpath('.//w:t/text()', namespaces=verify.NS))) for note in footnotes]
    note_texts = [value for value in note_texts if value]
    results = {}
    for edition, paths in EDITIONS.items():
        record = qa['editions'][edition]
        validate_qa_record(record, paths)
        content_raw, docx_raw, pdf_raw = ((root / path).read_bytes() for path in paths)
        require(all(sha(raw) == record[key] for raw, key in
                    ((content_raw, 'content_sha256'), (docx_raw, 'docx_sha256'), (pdf_raw, 'pdf_sha256'))),
                'Fresh QA does not bind actual revised bytes')
        content = strict_json(content_raw)
        verify.validate_source(content)
        if edition == 'current':
            contract.validate_report(report)
            contract.validate_manuscript(content, report)
            bindings = disclosed_source_bindings(root)
            preparation = dict(bindings, generator_sensitivity_report_sha256=sha(
                (root / 'data/swarm-ledger-generator-sensitivity-v1/report.json').read_bytes()))
            require(content['preparation_bindings'] == preparation,
                    'Preserved scientific input and ancestry commitments differ')
        else:
            old_contract = _module(root, 'factorial_report_contract', files)
            old_report = json.loads((root / 'research/factorial-report.json').read_bytes())
            for key, value in old_contract.expected_fields(old_report).items():
                require(content.get(key) == value, 'Historical fixture scientific field differs')
        builder_name = 'figure_build' if content.get('figures') else 'build'
        builder = _module(root, builder_name, files)
        builder_hash = sha((root / 'paper' / (builder_name + '.py')).read_bytes().replace(b'\r\n', b'\n'))
        require(builder_hash == record['builder_sha256'], 'Actual paper builder identity differs')
        expected = builder.assemble(content, template)
        compare_docx_parts(root / paths[1], expected)
        doc = E.fromstring(expected['word/document.xml'])
        paragraphs = [''.join(node.xpath('.//w:t/text()', namespaces=verify.NS))
                      for node in doc.xpath('//w:p', namespaces=verify.NS)]
        pdf_path = root / paths[2]
        require(len(pdf_raw) <= 25_000_000, 'PDF size exceeds the submission bound')
        reader = PdfReader(pdf_path)
        require(not reader.is_encrypted, 'Revised PDF requires a password')
        pages = [page.extract_text() or '' for page in reader.pages]
        main_pages = verify_text_order(pages, paragraphs, content['title'], note_texts, verify.compact)
        require(len(pages) == record['pages'] and main_pages == record['main_pages']
                and len(content['abstract'].split()) == record['abstract_words'],
                'New paper counts differ from actual PDF/source')
        for page in reader.pages:
            require(abs(float(page.mediabox.width) - 612) < 1 and abs(float(page.mediabox.height) - 792) < 1,
                    'Official-template PDF page geometry differs')
        if content.get('figures'):
            verify.figure_pdf_evidence(root / 'paper', content, reader, pdf_path)
        base = (root / paths[1]).parent
        core = dict(schema_version=1, content_sha256=sha(content_raw), builder_sha256=builder_hash,
                    template_sha256=template_hash, docx_sha256=sha(docx_raw),
                    references=len(content['references']), abstract_words=record['abstract_words'], qa_path=QA)
        build_record = strict_json((base / 'build-check.json').read_bytes())
        pdf_record = strict_json((base / 'pdf-check.json').read_bytes())
        if edition == 'current':
            require(set(build_record) == BUILD_KEYS and build_record == dict(
                core, kind='publication_editorial_revision_build_v1'), 'Current build identity record differs')
            require(set(pdf_record) == BUILD_KEYS | {'pdf_sha256', 'pages', 'main_pages'}
                    and pdf_record == dict(core, kind='publication_editorial_revision_pdf_v1',
                                           pdf_sha256=sha(pdf_raw), pages=len(pages), main_pages=main_pages),
                    'Current PDF identity record differs')
        else:
            legacy_build, legacy_pdf = legacy_fixture_records(root, files, verify, content, paragraphs)
            require(build_record == legacy_build and pdf_record == legacy_pdf,
                    'Preserved legacy fixture record contract differs')
        results[edition] = dict(valid=True, pages=len(pages), main_pages=main_pages,
                                abstract_words=record['abstract_words'], fresh_all_page_review=True)
    figures = _module(root, 'analysis.ledger_complete_figures', files)
    directory = root / 'data/swarm-ledger-v1-public'
    figure_receipt = root / 'research/paper-public-figure-input.json'
    figure_directory = root / 'paper/figures/swarm-ledger-complete-v1'
    figure_provenance = figures.verify_only(directory, figure_receipt, figure_directory)
    cases, figure_report = figures.load_cases(directory, figure_receipt)
    require(figure_report == report, 'Figures refer to a different reconstructed report')
    composition = figures.composition(cases)
    acquisition = figures.acquisition(cases)
    effects = figures.procedure_effects(report)
    require(len(composition) == 12 and len(effects) == 6
            and acquisition['n'] == 1280 and acquisition['blocks'] == 640,
            'Scientific figure population differs')
    require(qa_raw == (root / QA).read_bytes() and verify_admission(root) == before,
            'Revision changed during artifact verification')
    return dict(valid=True, scope=SCOPE, artifacts=results, figure_provenance=figure_provenance,
                figure_composition_groups=len(composition), figure_procedure_effects=len(effects),
                scientific_bindings='unchanged_data_and_preserved_frozen_ancestry_not_new_protocol_admission',
                parent_artifact_review='historical_not_reused_for_revised_bytes')
