"""Pre-reader secondary support-domain sensitivity; no inference or primary rescoring.

Import and public registration verification read no credentials or model answers.
"""
import argparse
from collections import defaultdict
from datetime import datetime,timezone
from functools import lru_cache
import hashlib,json,subprocess
from pathlib import Path
from experiments import swarm_ledger as engine
from experiments import swarm_ledger_complete as study
from experiments import swarm_ledger_complete_analysis as analysis

ROOT=study.ROOT
REGISTRATION=ROOT/'research/generator-sensitivity-v1-freeze.json'
TAG='generator-sensitivity-v1'
SOURCES=('analysis/ledger_generator_sensitivity.py','analysis/test_ledger_generator_sensitivity.py','research/SWARM_LEDGER_GENERATOR_SENSITIVITY_PROTOCOL.md')
VIEWS=('full','receipt_only7','random_loss','selective_loss','selective_random2','selective_metadata2','selective_contract2')
RULE='public-budget structural generator domain v1; no private arm/policy/profile conditioning'
expect=study.expect

def structural_pairs(public):
    budget=public.get('budget')
    expect(type(budget) is int and budget in (2,3,4),'Unknown structural-generator budget')
    expect(engine.valid_public(public),'Invalid public policy')
    end=public['lease_end']
    return ((end-1,False),) if budget in (2,3) else ((end-1,False),(end,False),(end-1,True))

def structural_contains(public,world):
    allowed=structural_pairs(public)
    return engine.valid_world(public,world) and (world['time_y'],world['revoked']) in allowed

@lru_cache(maxsize=8192)
def _domain_labels(encoded):
    packet=json.loads(encoded);engine.validate(packet);allowed=structural_pairs(packet['public'])
    worlds=engine.compatible_worlds(packet)
    nominal=frozenset(row['label'] for row in worlds)
    narrow=frozenset(row['label'] for row in worlds if (row['world']['time_y'],row['world']['revoked']) in allowed)
    expect(narrow<=nominal,'Narrow support escaped nominal support')
    return nominal,narrow

def domain_labels(packet):
    """Read only the exact packet; note text never creates authority."""
    return _domain_labels(engine.canonical(packet))

def packet_result(source,view,packet):
    expect(view in VIEWS,'Unregistered sensitivity view')
    p=source['public'];w=source['world']
    expect(structural_contains(p,w),'Actual world outside structural generator domain')
    expect(packet['public']==p,'Packet/public policy mismatch');engine.validate(packet)
    expected={r['id']:r for r in engine.records(p,w)}
    expect(all(expected.get(r['id'])==r for r in packet['records']),'Packet evidence differs from actual world')
    nominal,narrow=domain_labels(packet);truth=engine.simulate(p,w)['label']
    expect(nominal and narrow and truth in narrow,'Actual label excluded by narrowed evidence')
    if view in ('full','receipt_only7'):expect(len(nominal)==len(narrow)==1,'Sufficient evidence changed under narrowing')
    expect(len(narrow)!=1 or next(iter(narrow))==truth,'New singleton contradicts actual truth')
    return dict(source_id=source['source_id'],block_id=source['block_id'],arm=source['arm'],view=view,budget=p['budget'],
        packet_sha256=study.digest(packet),nominal_labels=sorted(nominal),structural_labels=sorted(narrow),actual_label=truth,
        nominal_answerable=len(nominal)==1,structural_answerable=len(narrow)==1,
        newly_answerable=len(nominal)>1 and len(narrow)==1,label_set_changed=nominal!=narrow)

def supported(prediction,labels):
    return prediction==(next(iter(labels)) if len(labels)==1 else 'ABSTAIN')

def summarize(artifacts):
    """Unique matched packets; same recorded verdicts are secondary descriptive rows."""
    sources=artifacts['worlds'];expect(len(sources)==2560 and len({s['source_id'] for s in sources})==2560,'Registered source inventory differs')
    expect(all(structural_contains(s['public'],s['world']) for s in sources),'MAIN world outside declared structural domain')
    selected=[s for s in sources if s['arm'] in ('honest','both')]
    expect(len(selected)==1280 and len({s['block_id'] for s in selected})==640,'Matched source/block inventory differs')
    packets=[];lookup={}
    for source in selected:
        generated={('receipt_only7' if v['view']=='sufficient' else v['view']):v['packet'] for v in engine.views(source['public'],source['world'])}
        expect(set(generated)==set(VIEWS),'Evidence-view inventory differs')
        for view in VIEWS:
            result=packet_result(source,view,generated[view]);key=(source['source_id'],view)
            expect(key not in lookup,'Duplicate matching packet');lookup[key]=result;packets.append(result)
    expect(len(packets)==8960,'Unique packet denominator differs')
    groups=defaultdict(list)
    for row in packets:groups[row['view']].append(row)
    finite={view:dict(packets=len(rows),nominal_answerable=sum(r['nominal_answerable'] for r in rows),
        structural_answerable=sum(r['structural_answerable'] for r in rows),newly_answerable=sum(r['newly_answerable'] for r in rows),
        label_set_changed=sum(r['label_set_changed'] for r in rows)) for view,rows in groups.items()}
    verdicts=[];seen=set();secondary=defaultdict(lambda:dict(n=0,nominal_supported_correct=0,structural_supported_correct=0,actual_truth_agreement=0))
    for profile in study.config()['reader_profiles']:
        for case in artifacts['cases:'+profile]:
            key=(case['source_id'],case['view'])
            if key not in lookup:continue
            expect(case['id'] not in seen,'Duplicate recorded verdict');seen.add(case['id']);packet=lookup[key]
            expect(case['packet_sha256']==packet['packet_sha256'] and case['actual_label']==packet['actual_label'],'Recorded verdict packet/truth drift')
            nominal=set(packet['nominal_labels']);narrow=set(packet['structural_labels']);pred=case['raw_label']
            nominal_correct=supported(pred,nominal);narrow_correct=supported(pred,narrow)
            expect(nominal_correct==case['correct_supported'],'Frozen nominal supported score differs')
            row=dict(id=case['id'],source_id=case['source_id'],view=case['view'],profile_id=profile,procedure=case['procedure'],
                raw_label=pred,nominal_supported_correct=nominal_correct,structural_supported_correct=narrow_correct,
                actual_truth_agreement=pred==packet['actual_label'])
            verdicts.append(row);group=secondary[(profile,case['view'],case['procedure'])];group['n']+=1
            for name in ('nominal_supported_correct','structural_supported_correct','actual_truth_agreement'):group[name]+=row[name]
    expect(len(verdicts)==38400,'Matched secondary recorded-verdict denominator differs')
    return dict(schema_version=1,scope='Secondary finite-cohort generator-knowledge sensitivity; original primary/report unchanged',
        structural_domain_rule=RULE,matched_blocks=640,matched_sources=1280,unique_packets=8960,views=finite,
        recorded_verdict_rows=38400,secondary_verdict_counts={':'.join(key):value for key,value in sorted(secondary.items())},
        uncertainty='Finite-cohort counts only; no superpopulation confidence intervals or revised primary claim.'),packets,verdicts

def pre_reader_gate():
    out=ROOT/('runs/'+study.config()['study_id']+'-main')
    for phase in ('readers','calibration'):
        path=out/phase/'attempts.jsonl'
        expect(not path.exists() or path.stat().st_size==0,'MAIN reader/calibration requests already started')
    actors=any((out/phase/'attempts.jsonl').exists() and (out/phase/'attempts.jsonl').stat().st_size>0 for phase in ('principal','coordinator','x','y','reporter'))
    return {'main_reader_attempts':0,'main_calibration_attempts':0,'actor_collection_already_started':actors,'outcomes_inspected':False}

def freeze():
    expect(not REGISTRATION.exists(),'Sensitivity registration exists');gate=pre_reader_gate();main=study.registration('main')
    for name in SOURCES:
        blob=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)
        expect(blob.replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),'Commit sensitivity sources first')
    value=dict(schema_version=1,tag=TAG,created=study.now(),domain_rule=RULE,source_sha256={p:study.sha(ROOT/p) for p in SOURCES},
        scientific_main_registration_sha256=study.sha(study.freeze_path('main')),scientific_source_sha256=main['source_sha256'],
        contexts_sha256=main['contexts_sha256'],pre_reader_gate=gate,
        base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    # Recheck immediately before writing, while actor collection is permitted.
    again=pre_reader_gate();expect(again['actor_collection_already_started']==gate['actor_collection_already_started'],'Actor start changed during sensitivity registration')
    with REGISTRATION.open('x',encoding='utf-8',newline='\n') as file:json.dump(value,file,indent=2);file.write('\n')
    return dict(created=True,tag=TAG)

def verify():
    value=study.read(REGISTRATION);main=study.registration('main')
    expect(set(value)=={'schema_version','tag','created','domain_rule','source_sha256','scientific_main_registration_sha256','scientific_source_sha256','contexts_sha256','pre_reader_gate','base_commit'},'Sensitivity registration fields differ')
    expect(type(value['schema_version']) is int and value['schema_version']==1 and value['tag']==TAG and value['domain_rule']==RULE,'Sensitivity domain identity differs')
    expect(value['source_sha256']=={p:study.sha(ROOT/p) for p in SOURCES},'Sensitivity source changed')
    expect(value['scientific_main_registration_sha256']==study.sha(study.freeze_path('main')) and value['scientific_source_sha256']==main['source_sha256'] and value['contexts_sha256']==main['contexts_sha256'],'Frozen science/context anchor changed')
    gate=value['pre_reader_gate'];expect(set(gate)=={'main_reader_attempts','main_calibration_attempts','actor_collection_already_started','outcomes_inspected'} and type(gate['main_reader_attempts']) is int and type(gate['main_calibration_attempts']) is int and gate['main_reader_attempts']==gate['main_calibration_attempts']==0 and gate['outcomes_inspected'] is False and type(gate['actor_collection_already_started']) is bool,'Pre-reader declaration differs')
    stamp=datetime.fromisoformat(value['created']);expect(stamp.tzinfo is not None,'Registration timestamp must be aware')
    for name in (*SOURCES,str(REGISTRATION.relative_to(ROOT)).replace('\\','/')):
        blob=subprocess.check_output(['git','show',TAG+':'+name],cwd=ROOT)
        expect(blob.replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),'Sensitivity tag content differs')
    expect(subprocess.run(['git','merge-base','--is-ancestor',value['base_commit'],TAG+'^{}'],cwd=ROOT,capture_output=True).returncode==0,'Sensitivity registration ancestry differs')
    return value

def raw_inventory(directory):
    directory=Path(directory);expect(directory.is_dir() and not directory.is_symlink(),'Input directory invalid')
    expect(all(p.is_file() and not p.is_symlink() for p in directory.iterdir()),'Input must contain regular verified files only')
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.iterdir())}

def export(input_directory,output_directory):
    registration=verify();source=Path(input_directory).resolve();target=Path(output_directory).resolve()
    expect(target.is_relative_to(ROOT.resolve()) and not target.exists() and not target.is_relative_to(source),'Use a new output outside the strict public directory')
    before=raw_inventory(source)
    # Literal frozen verifier, once; never clone or weaken its checks.
    checked=analysis.verify_public(source);expect(checked.get('valid') is True,'Public dataset did not verify')
    artifacts,original_report,manifest=analysis.load_public_artifacts(source)
    report,packets,verdicts=summarize(artifacts)
    expect(raw_inventory(source)==before,'Input artifacts changed during sensitivity analysis')
    verify();report.update(created=study.now(),registration_sha256=study.sha(REGISTRATION),input_files_raw_sha256=before,
        input_manifest_raw_sha256=before['manifest.json'],input_report_raw_sha256=before['report.json'],input_verification=checked,
        original_primary_unchanged=True,original_primary_commitment=study.digest(original_report['primary']),
        provenance_limit=manifest['provenance_limit'])
    target.mkdir(parents=True)
    for name,values in (('packets.jsonl',packets),('verdicts.jsonl',verdicts)):
        with (target/name).open('x',encoding='utf-8',newline='\n') as file:
            for row in values:file.write(study.canonical(row)+'\n')
    (target/'registration.json').write_text(json.dumps(registration,indent=2)+'\n',encoding='utf-8',newline='\n')
    report['derived_files_raw_sha256']={name:hashlib.sha256((target/name).read_bytes()).hexdigest() for name in ('packets.jsonl','verdicts.jsonl','registration.json')}
    (target/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    expect(raw_inventory(source)==before,'Original report/dataset changed during export')
    return dict(exported=True,unique_packets=8960,matched_sources=1280,original_primary_unchanged=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=('freeze','verify','export'));parser.add_argument('--input',type=Path);parser.add_argument('--output',type=Path);args=parser.parse_args()
    if args.command=='export':expect(args.input is not None and args.output is not None,'Input/output paths required');result=export(args.input,args.output)
    else:result=freeze() if args.command=='freeze' else {'valid':bool(verify())}
    print(study.canonical(result))

if __name__=='__main__':main()
