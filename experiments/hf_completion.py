"""Prospective operational completion of unchanged, originally unstarted HF jobs.

No network, credentials or scientific scores on import or public verification.
Old journals and results-v3 remain immutable; new receipts use a separate folder.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import build_opener, urlopen

from experiments import factorial_study as s
from experiments import factorial_continue as c
from experiments.access import SameOriginRedirect

ROOT=s.ROOT
TAG='hf-completion-v1'
CONFIG=ROOT/'research/hf-completion-config.json'
CATALOG=ROOT/'research/hf-completion-catalog.json'
FREEZE=ROOT/'research/hf-completion-v1-freeze.json'
CHECKPOINT='research/factorial-rate-stop.json'
SNAPSHOT='results-v3'
MANIFEST='data/factorial_report_manifest.json'
SOURCES=('experiments/hf_completion.py','experiments/tests/test_hf_completion.py',
         'research/HF_COMPLETION_PROTOCOL.md','research/hf-completion-config.json',
         'research/hf-completion-catalog.json','experiments/factorial_continue.py')
FIXED=dict(study_id=TAG,min_start_interval_seconds=30,transient_backoff_seconds=60,
           circuit_consecutive_transients=8,circuit_pause_seconds=600,
           new_transient_allowance=256,new_estimated_cost_cap='2.50',max_active=1,
           timeout_seconds=120,retries=0,metadata_recheck_calls=100,
           historical_audit_terminals=9742,historical_hf_terminals=1982,
           original_unstarted=1898,historical_429_count=5)


def now():return datetime.now(timezone.utc).isoformat()
def expect(ok,message):
    if not ok:raise ValueError(message)
def raw_sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def blob(path,tag=SNAPSHOT):return subprocess.check_output(['git','show',tag+':'+path],cwd=ROOT)
def config():
    value=s.read(CONFIG);expect(s.canonical(value)==s.canonical(FIXED),'Fixed completion configuration changed')
    return value
def folder():return ROOT/('runs/'+TAG)


def snapshot():
    """Public immutable planned/observed states; never infer absent answers."""
    data=blob(MANIFEST);manifest=json.loads(data)
    original=[j for j in manifest['jobs'] if j['condition_id'].startswith('original_')]
    pending=[j for j in original if j['state']=='UNSTARTED']
    expect(len(original)==11640 and sum(j['state']=='TERMINAL' for j in original)==9742,
           'Original snapshot grid differs')
    expect(len(pending)==1898 and all(j['provider']=='hf' and j['condition_id']=='original_hf' for j in pending),
           'Snapshot unstarted HF identities differ')
    return manifest,{j['id']:j for j in pending},hashlib.sha256(data).hexdigest()


def descriptor(job):
    provider,body=s.body_for(job)
    expect(provider=='hf' and job['model']==s.config()['hf_model'],'Completion is exact original HF only')
    return dict(id=job['id'],model=job['model'],provider=provider,
                metadata=job['metadata'],request_sha256=s.digest(body))


def original_idle(owned_lock=False):
    out=s.folder('audits')
    for name in ('collector.lock','continuation-pacing.lock','continuation.lock'):
        if name=='continuation.lock' and owned_lock:continue
        expect(not (out/name).exists(),'Original collector lock active or stale')
    path=ROOT/'runs/factorial-driver-v1/state.json'
    expect(path.exists(),'Original driver termination metadata required')
    state=s.read(path);expect(state.get('status') in ('stopped','complete'),'Original driver still running')
    pid=state.get('pid');expect(type(pid) is int and pid>0,'Original driver process identity')
    if os.name=='nt':
        command=(f'try {{ Get-Process -Id {pid} -ErrorAction Stop | Out-Null; exit 0 }} '
                 'catch { if ($_.CategoryInfo.Category -eq "ObjectNotFound") { exit 3 }; exit 4 }')
        result=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',command],capture_output=True)
        expect(result.returncode==3,'Original driver active or process lookup failed')
    else:
        try:os.kill(pid,0)
        except ProcessLookupError:return
        except (OSError,PermissionError):raise ValueError('Original driver termination cannot be verified') from None
        raise ValueError('Original driver process active')


def original_prefix(owned_lock=False):
    """Read-only replay of source/body/cost commitments, without printing answers."""
    c.verify_original_sources();s.verify();original_idle(owned_lock);cfg=config();checkpoint=s.read(ROOT/CHECKPOINT)
    for relative,value in checkpoint['raw_prefixes'].items():
        stage,name=relative.split('/',1);path=s.folder(stage)/name
        expect(path.stat().st_size==value['bytes'] and raw_sha(path)==value['sha256'],
               'Original raw checkpoint changed: '+relative)
    jobs,plan=c.shuffled_plan(s.audit_jobs());out=s.folder('audits')
    expect(s.read(out/'plan.json')==plan,'Original plan changed')
    starts,rows,started=c.ledger(out,jobs,plan)
    expect(len(starts)==len(rows)==cfg['historical_audit_terminals'],'Original checkpoint count changed')
    expect(sum(r['provider']=='hf' for r in rows)==cfg['historical_hf_terminals'],'Historical HF count changed')
    rate_ids=[r['id'] for r in rows if r['transport'].get('http_status')==429]
    expect(len(rate_ids)==cfg['historical_429_count'],'Historical error count changed')
    pending=[j for j in jobs if j['id'] not in started]
    expect(len(pending)==cfg['original_unstarted'],'Original unstarted complement changed')
    _,published,_=snapshot()
    for j in pending:
        d=descriptor(j);p=published[j['id']]
        expect(all(d[k]==p[k] for k in d),'Original request differs from published commitment')
    return pending,rate_ids


def catalog_record(data):
    cfg=s.config();name,provider=cfg['hf_model'].rsplit(':',1)
    matches=[p for m in data.get('data',[]) if m.get('id')==name
             for p in m.get('providers',[]) if p.get('provider')==provider]
    expect(len(matches)==1,'Exact HF route unavailable')
    p=matches[0];expect(p.get('status')=='live','HF route is not live')
    expect(all(Decimal(str(p.get('pricing',{}).get(k)))==Decimal(cfg['hf_'+k+'_rate']) for k in ('input','output')),
           'HF route price drift')
    return dict(model=cfg['hf_model'],provider=provider,status=p['status'],pricing=p['pricing'],
                context_length=p.get('context_length'),supports_structured_output=p.get('supports_structured_output'))


def metadata(expected=None):
    # This GET is public, carries no key and cannot change inference/billing settings.
    with urlopen(s.HF+'/models',timeout=30) as response:
        expect(response.status==200,'HF catalog unavailable');record=catalog_record(json.load(response))
    if expected is not None:expect(record==expected['route'],'HF route metadata drift')
    return dict(checked=now(),inference_calls=0,route=record)


def catalog():
    expect(not FREEZE.exists(),'Frozen catalog must not be overwritten')
    value=metadata();CATALOG.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
    return value


def freeze():
    expect(not FREEZE.exists(),'Completion freeze exists')
    config();catalog_record(dict(data=[dict(id=s.config()['hf_model'].rsplit(':',1)[0],providers=[s.read(CATALOG)['route']])]))
    for name in SOURCES:
        expect(blob(name,'HEAD').replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),
               'Commit completion source before registration: '+name)
    jobs,historical=original_prefix();_,_,published_hash=snapshot()
    record=dict(schema_version=1,tag=TAG,base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                source_sha256={p:s.sha(ROOT/p) for p in SOURCES},checkpoint_sha256=s.sha(ROOT/CHECKPOINT),
                original_freeze_sha256=s.sha(s.FREEZE),snapshot_tag=SNAPSHOT,snapshot_manifest_sha256=published_hash,
                historical_429_ids=historical,pending=[descriptor(j) for j in jobs],
                timing='Operational amendment after original outcomes were reviewed; scientific requests and scoring unchanged')
    with FREEZE.open('x',encoding='utf-8',newline='\n') as file:file.write(json.dumps(record,indent=2)+'\n')
    return dict(created=True,tag=TAG,pending=len(jobs))


def verify():
    """Public verification: no keys, raw journals, job reconstruction or API calls."""
    c.verify_original_sources();config();r=s.read(FREEZE)
    expect(set(r)=={'schema_version','tag','base_commit','source_sha256','checkpoint_sha256','original_freeze_sha256',
                    'snapshot_tag','snapshot_manifest_sha256','historical_429_ids','pending','timing'},'Completion registration schema')
    expect(type(r['schema_version']) is int and r['schema_version']==1 and r['tag']==TAG and r['snapshot_tag']==SNAPSHOT,'Completion registration identity')
    expect(r['source_sha256']=={p:s.sha(ROOT/p) for p in SOURCES},'Completion source changed')
    expect(r['checkpoint_sha256']==s.sha(ROOT/CHECKPOINT) and r['original_freeze_sha256']==s.sha(s.FREEZE),
           'Original checkpoint/freeze changed')
    for name in (*SOURCES,'research/'+FREEZE.name):
        expect(blob(name,TAG).replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),
               'Completion tag differs: '+name)
    expect(subprocess.run(['git','merge-base','--is-ancestor',r['base_commit'],TAG+'^{}'],cwd=ROOT,capture_output=True).returncode==0,
           'Completion registration ancestry')
    _,pending,h=snapshot();expect(h==r['snapshot_manifest_sha256'],'Snapshot manifest hash differs')
    expect(len(r['pending'])==1898 and len({j['id'] for j in r['pending']})==1898 and
           {j['id'] for j in r['pending']}==set(pending),'Registered unstarted set differs')
    for d in r['pending']:
        expect(set(d)=={'id','model','provider','metadata','request_sha256'} and all(d[k]==pending[d['id']][k] for k in d),
               'Registered request commitment differs')
    expect(len(r['historical_429_ids'])==len(set(r['historical_429_ids']))==5,'Historical errors must remain five')
    return r


def keys():
    allowed={'HF_TOKEN','ADAPTION_API_KEY','OLLAMA_API_KEY'};result={}
    path=ROOT/'.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            if not line.strip() or line.lstrip().startswith('#'):continue
            key,sep,value=line.partition('=');key=key.strip();value=value.strip()
            if sep and key in allowed:
                if len(value)>1 and value[0]==value[-1] and value[0] in ('"',"'"):value=value[1:-1]
                result[key]=value
    result.update({k:os.environ[k] for k in allowed if os.environ.get(k)})
    result={k:v for k,v in result.items() if v and 'replace_locally' not in v and not v.startswith('YOUR_')}
    expect(bool(result.get('HF_TOKEN')),'HF_TOKEN unavailable')
    return result


def explicit_overload(status,body):
    if status!=429:return False
    try:
        data=json.loads(body);error=data.get('error') if isinstance(data,dict) else None
        if isinstance(error,str):return error.strip().lower().startswith('server overload') or error=='server_overload'
        if isinstance(error,dict):
            return (any(error.get(k)=='server_overload' for k in ('type','code')) or
                    isinstance(error.get('message'),str) and error['message'].strip().lower().startswith('server overload'))
    except (ValueError,TypeError):pass
    return False


class CapturingOpener:
    """Retain bounded scrubbed errors privately; expose category, never raw body."""
    def __init__(self,out,secrets,clock,opener=None):
        self.out=Path(out);self.secrets=secrets;self.clock=clock
        self.opener=opener or build_opener(SameOriginRedirect());self.last_open_started=None
        self.service_overload=False;self.capture_failed=False;self.retry_after_delay=0.;self.ordinal=0;self.last_receipt=None
    def open(self,request,timeout=120):
        self.service_overload=False;self.capture_failed=False;self.retry_after_delay=0.;self.last_receipt=None
        self.last_open_started=self.clock()
        try:return self.opener.open(request,timeout=timeout)
        except HTTPError as error:
            self.retry_after_delay=c.retry_after((error.headers or {}).get('Retry-After')) or 0.
            try:
                raw=error.read(16384).decode('utf-8',errors='replace')
                self.service_overload=explicit_overload(error.code,raw)
                self.out.mkdir(parents=True,exist_ok=True)
                record=s.scrub(dict(http_status=error.code,error_body=raw,headers=dict(error.headers or {}),byte_cap=16384),self.secrets)
                path=self.out/f'error-{self.ordinal:06d}.json'
                with path.open('x',encoding='utf-8') as file:
                    file.write(json.dumps(record,ensure_ascii=True)+'\n')
                self.last_receipt=dict(file='private-errors/'+path.name,sha256=raw_sha(path))
                self.ordinal+=1
            except Exception:self.capture_failed=True
            raise


def reservation(job):
    ri,ro=s.rates(job['model']);cfg=s.config()
    return (cfg['input_byte_cap']*ri+cfg['max_output_tokens']*ro)/1000000


def transient(row):
    code=row['transport'].get('http_status')
    return (code in (502,503,504) or code==429 and row.get('service_overload') is True) and not row['known_usage'] and row.get('native_response') is None and row['transport'].get('error')=='HTTPError'


def fatal(row):
    if row.get('capture_failed'):return True
    if transient(row):return False
    return s.unsafe(row,0,0) or row['transport'].get('http_status')!=200


@contextmanager
def exclusive(out):
    owned=[];handles=[]
    try:
        for path in (s.folder('audits')/'continuation.lock',Path(out)/'collector.lock'):
            try:handle=path.open('x',encoding='ascii')
            except FileExistsError:raise ValueError('Collector active or stale lock requires review') from None
            owned.append(path);handles.append(handle);handle.write('1\n');handle.flush()
        yield
    finally:
        for handle in reversed(handles):handle.close()
        for path in reversed(owned):path.unlink()


def supplement_ledger(out,jobs,plan):
    expect(s.read(Path(out)/'plan.json')==plan,'Supplement plan changed')
    starts,rows,started=c.ledger(Path(out),jobs,dict(ids=plan['ids']))
    expect([r['id'] for r in starts]==plan['ids'][:len(starts)] and
           [r['id'] for r in rows]==[r['id'] for r in starts],'Supplement dispatch order differs')
    byid={j['id']:j for j in jobs}
    for row in rows:
        job=byid[row['id']]
        expect(row['model']==job['model'] and row['metadata']==job['metadata'],'Supplement identity/metadata changed')
        expect(type(row.get('service_overload')) is bool and type(row.get('capture_failed')) is bool,'Supplement flags invalid')
        normal,known=s.safe_response(row.get('native_response'),job['model'])
        expect(normal==row['response'] and known is row['known_usage'],'Supplement native normalization changed')
        receipt=row.get('error_receipt')
        if row['transport'].get('error')=='HTTPError' and not row['capture_failed']:
            expect(isinstance(receipt,dict) and set(receipt)=={'file','sha256'},'HTTP error capture commitment missing')
            relative=Path(receipt['file'])
            expect(relative.parent==Path('private-errors') and relative.name.startswith('error-') and
                   relative.suffix=='.json' and relative.stem[6:].isdigit(),'Error capture path outside owned folder')
            path=Path(out)/relative
            expect(raw_sha(path)==receipt['sha256'],'Private error capture changed')
            error=s.read(path)
            expect(error['http_status']==row['transport'].get('http_status') and
                   explicit_overload(error['http_status'],error['error_body']) is row['service_overload'],
                   'Error category differs from private capture')
        elif receipt is not None:raise ValueError('Unexpected private error commitment')
    return starts,rows,started


def execute(resume=False,transport=None,clock=None,sleep=None):
    r=verify();cfg=config();clock=clock or time.monotonic;sleep=sleep or time.sleep
    jobs,historical=original_prefix()
    expect([descriptor(j) for j in jobs]==r['pending'] and historical==r['historical_429_ids'],'Private original plan drift')
    out=folder();plan=dict(freeze_sha256=s.sha(FREEZE),ids=[j['id'] for j in jobs],planned=len(jobs),
                           pending_sha256=s.digest(r['pending']))
    if out.exists() and not resume:raise ValueError('Run exists; use exact unstarted continuation')
    if not out.exists():out.mkdir(parents=True);(out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8',newline='\n')
    with exclusive(out):
        repeated_jobs,repeated_historical=original_prefix(owned_lock=True)
        expect([descriptor(j) for j in repeated_jobs]==r['pending'] and repeated_historical==historical,
               'Original prefix changed while acquiring lock')
        starts,rows,started=supplement_ledger(out,jobs,plan)
        total_transients=sum(transient(row) for row in rows)
        expect(not any(fatal(row) for row in rows) and total_transients<cfg['new_transient_allowance'],'Prior fatal/allowance gate remains active')
        spent=sum((Decimal(row['estimated_cost']) for row in rows),Decimal(0))
        if (out/'summary.json').exists():
            prior=s.read(out/'summary.json')
            expect(not prior.get('halted') or prior.get('stop_reason')=='operator_stop','Prior halted completion requires a new amendment')
        pending=[j for j in jobs if j['id'] not in started]
        secret=keys();metadata(s.read(CATALOG))
        if transport is None:
            opener=CapturingOpener(out/'private-errors',list(secret.values()),clock)
            opener.ordinal=len(list((out/'private-errors').glob('error-*.json')))
            transport=c.Transport(out/'rate-private.jsonl',opener=opener,monotonic=clock)
        stop=out/'STOP';next_start=clock()+cfg['min_start_interval_seconds']
        # Fresh startup always waits; on resume also honor the last recorded wait
        # using wall time, without restarting an already-started identity.
        if rows:
            last=rows[-1];elapsed=max(0,time.time()-datetime.fromisoformat(last['finished']).timestamp())
            next_start=max(next_start,clock()+max(0,last['next_delay_seconds']-elapsed))
        streak=0
        for row in reversed(rows):
            if not transient(row):break
            streak+=1
        streak%=cfg['circuit_consecutive_transients']
        halted=False;reason='';since_metadata=0
        with (out/'attempts.jsonl').open('a',encoding='utf-8') as attempts,(out/'responses.jsonl').open('a',encoding='utf-8') as responses:
            while pending and not halted:
                try:c.wait_until(next_start,stop,clock,sleep)
                except c.Stopped:halted=True;reason='operator_stop';break
                if since_metadata>=cfg['metadata_recheck_calls']:
                    try:metadata(s.read(CATALOG));since_metadata=0
                    except Exception:halted=True;reason='catalog_drift';break
                job=pending[0];reserve=reservation(job)
                if spent+reserve>Decimal(cfg['new_estimated_cost_cap']):halted=True;reason='budget';break
                provider,body=s.body_for(job)
                if stop.exists():halted=True;reason='operator_stop';break
                s.durable(attempts,dict(id=job['id'],request_sha256=s.digest(body),provider=provider,
                                        reserved_cost=str(reserve),started=now()))
                try:public,native=transport(s.HF+'/chat/completions',secret['HF_TOKEN'],body,timeout=cfg['timeout_seconds'])
                except Exception:public,native=dict(http_status=None,error='unexpected_request_error'),None
                normal,known=s.safe_response(native,job['model']);ri,ro=s.rates(job['model'])
                usage=normal.get('usage');cost=(usage['input_tokens']*ri+usage['output_tokens']*ro)/1000000 if known else reserve
                spent+=cost;opener=getattr(transport,'opener',None)
                row=dict(id=job['id'],model=job['model'],metadata=job['metadata'],provider=provider,
                         transport=public,response=normal,known_usage=known,estimated_cost=str(cost),native_response=native,
                         service_overload=bool(getattr(opener,'service_overload',False)),
                         capture_failed=bool(getattr(opener,'capture_failed',False)),
                         error_receipt=getattr(opener,'last_receipt',None),finished=now())
                opened=c.numeric(getattr(opener,'last_open_started',None))
                base=clock() if opened is None else opened
                delay=cfg['min_start_interval_seconds'];wait_after=0.
                if transient(row):
                    total_transients+=1;streak+=1
                    wait_after=max(cfg['transient_backoff_seconds'],c.numeric(getattr(opener,'retry_after_delay',0)) or 0)
                    if streak>=cfg['circuit_consecutive_transients']:
                        wait_after=max(wait_after,cfg['circuit_pause_seconds']);streak=0
                else:streak=0
                next_start=max(base+delay,clock()+wait_after)
                row['next_delay_seconds']=max(0,next_start-clock())
                row=s.scrub(row,secret.values());s.durable(responses,row);rows.append(row);pending.pop(0);since_metadata+=1
                if fatal(row):halted=True;reason='fatal_transport_profile_or_capture'
                elif total_transients>=cfg['new_transient_allowance']:halted=True;reason='transient_allowance'
                elif spent>Decimal(cfg['new_estimated_cost_cap']):halted=True;reason='provider_cost_overrun'
        result=dict(planned=len(jobs),returned=len(rows),unstarted=len(pending),complete=len(rows)==len(jobs),halted=halted,
                    stop_reason=reason,new_transient_errors=total_transients,historical_429_preserved=5,
                    new_estimated_cost=str(spent),historical_hf_cost='0.880229785',freeze_sha256=s.sha(FREEZE),
                    cost_basis='token-rate estimate or full unknown reservation, not reconciled invoice',
                    original_audit_returned=9742+len(rows),original_hf_returned=1982+len(rows))
        (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
        return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=('catalog','freeze','verify','run'))
    parser.add_argument('--continue-unstarted',action='store_true');args=parser.parse_args()
    if args.command=='run':result=execute(args.continue_unstarted)
    elif args.command=='verify':verify();result=dict(valid=True,scope='public registration only; no calls or private ledgers')
    else:result=globals()[args.command]()
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
