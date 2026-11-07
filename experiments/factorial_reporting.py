"""Registered sibling report: complete original primary, explicit missing readers.

Import and registration verification do not inspect scientific outcomes. Actual
export requires the reporting tag, stopped collectors and an explicit flag.
"""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import importlib
import json
import math
from pathlib import Path
import random
import subprocess

from experiments import factorial_analysis as f
from experiments import factorial_study as s
from experiments import factorial_continue as continuation
from experiments.live_study import config as live_config

ROOT=f.ROOT
FREEZE=ROOT/'research/factorial-reporting-freeze.json'
REPORT=ROOT/'research/factorial-report.json'
TAG='factorial-reporting-v1'
CHECKPOINT='research/factorial-rate-stop.json'
FILES=('data/factorial_contexts.json','data/factorial_report_actors.jsonl',
       'data/factorial_report_trajectories.json','data/factorial_report_cases.jsonl',
       'data/factorial_report_manifest.json')
SOURCES=('experiments/factorial_reporting.py','experiments/tests/test_factorial_reporting.py',
         'experiments/factorial_bounds.py','experiments/tests/test_factorial_bounds.py',
         'research/FACTORIAL_REPORTING_AMENDMENT.md','experiments/factorial_analysis.py',
         'paper/factorial_report_contract.py','paper/tests/test_factorial_reporting_contract.py')
FLAGS={'profile_anomaly','service_overload','capture_failed'}
CASE_EXTRA={'condition_id','compatible_labels','restored_bytes','scored','gated'}
PRIMARY_N=192


def expect(ok,message):
    if not ok:raise ValueError(message)


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def rows(path):return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines()]
def raw_sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def extension_api():return importlib.import_module('experiments.ollama_study')


def descriptors(extension=None):
    cfg=s.config();out={}
    for ident,model in zip(('original_g26','original_g31','original_hf'),cfg['monitors']):
        out[ident]=dict(id=ident,model=model,provider='hf' if model==cfg['hf_model'] else 'adaption',
                        origin='original',views='all',think=None)
    if extension is not None:
        for condition in extension.config()['conditions']:
            ident=condition['id'];expect(ident not in out,'Condition identity collision')
            out[ident]={key:condition[key] for key in ('id','model','think','views','input_rate','output_rate')}
            out[ident].update(provider='ollama',origin='extension')
    return out


def build_plan(actors,design,extension=None):
    """Rebuild authentic packets and every planned identity without invented rows."""
    from experiments.factorial import views
    from experiments.factorial_reference import reference_labels
    trajectories=f.replay(actors,design);packets=[];original=[]
    cfg=s.config();registry=descriptors(extension)
    for trajectory in trajectories+s.calibration_trajectories():
        selected=views(trajectory['public'],trajectory['world'])
        if 'calibration_type' in trajectory:
            selected=[view|dict(view='calibration_'+trajectory['calibration_type'])
                      for view in selected if view['view']=='sufficient']
        for view in selected:
            support=set(view['compatible_labels'])
            expect(support and support==reference_labels(view['packet']) and trajectory['host']['label'] in support,
                   'Independent authentic packet support')
            if view['view']=='sufficient' or view['view'].startswith('calibration_'):
                expect(support=={trajectory['host']['label']},'Predeclared sufficient reference')
            packets.append(dict(source_seed=trajectory['source_seed'],view=view['view'],
                                packet_sha256=s.digest(view['packet']),packet=view['packet'],
                                compatible_labels=sorted(support),added_ids=view['added_ids'],
                                restored_bytes=view['restored_bytes']))
            for model in cfg['monitors']:
                for procedure,prompt in (('direct',s.DIRECT),('procedure',s.PROCEDURE)):
                    ident=f"audit-{trajectory['source_seed']}-{view['view']}-{procedure}-{model}"
                    original.append(s.job(ident,model,prompt,view['packet'],
                        source_seed=trajectory['source_seed'],phase='audit',view=view['view'],
                        procedure=procedure,packet_sha256=s.digest(view['packet'])))
    extras=[] if extension is None else extension.jobs_from_templates([job for job in original if job['model']==cfg['hf_model']])
    expect(len({job['id'] for job in original+extras})==len(original)+len(extras),'Planned identity uniqueness')
    return trajectories,packets,original,extras,registry


def _condition(job,registry):
    if 'condition_id' in job:
        ident=job['condition_id']
        expect(ident in registry and registry[ident]['origin']=='extension','Registered extension condition')
        expect(job['metadata'].get('condition_id')==ident,'Mode-aware metadata')
        return ident
    matches=[key for key,value in registry.items() if value['origin']=='original' and value['model']==job['model']]
    expect(len(matches)==1,'Original model identity');return matches[0]


def _body(job,descriptor,extension):
    if descriptor['origin']=='original':
        provider,body=s.body_for(job)
        expect(provider==descriptor['provider'],'Original provider identity');return body
    expect(extension is not None,'Extension codec unavailable')
    return extension.body_for(job)


def _cost(row,descriptor):
    if descriptor['origin']=='original':ri,ro=s.rates(row['model'])
    else:ri,ro=Decimal(descriptor['input_rate']),Decimal(descriptor['output_rate'])
    if row['known_usage']:
        usage=row['response']['usage']
        return (usage['input_tokens']*ri+usage['output_tokens']*ro)/1000000
    return (s.config()['input_byte_cap']*ri+s.config()['max_output_tokens']*ro)/1000000


def validate_row(row,descriptor,actor=False,decorated=False):
    allowed=set(f.ALLOWED)|({'job'} if actor else set())
    if descriptor['origin']=='extension':allowed|=FLAGS
    if decorated:allowed|=CASE_EXTRA
    expect(set(row)==allowed,'Public row field allowlist')
    expect(row['model']==descriptor['model'] and row['provider']==descriptor['provider'],'Public reader/provider identity')
    expect(type(row['known_usage']) is bool,'Usage flag type')
    expect(set(row['transport'])<={'http_status','latency_seconds','error'},'No public headers or receipts')
    transport=row['transport'];status=transport.get('http_status')
    expect(status is None or (type(status) is int and 100<=status<=599),'Transport status type')
    if 'latency_seconds' in transport:
        latency=transport['latency_seconds']
        expect(type(latency) in (int,float) and math.isfinite(latency) and latency>=0,'Client elapsed time type')
    if 'error' in transport:expect(type(transport['error']) is str,'Transport error class type')
    response=row['response']
    expect(set(response)=={'status','output_text','usage','returned_model'} and type(response['output_text']) is str,
           'Normalized final response fields')
    expect(response['status'] in ('completed','incomplete','failed'),'Normalized response status')
    if row['known_usage']:
        usage=response['usage']
        expect(isinstance(usage,dict) and set(usage)=={'input_tokens','output_tokens'} and
               all(type(value) is int and value>=0 for value in usage.values()),'Usage counter types')
    else:expect(response['usage'] is None,'Unknown usage stays unknown')
    if descriptor['origin']=='extension':
        expect(all(type(row[key]) is bool for key in FLAGS),'Operational flag types')
        if row['known_usage'] and not row['profile_anomaly']:
            expect(response['returned_model']==descriptor['model'] and
                   response['usage']['input_tokens']<=s.config()['input_byte_cap'] and
                   response['usage']['output_tokens']<=s.config()['max_output_tokens'],
                   'Unflagged public model/token drift')
    elif row['known_usage']:
        allowed=live_config()['hf_allowed_returned_models'] if descriptor['provider']=='hf' else [descriptor['model']]
        expect(response['returned_model'] in allowed,'Original returned-model identity')
    expect(Decimal(row['estimated_cost']).is_finite() and Decimal(row['estimated_cost'])==_cost(row,descriptor),
           'Known cost or full unknown reservation')


def build_cases(actors,audits,design,extension_audits=(),extension=None):
    """Validate observed subsets; UNSTARTED appears in manifest only."""
    trajectories,packets,original,extras,registry=build_plan(actors,design,extension)
    packet_map={(item['source_seed'],item['view']):item for item in packets}
    all_jobs=original+extras;expected={job['id']:job for job in all_jobs}
    observed=list(audits)+list(extension_audits)
    expect(len(observed)==len({row['id'] for row in observed}),'Duplicate observed terminal')
    expect({row['id'] for row in observed}<=set(expected),'Unplanned observed terminal')
    cases=[];seen=set()
    for row in observed:
        job=expected[row['id']];ident=_condition(job,registry);descriptor=registry[ident]
        expect(row['id']==job['id'] and row['model']==job['model'] and row['metadata']==job['metadata'],
               'Condition/instruction/source/request identity')
        validate_row(row,descriptor)
        packet=packet_map[job['metadata']['source_seed'],job['metadata']['view']]
        expect(job['metadata']['packet_sha256']==packet['packet_sha256'],'Visible packet commitment')
        admitted=row['response'] if descriptor['origin']=='original' else extension.admit_response(
            row['transport'],row['response'],row['known_usage'],row['profile_anomaly'])
        score=f.score_stateful(admitted,set(packet['compatible_labels']))
        cases.append(dict(row,condition_id=ident,compatible_labels=packet['compatible_labels'],
                          restored_bytes=packet['restored_bytes'],scored=score,
                          gated=f.gated_score(score,set(packet['compatible_labels']))))
        seen.add(row['id'])
    manifest_jobs=[]
    for job in all_jobs:
        ident=_condition(job,registry);descriptor=registry[ident]
        manifest_jobs.append(dict(id=job['id'],model=job['model'],condition_id=ident,provider=descriptor['provider'],
                                 metadata=job['metadata'],request_sha256=s.digest(_body(job,descriptor,extension)),
                                 state='TERMINAL' if job['id'] in seen else 'UNSTARTED'))
    manifest=dict(schema_version=1,conditions=list(registry.values()),packets=packets,
                  jobs=sorted(manifest_jobs,key=lambda item:item['id']))
    return trajectories,sorted(cases,key=lambda row:row['id']),manifest


def _availability(planned,cases):
    count=lambda values:sum(not row['metadata']['view'].startswith('calibration_') for row in values)
    expected={row['id'] for row in planned};observed={row['id'] for row in cases}
    expect(observed<=expected,'Condition subset')
    main_planned=count(planned);main_returned=count(cases)
    return dict(planned=len(planned),returned=len(cases),unstarted=len(expected-observed),
                main_planned=main_planned,main_returned=main_returned,
                calibration_planned=len(planned)-main_planned,calibration_returned=len(cases)-main_returned,
                complete=expected==observed)


def _views(rows,view_names):
    return {view:{procedure:dict(raw=f.metrics([row for row in rows if row['metadata']['view']==view and row['metadata']['procedure']==procedure]),
                                gated=f.metrics([row for row in rows if row['metadata']['view']==view and row['metadata']['procedure']==procedure],'gated'))
                  for procedure in ('direct','procedure')} for view in view_names}


def _complete_statistics(cases,seeds,strata,procedure_effect=True,effect_fn=f.effect):
    main=[row for row in cases if not row['metadata']['view'].startswith('calibration_')]
    lookup={(row['metadata']['source_seed'],row['metadata']['view'],row['metadata']['procedure']):row for row in main}
    names=sorted({row['metadata']['view'] for row in main})
    expect(len(lookup)==len(main) and all((seed,name,procedure) in lookup for seed in seeds for name in names for procedure in ('direct','procedure')),
           'Complete condition source/view/instruction grid')
    result=dict(by_view=_views(main,names),totals=f.metrics(main))
    if procedure_effect:
        values={seed:int(lookup[seed,'sufficient','procedure']['scored']['supported_definite'])-
                     int(lookup[seed,'sufficient','direct']['scored']['supported_definite']) for seed in seeds}
        result['primary_same_packet_procedure_minus_direct']=effect_fn(values,strata)
    if set(names)>={'random_metadata','random_random','random_contract','selective_metadata','selective_random','selective_contract'}:
        acquisition={}
        for left,right in (('metadata','random'),('contract','metadata')):
            values={seed:sum(int(lookup[seed,loss+'_'+left,'direct']['scored']['grounded_correct'])-
                             int(lookup[seed,loss+'_'+right,'direct']['scored']['grounded_correct'])
                             for loss in ('random','selective'))/2 for seed in seeds}
            acquisition[left+'_minus_'+right]=effect_fn(values,strata)
        result['secondary_acquisition_grounded']=acquisition
    return result


def _pairs(cases,seeds,left,right,procedure='direct'):
    lookup={(row['condition_id'],row['metadata']['source_seed'],row['metadata']['procedure']):row
            for row in cases if row['metadata']['view']=='sufficient'}
    score=lambda ident,seed,proc:None if (ident,seed,proc) not in lookup else int(lookup[ident,seed,proc]['scored']['supported_definite'])
    return [dict(source_seed=seed,direct=score(right,seed,procedure),procedure=score(left,seed,procedure)) for seed in seeds]


def _procedure_pairs(cases,seeds,condition):
    lookup={(row['metadata']['source_seed'],row['metadata']['procedure']):row for row in cases
            if row['condition_id']==condition and row['metadata']['view']=='sufficient'}
    return [dict(source_seed=seed,**{procedure:None if (seed,procedure) not in lookup else
                 int(lookup[seed,procedure]['scored']['supported_definite']) for procedure in ('direct','procedure')}) for seed in seeds]


def _bounds(pairs):
    module=importlib.import_module('experiments.factorial_bounds')
    return module.compute_binary_pair_bounds(pairs)


def _contrast(pairs,strata,effect_fn=f.effect):
    if all(pair['direct'] is not None and pair['procedure'] is not None for pair in pairs):
        return dict(status='complete',result=effect_fn({pair['source_seed']:pair['procedure']-pair['direct'] for pair in pairs},strata))
    return dict(status='partial',identification_bounds=_bounds(pairs))


def analyze(actors,trajectories,cases,manifest,effect_fn=f.effect,expected_sources=PRIMARY_N):
    """All production callers use the frozen effect helper and n=192 default."""
    expect(len(trajectories)==expected_sources,'Original independent source denominator')
    seeds=[trajectory['source_seed'] for trajectory in trajectories]
    expect(len(set(seeds))==len(seeds),'Unique source groups')
    strata={trajectory['source_seed']:trajectory['stratum'] for trajectory in trajectories}
    registry={condition['id']:condition for condition in manifest['conditions']}
    original_ids=('original_g26','original_g31','original_hf');models={};calibration={};extensions={}
    original_models=s.config()['monitors'];view_names=sorted({row['metadata']['view'] for row in manifest['jobs'] if not row['metadata']['view'].startswith('calibration_')})
    for ident,descriptor in registry.items():
        planned=[row for row in manifest['jobs'] if row['condition_id']==ident]
        observed=[row for row in cases if row['condition_id']==ident]
        availability=_availability(planned,observed)
        cal={procedure:f.metrics([row for row in observed if row['metadata']['view'].startswith('calibration_') and row['metadata']['procedure']==procedure])
             for procedure in ('direct','procedure')}
        if ident in original_ids[:2]:
            expect(availability['complete'] and availability['main_planned']==20*len(seeds) and availability['calibration_planned']==40,
                   'Original G26/G31 complete planned grids required')
            statistics=_complete_statistics(observed,seeds,strata,effect_fn=effect_fn)
        elif ident=='original_hf':
            statistics=dict(observed_by_view=_views([row for row in observed if not row['metadata']['view'].startswith('calibration_')],view_names),
                            sufficient_identification_bounds=_bounds(_procedure_pairs(cases,seeds,ident)))
        else:
            main_names=sorted({row['metadata']['view'] for row in planned if not row['metadata']['view'].startswith('calibration_')})
            statistics=dict(by_view=_views([row for row in observed if not row['metadata']['view'].startswith('calibration_')],main_names),
                            totals=f.metrics([row for row in observed if not row['metadata']['view'].startswith('calibration_')]))
            if availability['complete']:
                statistics=_complete_statistics(observed,seeds,strata,procedure_effect=ident!='gemma_bridge',effect_fn=effect_fn)
            else:statistics['sufficient_identification_bounds']=_bounds(_procedure_pairs(cases,seeds,ident))
            statistics.update(model=descriptor['model'],think=descriptor['think'],calibration=cal)
        statistics['availability']=availability
        if descriptor['origin']=='original':models[descriptor['model']]=statistics;calibration[descriptor['model']]=cal
        else:extensions[ident]=statistics
    primary_model=original_models[0]
    primary=dict(model=primary_model,view='sufficient',metric='raw supported definite procedure minus direct',
                 result=models[primary_model]['primary_same_packet_procedure_minus_direct'])
    main=[row for row in cases if not row['metadata']['view'].startswith('calibration_')]
    primary_rows=[row for row in main if row['condition_id']=='original_g26']
    lookup={(row['metadata']['source_seed'],row['metadata']['view'],row['metadata']['procedure']):row for row in primary_rows}
    coverage={}
    for left,right in (('metadata','random'),('contract','metadata')):
        values={seed:sum(int(len(lookup[seed,loss+'_'+left,'direct']['compatible_labels'])==1)-
                         int(len(lookup[seed,loss+'_'+right,'direct']['compatible_labels'])==1) for loss in ('random','selective'))/2 for seed in seeds}
        coverage[left+'_minus_'+right]=effect_fn(values,strata)
    actual=dict(source_groups=len(trajectories),issue_valid=sum(t['choices']['issue']['valid'] for t in trajectories),
                delegate_valid=sum(t['choices']['delegate']['valid'] for t in trajectories),settle_valid=sum(t['choices']['settle']['valid'] for t in trajectories),
                writes=sum(t['world']['outcome']=='write' for t in trajectories),unauthorized_writes=sum(t['host']['label']!='NONE' for t in trajectories),
                reads=sum(t['world']['outcome']=='read' for t in trajectories),not_called=sum(t['world']['outcome']=='not_called' for t in trajectories),
                useful_completion=sum((t['host']['permitted'] and t['world']['outcome']=='write') or (not t['host']['permitted'] and t['world']['outcome']=='read') for t in trajectories))
    unique={(row['metadata']['source_seed'],row['metadata']['view']):row for row in primary_rows if row['metadata']['procedure']=='direct'}
    baselines={}
    for name,answer in (('always_abstain',dict(status='ABSTAIN',worker_id=None)),('always_none',dict(status='NONE',worker_id=None))):
        scores=[f.score_stateful(dict(status='completed',output_text=json.dumps(answer)),set(row['compatible_labels'])) for row in unique.values()]
        baselines[name]=dict(packets=len(scores),grounded_correct=sum(score['grounded_correct'] for score in scores),supported_definite=sum(score['supported_definite'] for score in scores))
    baselines['exact_packet']=dict(packets=len(unique),grounded_correct=len(unique),supported_definite=sum(len(row['compatible_labels'])==1 for row in unique.values()))
    contrasts={}
    if {'ds_low','ds_off'}<=set(extensions):contrasts['low_minus_off_direct_sufficient']=_contrast(_pairs(cases,seeds,'ds_low','ds_off'),strata,effect_fn)
    if 'gemma_bridge' in extensions:contrasts['gemma_bridge_minus_adaption31_direct_sufficient']=_contrast(_pairs(cases,seeds,'gemma_bridge','original_g31'),strata,effect_fn)
    costs={provider:str(sum((Decimal(row['estimated_cost']) for row in actors+cases if row['provider']==provider),Decimal(0))) for provider in ('adaption','hf','ollama')}
    original_count=sum(row['condition_id'].startswith('original_') for row in cases)
    return dict(sources=len(trajectories),actor_calls=len(actors),audit_calls=len(cases),original_audit_calls=original_count,
                extension_audit_calls=len(cases)-original_count,main_audit_calls=len(main),calibration_calls=len(cases)-len(main),
                planned_original_audit_calls=sum(job['condition_id'].startswith('original_') for job in manifest['jobs']),
                planned_extension_audit_calls=sum(not job['condition_id'].startswith('original_') for job in manifest['jobs']),
                primary=primary,models=models,complete_models=original_models[:2],partial_models=[original_models[2]],calibration=calibration,
                secondary_oracle_coverage=coverage,actual_behavior=actual,baselines=baselines,costs=costs,
                extensions=dict(conditions=extensions,contrasts=contrasts),
                scope='Complete original G26 primary; original HF missing responses remain unknown. Shared 192 sources, separate calibration and registered secondary extensions; operational raw scores are not conditional reasoning competence.')


def freeze():
    """Source-only HEAD guard permits independent collection source commits."""
    continuation.verify_original_sources()
    expect(not FREEZE.exists(),'Reporting registration already exists')
    for name in SOURCES:
        committed=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)
        expect(committed.replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),
               'Commit reporting source before registration: '+name)
    extension=None
    try:extension=extension_api()
    except ModuleNotFoundError as error:
        if error.name!='experiments.ollama_study':raise
    if extension is not None:
        expect(extension.FREEZE.exists(),'Freeze Ollama profiles before reporting registration')
        extension.verify()
    record=dict(schema_version=1,registration_tag=TAG,
                base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                original_freeze_sha256=s.sha(s.FREEZE),original_checkpoint_sha256=s.sha(ROOT/CHECKPOINT),
                extension_freeze_sha256=None if extension is None else s.sha(extension.FREEZE),
                source_sha256={name:s.sha(ROOT/name) for name in SOURCES})
    with FREEZE.open('x',encoding='utf-8',newline='\n') as file:file.write(json.dumps(record,indent=2)+'\n')
    return dict(created=True,tag=TAG,scope='Reporting amendment before scientific metrics; no data read')


def verify_registration():
    continuation.verify_original_sources();record=read(FREEZE)
    expect(set(record)=={'schema_version','registration_tag','base_commit','original_freeze_sha256',
                         'original_checkpoint_sha256','extension_freeze_sha256','source_sha256'},'Reporting registration schema')
    expect(type(record['schema_version']) is int and record['schema_version']==1 and record['registration_tag']==TAG,
           'Reporting registration identity')
    expect(record['original_freeze_sha256']==s.sha(s.FREEZE) and record['original_checkpoint_sha256']==s.sha(ROOT/CHECKPOINT),
           'Original experiment/checkpoint identity')
    expect(record['source_sha256']=={name:s.sha(ROOT/name) for name in SOURCES},'Reporting sources changed')
    for name in (*SOURCES,'research/'+FREEZE.name):
        blob=subprocess.check_output(['git','show',TAG+':'+name],cwd=ROOT)
        expect(blob.replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),'Tagged reporting source mismatch')
    expect(subprocess.run(['git','merge-base','--is-ancestor',record['base_commit'],TAG+'^{}'],cwd=ROOT,capture_output=True).returncode==0,
           'Reporting registration ancestry')
    extension=None
    if record['extension_freeze_sha256'] is not None:
        extension=extension_api();extension.verify()
        expect(record['extension_freeze_sha256']==s.sha(extension.FREEZE),'Registered extension changed')
    return record,extension


def _stopped_ledger(folder):
    """Read start/terminal identities only; a missing extension stage is empty."""
    folder=Path(folder)
    if not folder.exists():return dict(present=False,started=0,returned=0)
    for name in ('collector.lock','continuation.lock','continuation-pacing.lock'):
        expect(not (folder/name).exists(),'Active or stale collector lock: '+str(folder/name))
    starts=rows(folder/'attempts.jsonl') if (folder/'attempts.jsonl').exists() else []
    terminals=rows(folder/'responses.jsonl') if (folder/'responses.jsonl').exists() else []
    ids={row['id'] for row in starts};returned={row['id'] for row in terminals}
    expect(len(ids)==len(starts) and len(returned)==len(terminals) and ids==returned,'Duplicate or unresolved collector start')
    return dict(present=True,started=len(starts),returned=len(terminals))


def _driver_stopped():
    """Guard gaps between stages using only safe driver/process metadata."""
    path=ROOT/'runs/ollama-extension-driver/state.json'
    expect(path.exists(),'Extension driver termination metadata required')
    state=read(path)
    expect(state.get('status') in ('stopped','complete'),'Extension driver still running')
    pid=state.get('pid');expect(type(pid) is int and pid>0,'Driver process identity')
    # Distinguish an absent process from a failed metadata lookup; fail closed.
    command=(f"try {{ Get-Process -Id {pid} -ErrorAction Stop | Out-Null; exit 0 }} "
             "catch { if ($_.CategoryInfo.Category -eq 'ObjectNotFound') { exit 3 }; exit 4 }")
    result=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',command],capture_output=True)
    expect(result.returncode==3,'Extension driver process active or termination cannot be verified')


def collection_stopped(extension=None):
    result={stage:_stopped_ledger(s.folder(stage)) for stage in ('smoke','issue','delegate','settle','audits')}
    expect(all(value['present'] for value in result.values()),'Original collection folders required')
    if extension is not None:
        _driver_stopped()
        state=extension.collection_status();expect(state['stopped'] is True,'Extension collector active')
    return result


def _ordered_plan(jobs,seed,freeze_hash):
    ordered=list(jobs);random.Random(seed).shuffle(ordered)
    return dict(freeze_sha256=freeze_hash,jobs_sha256=s.digest(ordered),ids=[job['id'] for job in ordered],planned=len(ordered))


def _native_stage(folder,jobs,plan,registry,extension=None,actor=False):
    """Validate receipts before discarding private/native fields."""
    expect(read(folder/'plan.json')==plan,'Exact frozen request plan')
    attempts=rows(folder/'attempts.jsonl');returned=rows(folder/'responses.jsonl')
    starts={row['id']:row for row in attempts};by_id={row['id']:row for row in returned};expected={job['id']:job for job in jobs}
    expect(len(starts)==len(attempts) and len(by_id)==len(returned) and set(starts)==set(by_id) and set(by_id)<=set(expected),
           'Native observed subset/start identities')
    output=[]
    for row in returned:
        job=expected[row['id']]
        ident=_condition(job,registry) if not actor else 'original_g26'
        descriptor=registry[ident]
        expect(row['model']==job['model'] and row['metadata']==job['metadata'] and row['provider']==descriptor['provider'],
               'Native job/condition/provider binding')
        body=_body(job,descriptor,extension)
        expect(starts[row['id']]['request_sha256']==s.digest(body) and starts[row['id']]['provider']==descriptor['provider'],
               'Native request commitment')
        if descriptor['origin']=='extension':
            normal,known,anomaly=extension.normalize(row['native_response'],job['model'],descriptor['think'])
            expect(anomaly==row['profile_anomaly'],'Native anomaly flag')
        else:normal,known=s.safe_response(row['native_response'],job['model'])
        expect(normal==row['response'] and known==row['known_usage'],'Native response normalization')
        clean={key:row[key] for key in f.ALLOWED}
        if descriptor['origin']=='extension':clean.update({key:row[key] for key in FLAGS})
        if actor:clean['job']=job
        validate_row(clean,descriptor,actor=actor)
        reserve_row=dict(clean,known_usage=False)
        expect(Decimal(starts[row['id']]['reserved_cost'])==_cost(reserve_row,descriptor),'Started cost reservation')
        output.append(clean)
    return output


def export(publish_after_collection=False):
    expect(publish_after_collection is True,'Explicit --publish-after-collection required')
    registration,extension=verify_registration()
    collection_stopped(extension)
    checkpoint=read(ROOT/CHECKPOINT);raw_hashes={};phases=dict(original={},extension={})
    for relative,expected in checkpoint['raw_prefixes'].items():
        stage,name=relative.split('/');data=(s.folder(stage)/name).read_bytes()
        expect(len(data)==expected['bytes'] and hashlib.sha256(data).hexdigest()==expected['sha256'],
               'Original stopped checkpoint changed')
        raw_hashes['original/'+relative]=expected['sha256']
    design=s.contexts();registry=descriptors(extension);actors=[]
    s.smoke_pass()
    for stage in ('issue','delegate','settle'):
        folder=s.folder(stage);summary=read(folder/'summary.json')
        expect(summary['complete'] is True and summary['halted'] is False,'Complete original actor phase')
        jobs=s.actor_jobs(stage);plan=_ordered_plan(jobs,s.config()['order_seed'],s.sha(s.FREEZE))
        actors.extend(_native_stage(folder,jobs,plan,registry,actor=True))
        phases['original'][stage]=summary
    phases['original']['smoke']=read(s.folder('smoke')/'summary.json')
    _,_,original_jobs,extension_jobs,_=build_plan(actors,design,extension)
    original_plan=_ordered_plan(original_jobs,s.config()['order_seed'],s.sha(s.FREEZE))
    audits=_native_stage(s.folder('audits'),original_jobs,original_plan,registry)
    phases['original']['audits']=read(s.folder('audits')/'summary.json')
    expect(len(actors)==576 and len(audits)==9742 and len(original_jobs)==11640,'Registered original availability counts')
    extra=[]
    if extension is not None:
        for stage in ('pilot','readers'):
            folder=extension.folder(stage)
            if not folder.exists():continue
            jobs=extension.jobs('pilot') if stage=='pilot' else extension_jobs
            plan=extension.plan_for(stage,jobs)
            clean=_native_stage(folder,jobs,plan,registry,extension=extension)
            phases['extension'][stage]=read(folder/'summary.json')
            if stage=='readers':extra=clean
            for name in ('plan.json','attempts.jsonl','responses.jsonl','summary.json'):
                raw_hashes['extension/'+stage+'/'+name]=raw_sha(folder/name)
    trajectories,cases,manifest=build_cases(actors,audits,design,extra,extension)
    analysis=analyze(actors,trajectories,cases,manifest)
    original_complete=all(model['availability']['complete'] for model in analysis['models'].values())
    extension_complete=bool(analysis['extensions']['conditions']) and all(condition['availability']['complete'] for condition in analysis['extensions']['conditions'].values())
    expect(not original_complete,'This amendment must not claim the incomplete original plan complete')
    collection_stopped(extension)
    values=(dict(main=design),sorted(actors,key=lambda row:row['id']),trajectories,cases,manifest)
    for name,value in zip(FILES,values):
        text=''.join(s.canonical(row)+'\n' for row in value) if name.endswith('.jsonl') else json.dumps(value,indent=2,ensure_ascii=False)+'\n'
        (ROOT/name).write_text(text,encoding='utf-8',newline='\n')
    report=dict(schema_version=1,status='primary_complete_with_registered_extensions' if extension_complete else 'primary_complete_secondary_incomplete',
                study_id=s.config()['study_id'],reporting_tag=TAG,primary_complete=True,original_plan_complete=False,
                extension_plan_complete=extension_complete,config=s.config(),extension_config=None if extension is None else extension.config(),
                freeze_sha256=s.sha(s.FREEZE),reporting_freeze_sha256=s.sha(FREEZE),extension_freeze_sha256=registration['extension_freeze_sha256'],
                original_checkpoint_sha256=registration['original_checkpoint_sha256'],
                artifacts={name:raw_sha(ROOT/name) for name in FILES},raw_file_sha256=raw_hashes,phases=phases,analysis=analysis,
                billing='Separate provider token-rate estimates and unknown reservations; not invoices; excluded technical pilots are not scientific n',
                training_runs=0)
    REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
    return verify_public()


def _verify_phase_accounting(report,actors,cases,manifest):
    original=report['phases']['original']
    expect(set(original)=={'smoke','issue','delegate','settle','audits'},'Original phase summary coverage')
    for stage in ('issue','delegate','settle','audits'):
        summary=original[stage]
        values=[row for row in actors if row['metadata']['phase']==stage] if stage!='audits' else [row for row in cases if row['condition_id'].startswith('original_')]
        planned=192 if stage!='audits' else 11640
        expect(summary['planned']==planned and summary['returned']==len(values) and summary['unstarted']==planned-len(values) and
               summary['complete'] is (len(values)==planned) and summary['halted'] is (stage=='audits'),
               'Original phase actual/planned distinction')
        expect(summary['freeze_sha256']==s.sha(s.FREEZE),'Original phase freeze')
        expect(summary['incomplete']==sum(row['response']['status']=='incomplete' for row in values) and
               summary['gateway_errors']==sum(row['transport'].get('http_status') in (502,503,504) for row in values),
               'Original invalid/incomplete counts')
        costs={provider:str(sum((Decimal(row['estimated_cost']) for row in values if row['provider']==provider),Decimal(0))) for provider in ('adaption','hf')}
        expect(all(Decimal(summary['costs'][provider])==Decimal(cost) for provider,cost in costs.items()),'Original phase cost replay')
    smoke=original['smoke']
    expect(smoke['planned']==smoke['returned']==6 and smoke['unstarted']==0 and smoke['complete'] is True and smoke['halted'] is False,
           'Excluded original technical smoke count')
    checkpoint=read(ROOT/CHECKPOINT)
    for relative,expected in checkpoint['raw_prefixes'].items():
        expect(report['raw_file_sha256'].get('original/'+relative)==expected['sha256'],'Original checkpoint raw commitment')
    extensions=report['phases']['extension']
    expect(set(extensions)<={'pilot','readers'},'Extension phase allowlist')
    if 'readers' in extensions:
        summary=extensions['readers'];values=[row for row in cases if not row['condition_id'].startswith('original_')]
        planned=sum(not job['condition_id'].startswith('original_') for job in manifest['jobs'])
        expect(summary['planned']==planned and summary['returned']==len(values) and summary['unstarted']==planned-len(values) and
               summary['complete'] is (len(values)==planned) and type(summary['halted']) is bool,'Extension phase actual/planned distinction')
        expect(Decimal(summary['estimated_cost'])==sum((Decimal(row['estimated_cost']) for row in values),Decimal(0)),
               'Extension reader cost replay')
        expect(summary['incomplete']==sum(row['response']['status']=='incomplete' for row in values),'Extension incomplete count')
    if 'pilot' in extensions:
        pilot=extensions['pilot']
        expect(pilot['planned']==6 and type(pilot['returned']) is int and 0<=pilot['returned']<=6 and
               pilot['unstarted']==6-pilot['returned'] and pilot['complete'] is (pilot['returned']==6),
               'Excluded extension pilot denominator')


def verify_public():
    registration,extension=verify_registration();report=read(REPORT)
    expect(set(report)=={'schema_version','status','study_id','reporting_tag','primary_complete','original_plan_complete',
                         'extension_plan_complete','config','extension_config','freeze_sha256','reporting_freeze_sha256',
                         'extension_freeze_sha256','original_checkpoint_sha256','artifacts','raw_file_sha256','phases',
                         'analysis','billing','training_runs'},'Public report field allowlist')
    expect(type(report['schema_version']) is int and report['schema_version']==1 and report['reporting_tag']==TAG and
           report['config']==s.config() and report['study_id']==s.config()['study_id'], 'Public report identity')
    expect(report['freeze_sha256']==s.sha(s.FREEZE) and report['reporting_freeze_sha256']==s.sha(FREEZE) and
           report['extension_freeze_sha256']==registration['extension_freeze_sha256'] and
           report['original_checkpoint_sha256']==registration['original_checkpoint_sha256'],'Public registration bindings')
    expect(set(report['artifacts'])==set(FILES) and report['training_runs']==0,'Public artifact contract')
    for name,digest in report['artifacts'].items():expect(raw_sha(ROOT/name)==digest,'Public artifact hash')
    design=read(ROOT/FILES[0])['main']
    expect(s.digest(dict(main=design))==read(ROOT/'research/factorial-design.json')['canonical_sha256'],'Original committed source design')
    actors=rows(ROOT/FILES[1]);published=rows(ROOT/FILES[3]);manifest=read(ROOT/FILES[4])
    registry=descriptors(extension)
    for actor in actors:validate_row(actor,registry['original_g26'],actor=True)
    originals=[];extras=[]
    for row in published:
        ident=row['condition_id'];expect(ident in registry,'Registered case condition')
        validate_row(row,registry[ident],decorated=True)
        clean={key:row[key] for key in f.ALLOWED}
        if registry[ident]['origin']=='extension':clean.update({key:row[key] for key in FLAGS});extras.append(clean)
        else:originals.append(clean)
    trajectories,cases,rebuilt=build_cases(actors,originals,design,extras,extension)
    expect(trajectories==read(ROOT/FILES[2]) and published==cases and rebuilt==manifest,'Public world/plan/observed-score replay')
    analysis=analyze(actors,trajectories,cases,manifest)
    expect(report['analysis']==analysis,'Original bootstrap, bounds and extension contrasts replay')
    expect(analysis['sources']==192 and analysis['actor_calls']==576 and analysis['original_audit_calls']==9742 and
           analysis['planned_original_audit_calls']==11640,'Original full-primary/partial-secondary denominator')
    expect(report['primary_complete'] is True and report['original_plan_complete'] is False and
           not analysis['models'][s.config()['hf_model']]['availability']['complete'],'Original missingness not backfilled')
    complete=bool(analysis['extensions']['conditions']) and all(condition['availability']['complete'] for condition in analysis['extensions']['conditions'].values())
    expect(report['extension_plan_complete'] is complete and report['status']==('primary_complete_with_registered_extensions' if complete else 'primary_complete_secondary_incomplete'),
           'Honest condition-completeness status')
    expect(report['extension_config']==(None if extension is None else extension.config()),'Registered extension profile')
    _verify_phase_accounting(report,actors,cases,manifest)
    return dict(valid=True,status=report['status'],sources=192,original_returned=9742,original_unstarted=1898,
                extension_returned=analysis['extension_audit_calls'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('freeze','verify-registration','export','verify'))
    parser.add_argument('--publish-after-collection',action='store_true')
    args=parser.parse_args()
    if args.command=='freeze':result=freeze()
    elif args.command=='verify-registration':verify_registration();result={'valid':True,'scope':'Source registration only; no outcomes read'}
    elif args.command=='export':result=export(args.publish_after_collection)
    else:result=verify_public()
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
