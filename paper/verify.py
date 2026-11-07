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
        manifest['stateful_sources']={n:source_hash(json.loads((root.parent/'research'/n).read_text(encoding='utf-8'))) for n in ('stateful-config.json','stateful-main-v2-freeze.json','stateful-qualification.json')}
    if content.get('table2_source')=='stateful':
        manifest['stateful_sources']={n:source_hash(json.loads((root.parent/'research'/n).read_text(encoding='utf-8'))) for n in ('stateful-config.json','stateful-main-v2-freeze.json','stateful-main-v2-continuation-v1-freeze.json','stateful-qualification.json','hf-stateful-config.json','stateful-hf-v3-freeze.json','stateful-results.json')}
    if content.get('table2_source')=='live':
        manifest['live_sources']={n:source_hash(json.loads((root.parent/'research'/n).read_text(encoding='utf-8'))) for n in ('live-config.json','live-audit-v2-freeze.json','live-audit-v2-continuation-v1-freeze.json','live-qualification-v1.json','live-results.json','weight-config.json','weight-audit-v1-freeze.json','weight-results.json','stateful-results.json')}
    if content.get('table2_source')=='factorial':
        manifest['factorial_sources']={n:source_hash(json.loads((root.parent/'research'/n).read_text(encoding='utf-8'))) for n in ('factorial-config.json','factorial-audit-v1-freeze.json','factorial-results.json','live-results.json','weight-results.json','stateful-results.json')}
    if content.get('table2_source')=='factorial_reporting':
        manifest['factorial_reporting_sources']={n:source_hash(json.loads((root.parent/'research'/n).read_text(encoding='utf-8'))) for n in ('factorial-config.json','factorial-audit-v1-freeze.json','factorial-reporting-freeze.json','factorial-report.json','ollama-reader-v1-freeze.json','live-results.json','weight-results.json','stateful-results.json')}
        manifest['factorial_reporting_contract_sha256']=hashlib.sha256((root/'factorial_report_contract.py').read_bytes().replace(b'\r\n',b'\n')).hexdigest()
    if content.get('figures'):
        from figure_build import assemble as figure_assemble, figure_manifest, package_delta
        parts=figure_assemble(content,root/'official-template.docx')
        manifest.update(package_delta(parts,root/'official-template.docx'))
        manifest['figures']=figure_manifest(content,root)
        manifest['figure_builder_sha256']=hashlib.sha256((root/'figure_build.py').read_bytes().replace(b'\r\n',b'\n')).hexdigest()
        manifest['figure_verifier_sha256']=hashlib.sha256((root/'verify.py').read_bytes().replace(b'\r\n',b'\n')).hexdigest()
    return manifest

def validate_results(root,content):
    if content.get('table2_source')=='factorial_reporting':
        from factorial_report_contract import expected_fields
        report=json.loads((root.parent/'research/factorial-report.json').read_text(encoding='utf-8'))
        require(report['status'] in ('primary_complete_secondary_incomplete','primary_complete_with_registered_extensions'), 'Amended report status missing')
        for key,value in expected_fields(report).items():
            require(content.get(key)==value,'Amended paper field differs from public report: '+key)
        return
    if content.get('table2_source')=='factorial':
        r=json.loads((root.parent/'research/factorial-results.json').read_text(encoding='utf-8'))
        a=r['analysis'];cfg=r['config'];ids=cfg['monitors'];sources=a['sources']
        require(r['status']=='complete' and cfg['study_id']=='factorial-audit-v1','Factorial report requires complete frozen records')
        expected=dict(status='completed factorial study',source_groups=sources,actor_calls=a['actor_calls'],main_audit_calls=a['main_audit_calls'],calibration_calls=a['calibration_calls'],training_runs=0,freeze='factorial-audit-v1')
        require(content['evidence_status']==expected,'Factorial evidence counts differ')
        require(sources==cfg['sources']==192 and a['actor_calls']==3*sources and a['main_audit_calls']==20*sources*len(ids),'Factorial source/call grid differs')
        require(content['table2_model_ids']==ids and len(ids)==3 and all(len(content[t])==4 for t in ('table1','table2','table3')),'Factorial table identity/size')
        require(all(len(row)==columns for t,columns in (('table1',3),('table2',4),('table3',3)) for row in content[t]),'Factorial table column count')
        def fx(e):return f"{100*e['estimate']:+.2f} [{100*e['ci95'][0]:+.2f}, {100*e['ci95'][1]:+.2f}]"
        expected_views={'sufficient','identity_loss'}|{loss+'_'+policy for loss in ('random','selective') for policy in ('none','random','metadata','contract')}
        names=dict(zip(ids,('Gemma 26B A4B','Gemma 31B','Llama 70B HF')))
        for i,model in enumerate(ids,1):
            s=a['models'][model];views=s['by_view'];suff=views['sufficient'];primary=s['primary_same_packet_procedure_minus_direct']
            require(set(views)==expected_views,'Factorial main views differ')
            require(primary['n']==sources,'Effect source denominator differs from public study')
            row=content['table1'][i]
            require(row==[f'{names[model]} ({sources})',f"{suff['direct']['raw']['supported_definite']}/{sources} / {suff['procedure']['raw']['supported_definite']}/{sources}",fx(primary)],'Primary same-packet table differs from public study')
            totals={proc:{k:sum(views[v][proc]['raw'][k] for v in expected_views) for k in ('calls','grounded_correct','unsupported_executor','unsupported_none','invalid')} for proc in ('direct','procedure')}
            direct,procedure=totals['direct'],totals['procedure'];calls=s['totals']['calls']
            require(calls==20*sources and direct['calls']==procedure['calls']==10*sources and all(views[v][proc]['raw']['calls']==sources for v in expected_views for proc in ('direct','procedure')),'Reader table differs from public call grid')
            row=content['table2'][i]
            require(row==[f'{names[model]} ({calls})',f"{direct['grounded_correct']} / {procedure['grounded_correct']}",f"D:{direct['unsupported_executor']}/{direct['unsupported_none']}; P:{procedure['unsupported_executor']}/{procedure['unsupported_none']}",f"{direct['invalid']} / {procedure['invalid']}"],'Reader table differs from public cases')
            effects=s['secondary_acquisition_grounded'];left=effects['metadata_minus_random'];right=effects['contract_minus_metadata']
            row=content['table3'][i]
            require(left['n']==right['n']==sources and row==[f'{names[model]} ({sources})',fx(left),fx(right)],'Effect source denominator/table differs from public study')
        return
    if content.get('table2_source')=='live':
        r=json.loads((root.parent/'research/live-results.json').read_text(encoding='utf-8'))
        w=json.loads((root.parent/'research/weight-results.json').read_text(encoding='utf-8'))
        a=r['analysis'];b=w['analysis'];ids=r['config']['monitors']
        require(r['status']==w['status']=='complete','Live/weight report requires complete records')
        amendment='live-audit-v2-continuation-v1'
        amendment_sha=hashlib.sha256((root.parent/'research'/str(amendment+'-freeze.json')).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
        require(r.get('operational_amendment')==dict(tag=amendment,freeze_sha256=amendment_sha),'Live continuation declaration missing or stale')
        expected=dict(status='completed live and weight study',live_source_clusters=a['main_source_clusters'],live_actor_calls=a['actor_calls'],live_audit_calls=a['main_audit_calls']+a['influence_audit_calls'],weight_writer_calls=b['planned_calls'],weight_variants=b['variants'],training_runs=0,live_freeze='live-audit-v2',weight_freeze='weight-audit-v1',live_operational_amendment=amendment)
        require(content['evidence_status']==expected,'Live/weight evidence counts differ')
        require(content['table2_model_ids']==ids and len(content['table2'])==4 and len(content['table1'])==4 and len(content['table3'])==4,'Live/weight table identity/size')
        def fx(e):return f"{100*e['estimate']:+.2f} [{100*e['ci95'][0]:+.2f}, {100*e['ci95'][1]:+.2f}]"
        def wf(e):return f"{e['successes']}/{e['n']} [{100*e['ci95'][0]:.1f}, {100*e['ci95'][1]:.1f}]"
        for i,model in enumerate(ids,1):
            s=a['model_totals'][model];row=content['table2'][i];n=re.search(r'\((\d+)\)$',row[0])
            require(row[1:]==[str(s['grounded_correct']),str(s['supported_definite']),f"{s['unsupported_executor']} / {s['unsupported_none']} / {s['invalid']}"] and n is not None and int(n.group(1))==s['calls'],'Reader table differs from public cases')
            e=a['effects'][model]['delegated'];row=content['table1'][i];n=re.search(r'\((\d+)\)$',row[0])
            require(row[1:]==[fx(e['restoration_grounded_metadata_minus_random']),fx(e['unsupported_selective_minus_random'])] and n is not None and int(n.group(1))==a['main_source_clusters'],'Effect source denominator/table differs from public study')
            row=content['table3'][i];n=re.search(r'\((\d+)\)$',row[0]);wr=b['model_results'][model]
            require(row[1:]==[wf(wr['repair']['exact']),wf(wr['synthesize']['exact'])] and n is not None and int(n.group(1))==b['variants'],'Weight variant denominator/table differs from public study')
        return
    if content.get('table2_source')=='stateful':
        r=json.loads((root.parent/'research/stateful-results.json').read_text(encoding='utf-8'))
        main,hf,inf=r['main'],r['hf'],r['influence']
        require(all(arm['status']=='complete' for arm in (main,hf,inf)), 'Completed report requires complete core/HF/influence records')
        expected=dict(status='completed stateful study',main_source_episodes=main['source_episodes'],main_reader_calls=main['returned_calls'],hf_source_episodes=hf['source_episodes'],hf_reader_calls=hf['returned_calls'],influence_calls=inf['returned_calls'],training_runs=0,operational_amendment='stateful-main-v2-continuation-v1')
        require(content['evidence_status']==expected, 'Evidence counts differ from public study')
        stats={**main['model_totals'],**hf['model_totals']}
        ids=r['config']['models']+[hf['configuration']['model']]
        require(content['table2_model_ids']==ids and len(content['table2'])==len(ids)+1, 'Reader table identity mismatch')
        for row,model in zip(content['table2'][1:],ids):
            s=stats[model]
            denominator=re.search(r'\((\d+)\)$',row[0])
            require(row[1:]==[str(s['grounded_correct']),str(s['supported_definite']),f"{s['unsupported_executor']} / {s['unsupported_none']} / {s['invalid']}"] and denominator is not None and int(denominator.group(1))==s['calls'], 'Reader table differs from public cases')
        def fx(e):return f"{100*e['estimate']:+.2f} [{100*e['ci95'][0]:+.2f}, {100*e['ci95'][1]:+.2f}]"
        require(len(content['table3'])==4, 'Paired effect table size')
        for row,model in zip(content['table3'][1:],ids):
            effects=main['analysis']['effects'][model] if model in r['config']['models'] else hf['paired_effects']
            key='primary_unsupported_targeted_minus_random' if model in r['config']['models'] else 'unsupported_targeted_minus_random'
            require(row[1:]==[fx(effects[key]),fx(effects['restoration_grounded_priority_minus_random'])], 'Effect table differs from frozen public analysis')
            source_n=main['source_episodes'] if model in r['config']['models'] else hf['source_episodes']
            denominator=re.search(r'\((\d+)\)$',row[0])
            require(denominator is not None and int(denominator.group(1))==source_n, 'Effect source denominator differs from public study')
        return
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
        f=json.loads((root.parent/'research/stateful-main-v2-freeze.json').read_text(encoding='utf-8'))
        n=len(cfg['stages']['main']['families'])*cfg['stages']['main']['episodes_per_family']
        require(content['stateful_plan']==dict(main_planned_episodes=n,main_planned_calls=n*10*len(cfg['models']),main_completed_calls=q['main_completed_calls'],qualification_calls=q['summary']['attempted_calls'],qualification_pass=q['summary']['qualification_pass'],freeze_tag=cfg['study_id']), 'Stateful plan/result mismatch')
        require(f['config']==cfg and q['main_completed_calls']==0, 'This report contract contains no main results')
        freeze_hash=hashlib.sha256((root.parent/'research/stateful-main-v2-freeze.json').read_bytes().replace(b'\r\n',b'\n')).hexdigest()
        require(q['freeze_sha256']==freeze_hash and q['summary']['freeze_sha256']==freeze_hash, 'Qualification belongs to another registration')

def compact(value):
    value=unicodedata.normalize('NFKC',value).translate(str.maketrans({'\u00ad':'','−':'-','–':'-','—':'-','’':"'",'‘':"'",'“':'"','”':'"'}))
    return ''.join(value.split())

def validate_source(content):
    require(any('Limitations and Dual-Use / Ethical Considerations' in h for h,_ in content['appendix']), 'Required appendix missing')
    prose=' '.join(p for _,ps in content['sections']+content['appendix'] for p in ps)
    prose+=' '.join(cell for row in content['table1'] for cell in row)
    prose+=' '.join(cell for row in content.get('table2',[]) for cell in row)
    prose+=' '.join(cell for row in content.get('table3',[]) for cell in row)
    if content.get('figures'):
        require(type(content['figures']) is list and all(type(v) is dict and type(v.get('caption')) is str for v in content['figures']),'Figure caption registry invalid')
        prose+=' '.join(v['caption'] for v in content['figures'])
    cited=set()
    for group in re.findall(r'\[([\d,–-]+)\]',prose):
        for item in group.split(','):
            ends=re.split('[–-]',item)
            cited.update(range(int(ends[0]),int(ends[-1])+1))
    ids=[int(re.match(r'\[(\d+)\]',r).group(1)) for r in content['references']]
    require(ids==list(range(1,len(ids)+1)), 'References must have unique sequential IDs')
    require(cited==set(ids), 'Citation/reference mismatch: '+str(cited.symmetric_difference(ids)))
    if content.get('table2_source') in ('stateful','live','factorial','factorial_reporting'):
        expected_status={'live':'completed live and weight study','stateful':'completed stateful study','factorial':'completed factorial study','factorial_reporting':'primary complete; original secondary incomplete'}[content['table2_source']]
        require(content['evidence_status']['status']==expected_status, 'Study evidence status must be explicit')
        require(all(s in content['abstract'] for s in ('Adaption','Hugging Face')), 'Service evidence missing from abstract')
        if content.get('table2_source')=='factorial_reporting':
            require('Ollama' in content['abstract'], 'Registered extension service missing from abstract')
    else:
        require(content['evidence_status']['confirmatory_episodes']==0, 'Confirmatory claim requires a separately reviewed report contract')
        require(content['evidence_status']['status']=='development pilot', 'Report evidence status must stay explicit')
        require('development' in content['abstract'].lower(), 'Development boundary missing from abstract')

def check_docx(root,content):
    if content.get('figures'):
        from figure_build import assemble as figure_assemble
        expected=figure_assemble(content,root/'official-template.docx')
    else:expected=assemble(content,root/'official-template.docx')
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

def painted_image_count(reader):
    """Count painted image XObjects, including images inside painted Form objects.

    Unused resources and empty image streams do not establish figure presence.
    Counts do not verify semantic identity; the hash-bound page review does that.
    """
    from pypdf.generic import ContentStream
    def obj(value):return value.get_object() if hasattr(value,'get_object') else value
    def count(stream,resources,ancestry=()):
        if stream is None:return 0
        stream=obj(stream);resources=obj(resources or {});total=0
        require(len(ancestry)<20,'Recursive PDF Form resources')
        for operands,operator in ContentStream(stream,reader).operations:
            if operator!=b'Do':continue
            require(len(operands)==1,'Invalid PDF image operation')
            xobjects=obj(resources.get('/XObject',{}));name=operands[0]
            require(name in xobjects,'Missing painted PDF XObject')
            x=obj(xobjects[name]);subtype=x.get('/Subtype')
            if subtype=='/Image':
                require(int(x.get('/Width',0))>0 and int(x.get('/Height',0))>0 and len(x.get_data())>0,'Empty PDF image')
                total+=1
            elif subtype=='/Form':
                identity=id(x);require(identity not in ancestry,'Cyclic PDF Form resources')
                total+=count(x,x.get('/Resources',resources),ancestry+(identity,))
        return total
    return [count(page.get_contents(),page.get('/Resources',{})) for page in reader.pages]


def figure_pdf_evidence(root,content,reader,path):
    from figure_build import figure_manifest
    figures=figure_manifest(content,root)
    counts=painted_image_count(reader)
    require(sum(counts)>=len(figures),'PDF missing painted scientific figure images')
    review_path=root/'out/figure-review.json'
    require(review_path.is_file(),'All-page scientific figure inspection record required')
    review=json.loads(review_path.read_text(encoding='utf-8'))
    require(set(review)=={'schema_version','pdf_sha256','figure_sha256','rendered_pages','inspected_all_pages','reviewer','reviewed_at'},'Figure inspection record schema')
    require(type(review['schema_version']) is int and review['schema_version']==1 and review['pdf_sha256']==sha(path)
            and review['figure_sha256']=={f['id']:f['sha256'] for f in figures},'Figure inspection record stale')
    require(review['inspected_all_pages'] is True and review['rendered_pages']==list(range(1,len(reader.pages)+1))
            and all(type(v) is int for v in review['rendered_pages']),'Every rendered page must be inspected')
    require(type(review['reviewer']) is str and review['reviewer'].strip() and type(review['reviewed_at']) is str and review['reviewed_at'].strip(),'Figure inspection attribution required')
    return dict(painted_images_by_page=counts,figure_review_sha256=sha(review_path),
                figure_identity_limit='Image objects establish presence; Word recompression prevents a general pixel-identity guarantee. All pages require visual inspection.')


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
    manifest=dict(pages=len(pages),main_pages=main_pages,pdf_bytes=path.stat().st_size,
                abstract_words=len(content['abstract'].split()),render_engine='Microsoft Word',
                evidence_status=content['evidence_status'],template_sha256=SHA,content_sha256=source_hash(content),
                builder_sha256=builder_hash(root),docx_sha256=sha(root/'out/swarm_audit_scoping.docx'),pdf_sha256=sha(path))
    if content.get('figures'):
        manifest.update(figure_pdf_evidence(root,content,reader,path))
        manifest['figure_builder_sha256']=hashlib.sha256((root/'figure_build.py').read_bytes().replace(b'\r\n',b'\n')).hexdigest()
        manifest['figures']={v['id']:v['sha256'] for v in content['figures']}
    return manifest

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
