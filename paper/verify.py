"""Check committed artifacts without rebuilding. --record-pdf records a validated Word export."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unicodedata
import zipfile
from lxml import etree as E
from pypdf import PdfReader
from build import assemble, require, SHA, NS

ROOT=Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source_hash(content):
    return hashlib.sha256(json.dumps(content,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def builder_hash(root):
    return hashlib.sha256((root/'build.py').read_text(encoding='utf-8').replace('\r\n','\n').encode()).hexdigest()

def build_manifest(root,content):
    results=json.loads((root.parent/'research/pilot-results.json').read_text(encoding='utf-8'))
    manifest=dict(abstract_words=len(content['abstract'].split()),template_sha256=SHA,
                content_sha256=source_hash(content),builder_sha256=builder_hash(root),
                docx_sha256=sha(root/'out/swarm_audit_scoping.docx'),
                changed_package_parts=['word/document.xml'],evidence_status=content['evidence_status'],results_sha256=source_hash(results))
    if 'stateful_plan' in content:
        manifest['stateful_sources']={n:source_hash(json.loads((root.parent/'research'/n).read_text(encoding='utf-8'))) for n in ('stateful-config.json','stateful-freeze.json','stateful-qualification.json')}
    return manifest

def validate_results(root,content):
    report=json.loads((root.parent/'research/pilot-results.json').read_text(encoding='utf-8'))
    batch=report['batches']['pilot-development-v4']
    require(content['evidence_status']['fixed_batch_reader_calls']==batch['retained_responses'], 'Reported call count differs from aggregates')
    require(content['evidence_status']['retained_adaption_request_records']==sum(v['retained_responses'] for v in report['batches'].values())+report['influence']['calls'], 'Total retained record count differs')
    require(content['evidence_status']['hf_smoke_calls']==report['hugging_face_smoke']['calls'], 'HF count differs')
    for row,model in zip(content['table2'][1:3],content['table2_model_ids']):
        stats=batch['models'][model]
        expected=[str(stats['grounded_correct']),str(stats['supported_definite']),f"{stats['unsupported_executor']} / {stats['unsupported_none']} / {stats['invalid']}"]
        require(row[1:]==expected, 'Paper table differs from observed aggregates: '+model)
    if 'stateful_plan' in content:
        cfg=json.loads((root.parent/'research/stateful-config.json').read_text(encoding='utf-8'))
        q=json.loads((root.parent/'research/stateful-qualification.json').read_text(encoding='utf-8'))
        f=json.loads((root.parent/'research/stateful-freeze.json').read_text(encoding='utf-8'))
        n=len(cfg['stages']['main']['families'])*cfg['stages']['main']['episodes_per_family']
        require(content['stateful_plan']==dict(main_planned_episodes=n,main_planned_calls=n*10*len(cfg['models']),main_completed_calls=q['main_completed_calls'],qualification_calls=q['summary']['attempted_calls'],qualification_pass=q['summary']['qualification_pass'],freeze_tag=cfg['study_id']), 'Stateful plan/result mismatch')
        require(f['config']==cfg and q['main_completed_calls']==0, 'This report contract contains no main results')

def compact(value):
    value=unicodedata.normalize('NFKC',value).translate(str.maketrans({'\u00ad':'','−':'-','–':'-','—':'-','’':"'",'‘':"'",'“':'"','”':'"'}))
    return ''.join(value.split())

def validate_source(content):
    require(any('Limitations and Dual-Use / Ethical Considerations' in h for h,_ in content['appendix']), 'Required appendix missing')
    prose=' '.join(p for _,ps in content['sections']+content['appendix'] for p in ps)
    prose+=' '.join(cell for row in content['table1'] for cell in row)
    prose+=' '.join(cell for row in content.get('table2',[]) for cell in row)
    cited=set()
    for group in re.findall(r'\[([\d,–-]+)\]',prose):
        for item in group.split(','):
            ends=re.split('[–-]',item)
            cited.update(range(int(ends[0]),int(ends[-1])+1))
    ids=[int(re.match(r'\[(\d+)\]',r).group(1)) for r in content['references']]
    require(ids==list(range(1,len(ids)+1)), 'References must have unique sequential IDs')
    require(cited==set(ids), 'Citation/reference mismatch: '+str(cited.symmetric_difference(ids)))
    require(content['evidence_status']['confirmatory_episodes']==0, 'Confirmatory claim requires a separately reviewed report contract')
    require(content['evidence_status']['status']=='development pilot', 'Report evidence status must stay explicit')
    require('development' in content['abstract'].lower(), 'Development boundary missing from abstract')

def check_docx(root,content):
    expected=assemble(content,root/'official-template.docx')
    with zipfile.ZipFile(root/'out/swarm_audit_scoping.docx') as z:
        require(len(z.namelist())==len(set(z.namelist())), 'Duplicate DOCX package parts')
        require(set(z.namelist())==set(expected), 'DOCX package part set changed')
        for name,data in expected.items():
            require(z.read(name)==data, 'Stale or modified DOCX part: '+name)
        doc=E.fromstring(z.read('word/document.xml'))
    paragraphs=[''.join(p.xpath('.//w:t/text()',namespaces=NS)) for p in doc.xpath('//w:p',namespaces=NS)]
    manuscript=' '.join(paragraphs)
    for placeholder in ['PROJECT TITLE','Author name 1','How to use this template','[Reference 1]']:
        require(placeholder not in manuscript, 'Template placeholder remains: '+placeholder)
    require(not re.search(r'\b(?:TABLE|FIGURE)\d+\b',manuscript), 'Unresolved content marker')
    actual=json.loads((root/'out/build-check.json').read_text(encoding='utf-8'))
    require(actual==build_manifest(root,content), 'Stale build manifest')
    return paragraphs

def pdf_manifest(root,content,paragraphs):
    path=root/'out/swarm_audit_scoping.pdf'
    require(path.stat().st_size<=25_000_000, 'PDF exceeds 25 MB')
    reader=PdfReader(path)
    require(not reader.is_encrypted, 'PDF must be readable without a password')
    pages=[p.extract_text() or '' for p in reader.pages]
    all_text=compact('\n'.join(pages))
    for paragraph in paragraphs:
        if paragraph.strip():
            require(compact(paragraph) in all_text, 'PDF text missing/stale: '+paragraph[:90])
    # Substring checks alone miss removed prose still present in an old PDF.
    # The retained template has one title footnote, numbered 1 at rendering.
    with zipfile.ZipFile(root/'official-template.docx') as z:
        notes=E.fromstring(z.read('word/footnotes.xml'))
    note_texts=[compact(''.join(n.xpath('.//w:t/text()',namespaces=NS))) for n in notes]
    note_texts=[t for t in note_texts if t]
    require(len(note_texts)==1, 'Unexpected template footnote contract')
    title=compact(content['title'])
    require(all_text.count(title+'1')==1, 'Missing/changed PDF title footnote marker')
    note='1'+note_texts[0]
    require(all_text.count(note)==1, 'Missing/changed PDF event footnote')
    body_text=all_text.replace(title+'1',title,1).replace(note,'',1)
    require(body_text==compact(''.join(paragraphs)), 'PDF has extra/stale/reordered text')
    starts=[i for i,t in enumerate(pages) if re.search(r'(?m)^\s*References\s*$',t)]
    require(len(starts)==1, 'Cannot uniquely locate References page')
    main_pages=starts[0]
    require(1<=main_pages<=8, 'Main paper must be at most 8 pages')
    for page in reader.pages:
        require(abs(float(page.mediabox.width)-612)<1 and abs(float(page.mediabox.height)-792)<1, 'PDF page geometry differs from template')
    return dict(pages=len(pages),main_pages=main_pages,pdf_bytes=path.stat().st_size,
                abstract_words=len(content['abstract'].split()),render_engine='Microsoft Word',
                evidence_status=content['evidence_status'],template_sha256=SHA,content_sha256=source_hash(content),
                builder_sha256=builder_hash(root),docx_sha256=sha(root/'out/swarm_audit_scoping.docx'),pdf_sha256=sha(path))

def check_ignores(root):
    protected=['.env','.env.production','private.pem','private.key','id_rsa','id_ed25519','.modal.toml','runs/raw.json','nested/runs-test/raw.json','.swarm/state.json','.playwright-mcp/download.tmp']
    result=subprocess.run(['git','check-ignore','--no-index',*protected],cwd=root.parent,text=True,capture_output=True)
    require(result.returncode==0 and set(result.stdout.splitlines())==set(protected), 'Secret/raw-output exclusions failed')
    require(subprocess.run(['git','check-ignore','--no-index','.env.example'],cwd=root.parent,capture_output=True).returncode==1, 'Example environment must stay trackable')

def verify(root=ROOT,record_pdf=False,git_checks=True):
    content=json.loads((root/'content.json').read_text(encoding='utf-8'))
    validate_source(content)
    validate_results(root,content)
    paragraphs=check_docx(root,content)
    manifest=pdf_manifest(root,content,paragraphs)
    target=root/'out/pdf-check.json'
    if git_checks:
        check_ignores(root)
    if record_pdf:
        temporary=target.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
        temporary.replace(target)
    else:
        require(json.loads(target.read_text(encoding='utf-8'))==manifest, 'Stale PDF manifest')
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record-pdf',action='store_true')
    args=parser.parse_args()
    try:
        result=verify(record_pdf=args.record_pdf)
    except (ValueError,OSError,KeyError,zipfile.BadZipFile) as exc:
        raise SystemExit('FAIL: '+str(exc)) from exc
    print('PASS: current DOCX/PDF text, hashes, template, citations and exclusions; '+str(result['main_pages'])+' main pages')
