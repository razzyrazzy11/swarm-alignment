"""Prospective six-reader MAIN adapter over immutable shared-budget science.

The eight-reader engineering graph remains the original engineering graph.
No credentials, inference or empirical outcomes are accessed on import.
"""
import argparse
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import random
import secrets
import subprocess
import threading
import time
from decimal import Decimal

from experiments import swarm_ledger_study as old

ROOT=old.ROOT
CONFIG=ROOT/'research/swarm-ledger-complete-config.json'
CATALOG=old.CATALOG
PREFIX='swarm-ledger-complete-v1'
NEW_SOURCES=(
 'experiments/swarm_ledger_complete.py','experiments/tests/test_swarm_ledger_complete.py',
 'experiments/swarm_ledger_complete_analysis.py','experiments/tests/test_swarm_ledger_complete_analysis.py',
 'experiments/swarm_ledger_complete_dispatch.py','experiments/tests/test_swarm_ledger_complete_dispatch.py',
 'experiments/swarm_ledger_complete_forecast.py','experiments/tests/test_swarm_ledger_complete_forecast.py',
 'research/swarm-ledger-complete-config.json','research/SWARM_LEDGER_COMPLETE_PROTOCOL.md',
 'research/swarm-ledger-complete-dispatch-config.json','research/SWARM_LEDGER_COMPLETE_DISPATCH_PROTOCOL.md',
 'research/swarm-ledger-dispatch-v1-stop.json','research/swarm-ledger-dispatch-v2-stop.json')
SOURCES=tuple(sorted(set(old.SOURCES+NEW_SOURCES)))
canonical=old.canonical;digest=old.digest;read=old.read;sha=old.sha;now=old.now;expect=old.expect
engine=old.engine;ARMS=old.ARMS;POLICIES=old.POLICIES
DIRECT=old.DIRECT;PROCEDURE=old.PROCEDURE;ACTOR=old.ACTOR;VERDICT_SCHEMA=old.VERDICT_SCHEMA
profile=old.profile;job=old.job;actor_jobs=old.actor_jobs;decoded_row=old.decoded_row
source_worlds=old.source_worlds;calibration_sources=old.calibration_sources
technical_jobs=old.technical_jobs
influence_jobs=old.influence_jobs;influence_worlds=old.influence_worlds
body_for=old.body_for;normalize=old.normalize;admitted=old.admitted
reservation=old.reservation;actual_cost=old.actual_cost;apply_host_action=old.apply_host_action
Transport=old.Transport;credentials=old.credentials
rows=old.rows;durable=old.durable;ledger=old.ledger;exclusive=old.exclusive
check_metadata=old.check_metadata;service_overload=old.service_overload
validate_contexts=old.validate_contexts
score=old.score;decode_actor=old.decode_actor
_lock=threading.RLock();_snapshot=None

def _validate_config(c):
    baseline=old.config()
    expect(set(c)==set(baseline)|{'registration_prefix'},'Unregistered configuration field')
    changed={'status','reader_profiles','auxiliary_reader_profiles','combined_caps','phase_caps'}
    expect(all(c[k]==v for k,v in baseline.items() if k not in changed),'Material frozen body/actor/policy/price setting changed')
    expect(c['registration_prefix']==PREFIX,'Complete-study registration identity')
    expect(c['reader_profiles']==['g26','g31','hf_text','hf_schema','ds_off','ds_low'],'Six-reader core grid')
    expect(c['auxiliary_reader_profiles']==['g26','g31','ds_low'],'Three-reader auxiliary grid')
    expected_combined=deepcopy(baseline['combined_caps']);expected_combined['ollama']='100.00'
    expected_phases=deepcopy(baseline['phase_caps']);expected_phases['main']['ollama']='99.70'
    expect(c['combined_caps']==expected_combined and c['phase_caps']==expected_phases,'Only the funded Ollama ceiling may change')
    expect(c['status'] in ('DRAFT_NOT_REGISTERED','READY_FOR_REGISTRATION'),'Unknown configuration status')
    return c

def config():
    return deepcopy(_snapshot['data']) if _snapshot is not None else _validate_config(read(CONFIG))

def check_config_file():
    old.check_config_file()
    if _snapshot is not None:
        expect(hashlib.sha256(CONFIG.read_bytes()).hexdigest()==_snapshot['raw_sha256'],'Complete config bytes changed')
        expect(digest(_snapshot['data'])==_snapshot['canonical_sha256'],'Complete snapshot mutation')
    return True

@contextmanager
def verified_config():
    global _snapshot
    with _lock,old.verified_config():
        previous=_snapshot;raw=CONFIG.read_bytes();data=_validate_config(json.loads(raw.decode('utf-8-sig')))
        snapshot={'data':deepcopy(data),'raw_sha256':hashlib.sha256(raw).hexdigest(),'canonical_sha256':digest(data)}
        if previous is not None:
            expect(previous['raw_sha256']==snapshot['raw_sha256'],'Nested complete config drift');snapshot=previous
        _snapshot=snapshot
        try:yield deepcopy(data)
        finally:
            try:check_config_file()
            finally:_snapshot=previous

def folder(split):return ROOT/('runs/'+config()['study_id']+'-'+split)

def atomic_metadata(path,value):
    """Retry Windows metadata sharing violations, never a provider request."""
    temporary=Path(path).with_name(Path(path).name+'.'+str(os.getpid())+'.tmp')
    for attempt in range(40):
        try:
            with temporary.open('w',encoding='utf-8',newline='\n') as f:
                json.dump(value,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
            temporary.replace(path)
            return
        except PermissionError:
            if attempt==39:raise
            time.sleep(min(.05*(attempt+1),.25))

class BalanceGuard:
    """Original shared-cache rule, using this adapter's explicit ROOT."""
    def __init__(self,transport):self.transport=transport;self.last=None;self.available=None;self.at_poll=Decimal(0)
    def check(self,spent,reserved):
        c=config()
        if self.last is None or time.monotonic()-self.last>=c['balance_poll_seconds']:
            path=ROOT/('runs/'+c['study_id']+'-guard/balance-private.json')
            cached=read(path) if path.exists() else None
            if cached and 0<=time.time()-cached['epoch']<c['balance_poll_seconds']:
                self.available=Decimal(cached['available']);self.at_poll=Decimal(cached['spent'])
                self.last=time.monotonic()-(time.time()-cached['epoch'])
            else:
                data=self.transport.metadata('https://ollama.com/api/balance','OLLAMA_API_KEY')
                try:self.available=Decimal(str(data['included']['balance_usd']))+Decimal(str(data['purchased']['balance_usd']))
                except (KeyError,TypeError,ArithmeticError):raise ValueError('Ollama balance schema unknown') from None
                expect(self.available.is_finite(),'Nonfinite balance');self.last=time.monotonic();self.at_poll=spent
                path.parent.mkdir(parents=True,exist_ok=True)
                atomic_metadata(path,{'epoch':time.time(),'available':str(self.available),'spent':str(spent)})
        expect(self.available-(spent-self.at_poll)-reserved>Decimal(c['remaining_credit_floor']),'Ollama credit floor reached')

def freeze_path(split):
    return ROOT/('research/'+PREFIX+'-main-freeze.json') if split=='main' else old.freeze_path(split)

def contexts(split):
    values=read(folder(split)/'contexts-private.json');validate_contexts(values,split);return values

def make_contexts(split='main'):
    expect(split=='main' and not freeze_path('main').exists(),'Only an unregistered fresh MAIN design')
    expect(not old.freeze_path('main').exists(),'Original eight-reader MAIN must remain unregistered')
    c=config();out=folder('main');expect(not (out/'contexts-private.json').exists(),'Private design exists')
    rng=secrets.SystemRandom();values=[]
    for family in c['worker_profiles']:
        for policy in POLICIES:
            for layout in ('canonical','shuffled'):
                for repetition in range(c['main_repetitions']):
                    start=rng.randrange(10,1000)
                    public=dict(namespace=secrets.token_hex(16),budget=int(policy[1]),local_cap_x=2,local_cap_y=2,
                                lease_start=start,lease_end=start+3,target_closed=True,workers=list('ABCDE'))
                    values.append(dict(block_id=secrets.token_hex(12),public=public,policy=policy,layout=layout,
                        worker_profile=family,route=rng.sample(list('ABCDE'),5),time_y=start+3 if policy=='B4expiry' else start+2,
                        revoked=policy=='B4revoked',repetition=repetition,split='main'))
    rng.shuffle(values);validate_contexts(values,'main');out.mkdir(parents=True,exist_ok=True)
    with (out/'contexts-private.json').open('x',encoding='utf-8',newline='\n') as f:
        json.dump(values,f);f.flush();os.fsync(f.fileno())
    return {'blocks':len(values),'sha256':digest(values)}

def reader_jobs(sources):
    c=config();out=[]
    if sources and sources[0]['split']=='development':
        expect(all(s['split']=='development' for s in sources),'Mixed engineering and MAIN sources')
        return old.reader_jobs(sources)
    for src in sources:
        expect(src['split']=='main','MAIN reader source required')
        for name,v in {v['view']:v for v in engine.views(src['public'],src['world'])}.items():
            if name=='full':readers=c['reader_profiles'];procedures=('direct','procedure')
            elif src['arm'] in ('honest','both'):readers=c['auxiliary_reader_profiles'];procedures=('direct',)
            else:continue
            packet=v['packet'];text=engine.serialize(packet,layout=src['layout'])
            for reader in readers:
                for procedure in procedures:
                    metadata={k:src[k] for k in ('source_id','block_id','arm','worker_profile','policy','layout','split')}
                    metadata.update(view='receipt_only7' if name=='sufficient' else name,procedure=procedure,
                        packet_sha256=digest(packet),compatible_labels=sorted(v['compatible_labels']),
                        restored_ids=v['restored_ids'],restored_bytes=v['restored_bytes'])
                    out.append(job(digest([src['source_id'],name,reader,procedure]),reader,
                        [{'role':'system','content':DIRECT if procedure=='direct' else PROCEDURE},
                         {'role':'user','content':text}],metadata))
    expect(len({j['id'] for j in out})==len(out),'Duplicate complete reader job')
    return out

def registration(split,create=False):
    if split!='main':return old.registration(split,create)
    c=config();path=freeze_path('main')
    old.registration('technical');old.registration('development')
    if create:
        expect(c['status']=='READY_FOR_REGISTRATION' and not path.exists(),'Configuration or registration not ready')
        expect(not old.freeze_path('main').exists(),'Original eight-reader MAIN was registered')
        expect(not any(p.stat().st_size for p in folder('main').glob('*/attempts.jsonl')),'MAIN already started')
        for name in SOURCES:
            blob=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)
            expect(blob.replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),'Commit complete sources before registration')
        value=dict(schema_version=1,split='main',config=c,source_sha256={n:sha(ROOT/n) for n in SOURCES},
            base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            tag=PREFIX+'-main',created=now(),contexts_sha256=digest(contexts('main')),
            engineering_registration_sha256={p:sha(old.freeze_path(p)) for p in ('technical','development')},
            original_eight_reader_main_registered=False,main_started_before_registration=False,
            planned=dict(blocks=640,trajectories=2560,actor_calls_including_influence=9200,
                         reader_calls=53760,calibration_calls=240,total_calls=63200))
        with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
        return value
    value=read(path)
    expect(value['config']==c and value['source_sha256']=={n:sha(ROOT/n) for n in SOURCES},'Complete registered source drift')
    expect(value['engineering_registration_sha256']=={p:sha(old.freeze_path(p)) for p in ('technical','development')},'Original engineering anchors changed')
    expect(value['original_eight_reader_main_registered'] is False and value['main_started_before_registration'] is False,'MAIN chronology changed')
    for name in (*SOURCES,str(path.relative_to(ROOT)).replace('\\','/')):
        blob=subprocess.check_output(['git','show',value['tag']+':'+name],cwd=ROOT)
        expect(blob.replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),'Complete registered tag drift')
    expect(subprocess.run(['git','merge-base','--is-ancestor',value['base_commit'],value['tag']+'^{}'],cwd=ROOT,capture_output=True).returncode==0,'Complete registration ancestry')
    return value

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('design','freeze','verify'));a=p.parse_args()
    result=make_contexts() if a.command=='design' else registration('main',True) if a.command=='freeze' else {'valid':bool(registration('main'))}
    print(canonical(result))

if __name__=='__main__':main()
