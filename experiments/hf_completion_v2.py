"""Prospective HF overload-classifier recovery; immutable first nine terminals."""
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import time
from urllib.error import HTTPError

from experiments import hf_completion as h, factorial_study as s, factorial_continue as c

ROOT=s.ROOT
TAG='hf-completion-v2'
FREEZE=ROOT/'research/hf-completion-v2-freeze.json'
SOURCES=('experiments/hf_completion_v2.py','experiments/tests/test_hf_completion_v2.py',
         'research/HF_COMPLETION_V2_PROTOCOL.md')
FIXED=dict(study_id=TAG,prior_terminals=9,remaining=1889,total_terminals=1898,
    min_start_interval_seconds=30,transient_backoff_seconds=60,circuit_consecutive_transients=8,
    circuit_pause_seconds=600,new_transient_allowance=256,new_estimated_cost_cap='2.50',
    timeout_seconds=120,retries=0,metadata_recheck_calls=100,max_active=1)


def expect(ok,message):
    if not ok:raise ValueError(message)


def folder():return ROOT/('runs/'+TAG)
def now():return datetime.now(timezone.utc).isoformat()


def explicit_overload(status,body):
    """New narrow top-level profile plus the unchanged prior nested profiles."""
    if h.explicit_overload(status,body):return True
    if status!=429:return False
    try:
        value=json.loads(body)
        return (type(value) is dict and any(value.get(k)=='server_overload' for k in ('type','code'))
            and type(value.get('message')) is str and value['message'].strip().lower().startswith('server overload'))
    except (ValueError,TypeError):return False


class CapturingOpener(h.CapturingOpener):
    def open(self,request,timeout=120):
        try:return super().open(request,timeout)
        except HTTPError:
            if self.last_receipt is not None and not self.capture_failed:
                try:
                    saved=s.read(self.out.parent/self.last_receipt['file'])
                    self.service_overload=explicit_overload(saved['http_status'],saved['error_body'])
                except Exception:self.capture_failed=True
            raise


def prior_prefix(owned_lock=False):
    """Private call; requires analysis source registration before any answer read."""
    from experiments import hf_completion_analysis as a
    a.verify_registration();a.driver_stopped()
    jobs,historical=h.original_prefix(owned_lock)
    registration=h.verify()
    plan=dict(freeze_sha256=s.sha(h.FREEZE),ids=[j['id'] for j in jobs],planned=len(jobs),
              pending_sha256=s.digest(registration['pending']))
    starts,rows,started=h.supplement_ledger(h.folder(),jobs,plan)
    expect(len(starts)==len(rows)==9,'Prior completion prefix must remain exactly nine terminals')
    hashes={name:h.raw_sha(h.folder()/name) for name in ('plan.json','attempts.jsonl','responses.jsonl','summary.json')}
    remaining=[j for j in jobs if j['id'] not in started]
    expect(len(remaining)==1889,'Remaining original complement differs')
    # Count the newly diagnosed prior overload, without changing its old flag.
    prior_transients=0
    for row in rows:
        receipt=row.get('error_receipt')
        if receipt is not None:
            error=s.read(h.folder()/receipt['file'])
            prior_transients+=int(explicit_overload(error['http_status'],error['error_body']))
    expect(prior_transients==1,'Diagnosed prior overload count differs')
    return remaining,rows,hashes,prior_transients


def freeze():
    expect(not FREEZE.exists(),'Recovery registration exists')
    from experiments import hf_completion_analysis as a
    a.verify_registration()
    for name in SOURCES:
        expect(h.blob(name,'HEAD').replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),'Commit recovery sources before registration')
    jobs,prior,hashes,transients=prior_prefix()
    record=dict(schema_version=1,tag=TAG,config=FIXED,created=now(),
        base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_sha256={name:s.sha(ROOT/name) for name in SOURCES},
        analysis_freeze_sha256=s.sha(a.FREEZE),original_completion_freeze_sha256=s.sha(h.FREEZE),
        prior_raw_sha256=hashes,prior_ids=[r['id'] for r in prior],prior_transients=transients,
        prior_estimated_cost=str(sum((Decimal(r['estimated_cost']) for r in prior),Decimal(0))),
        pending=[h.descriptor(j) for j in jobs],
        timing='After nine terminal receipts and metadata-only overload diagnosis; no repeats; prior terminals and old classification retained')
    with FREEZE.open('x',encoding='utf-8',newline='\n') as file:file.write(json.dumps(record,indent=2)+'\n')
    return dict(created=True,remaining=1889,prior_preserved=9,tag=TAG)


def verify():
    """Public source/identity verification; no private journal access or calls."""
    from experiments import hf_completion_analysis as a
    a.verify_registration();old=h.verify();r=s.read(FREEZE)
    expect(set(r)=={'schema_version','tag','config','created','base_commit','source_sha256',
        'analysis_freeze_sha256','original_completion_freeze_sha256','prior_raw_sha256','prior_ids',
        'prior_transients','prior_estimated_cost','pending','timing'},'Recovery registration schema')
    expect(r['schema_version']==1 and r['tag']==TAG and r['config']==FIXED,'Recovery identity/configuration')
    expect(r['source_sha256']=={name:s.sha(ROOT/name) for name in SOURCES},'Recovery sources changed')
    expect(r['analysis_freeze_sha256']==s.sha(a.FREEZE) and r['original_completion_freeze_sha256']==s.sha(h.FREEZE),'Recovery parent registrations changed')
    for name in (*SOURCES,'research/'+FREEZE.name):
        expect(h.blob(name,TAG).replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),'Recovery tag differs')
    expect(subprocess.run(['git','merge-base','--is-ancestor',r['base_commit'],TAG+'^{}'],cwd=ROOT,capture_output=True).returncode==0,'Recovery ancestry')
    old_by={d['id']:d for d in old['pending']};prior=set(r['prior_ids']);pending={d['id'] for d in r['pending']}
    expect(len(r['prior_ids'])==len(prior)==9 and len(r['pending'])==len(pending)==1889 and not prior&pending and prior|pending==set(old_by),'Recovery exact unstarted complement')
    expect(all(d==old_by[d['id']] for d in r['pending']),'Recovery request/endpoint changed')
    expect(r['prior_transients']==1 and Decimal(r['prior_estimated_cost']).is_finite() and Decimal(r['prior_estimated_cost'])>=0,'Prior cost/transient commitment')
    expect(set(r['prior_raw_sha256'])=={'plan.json','attempts.jsonl','responses.jsonl','summary.json'},'Prior prefix commitment set')
    return r


def supplement_ledger(out,jobs,plan):
    expect(s.read(Path(out)/'plan.json')==plan,'Recovery plan changed')
    starts,rows,started=c.ledger(Path(out),jobs,dict(ids=plan['ids']))
    expect([x['id'] for x in starts]==plan['ids'][:len(starts)] and [x['id'] for x in rows]==[x['id'] for x in starts],'Recovery dispatch order changed')
    by={j['id']:j for j in jobs}
    for row in rows:
        j=by[row['id']];normal,known=s.safe_response(row.get('native_response'),j['model'])
        expect(row['model']==j['model'] and row['metadata']==j['metadata'] and normal==row['response'] and known is row['known_usage'],'Recovery native normalization/identity changed')
        expect(type(row.get('service_overload')) is bool and type(row.get('capture_failed')) is bool,'Recovery flags invalid')
        receipt=row.get('error_receipt')
        if row['transport'].get('error')=='HTTPError' and not row['capture_failed']:
            expect(type(receipt) is dict and set(receipt)=={'file','sha256'},'Error receipt missing')
            rel=Path(receipt['file'])
            expect(rel.parent==Path('private-errors') and rel.name.startswith('error-') and rel.suffix=='.json' and rel.stem[6:].isdigit(),'Unsafe error path')
            expect(h.raw_sha(Path(out)/rel)==receipt['sha256'],'Error receipt changed')
            saved=s.read(Path(out)/rel)
            expect(saved['http_status']==row['transport'].get('http_status') and explicit_overload(saved['http_status'],saved['error_body']) is row['service_overload'],'Recovery error classification differs')
        else:expect(receipt is None,'Unexpected error receipt')
    return starts,rows,started


def private_completed(owned_lock=False):
    """Validated two-journal union, for explicit completed-analysis export only."""
    registration=verify();jobs,prior,hashes,transients=prior_prefix(owned_lock)
    expect(hashes==registration['prior_raw_sha256'] and [x['id'] for x in prior]==registration['prior_ids'],'Prior nine journal bytes changed')
    expect([h.descriptor(j) for j in jobs]==registration['pending'],'Recovery remaining plan changed')
    plan=dict(freeze_sha256=s.sha(FREEZE),ids=[j['id'] for j in jobs],planned=len(jobs),pending_sha256=s.digest(registration['pending']))
    starts,new,started=supplement_ledger(folder(),jobs,plan)
    expect(len(starts)==len(new)==1889,'Recovery is not terminal-complete')
    summary=s.read(folder()/'summary.json')
    expect(set(summary)=={'planned','returned','unstarted','complete','halted','stop_reason','new_transient_errors',
        'prior_terminals','prior_estimated_cost','new_estimated_cost','combined_estimated_cost','freeze_sha256'},'Recovery summary schema')
    expect(summary['complete'] is True and summary['planned']==1889 and summary['returned']==1889 and summary['unstarted']==0 and summary['freeze_sha256']==s.sha(FREEZE),'Recovery summary incomplete')
    new_cost=sum((Decimal(x['estimated_cost']) for x in new),Decimal(0))
    prior_cost=sum((Decimal(x['estimated_cost']) for x in prior),Decimal(0))
    expect(Decimal(summary['new_estimated_cost'])==new_cost and Decimal(summary['prior_estimated_cost'])==prior_cost==Decimal(registration['prior_estimated_cost']) and Decimal(summary['combined_estimated_cost'])==new_cost+prior_cost,'Recovery summary cost differs')
    expect(summary['prior_terminals']==9 and type(summary['new_transient_errors']) is int and summary['new_transient_errors']==transients+sum(h.transient(x) for x in new),'Recovery summary transient accounting differs')
    combined=prior+new
    combined_summary=dict(planned=1898,returned=1898,unstarted=0,complete=True,halted=summary['halted'],
        stop_reason=summary['stop_reason'],new_transient_errors=transients+sum(h.transient(x) for x in new),
        historical_429_preserved=5,new_estimated_cost=str(sum((Decimal(x['estimated_cost']) for x in combined),Decimal(0))),
        historical_hf_cost='0.880229785',freeze_sha256=s.sha(h.FREEZE),cost_basis='token-rate estimate or full unknown reservation, not reconciled invoice',
        original_audit_returned=11640,original_hf_returned=3880)
    commitments={'hf-completion-v1':hashes,'hf-completion-v2':{name:h.raw_sha(folder()/name) for name in ('plan.json','attempts.jsonl','responses.jsonl','summary.json')}}
    body_by={d['id']:d['request_sha256'] for d in h.verify()['pending']}
    return combined,body_by,combined_summary,commitments


def execute(resume=False,transport=None,clock=None,sleep=None):
    registration=verify();clock=clock or time.monotonic;sleep=sleep or time.sleep
    jobs,prior,hashes,transients=prior_prefix()
    expect(hashes==registration['prior_raw_sha256'] and [h.descriptor(j) for j in jobs]==registration['pending'],'Frozen recovery prefix differs')
    out=folder();plan=dict(freeze_sha256=s.sha(FREEZE),ids=[j['id'] for j in jobs],planned=len(jobs),pending_sha256=s.digest(registration['pending']))
    if out.exists() and not resume:raise ValueError('Recovery exists; continue only exact unstarted complement')
    if not out.exists():out.mkdir(parents=True);(out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8',newline='\n')
    with h.exclusive(out):
        _,_,repeated,_=prior_prefix(True);expect(repeated==hashes,'Prior journal changed during lock acquisition')
        starts,rows,started=supplement_ledger(out,jobs,plan)
        total_transients=transients+sum(h.transient(x) for x in rows)
        expect(not any(h.fatal(x) for x in rows) and total_transients<FIXED['new_transient_allowance'],'Prior recovery fatal/allowance gate')
        prior_cost=Decimal(registration['prior_estimated_cost']);spent=sum((Decimal(x['estimated_cost']) for x in rows),Decimal(0))
        if (out/'summary.json').exists():
            previous=s.read(out/'summary.json');expect(not previous.get('halted') or previous.get('stop_reason')=='operator_stop','Recovery halted; new amendment required')
        pending=[j for j in jobs if j['id'] not in started];secret=h.keys();h.metadata(s.read(h.CATALOG))
        if transport is None:
            opener=CapturingOpener(out/'private-errors',list(secret.values()),clock)
            opener.ordinal=len(list((out/'private-errors').glob('error-*.json')))
            transport=c.Transport(out/'rate-private.jsonl',opener=opener,monotonic=clock)
        stop=out/'STOP';next_start=clock()+30
        if rows:
            elapsed=max(0,time.time()-datetime.fromisoformat(rows[-1]['finished']).timestamp())
            next_start=max(next_start,clock()+max(0,rows[-1]['next_delay_seconds']-elapsed))
        streak=0
        for x in reversed(rows):
            if not h.transient(x):break
            streak+=1
        streak%=8;halted=False;reason='';since_metadata=0
        with (out/'attempts.jsonl').open('a',encoding='utf-8') as attempts,(out/'responses.jsonl').open('a',encoding='utf-8') as responses:
            while pending and not halted:
                try:c.wait_until(next_start,stop,clock,sleep)
                except c.Stopped:halted=True;reason='operator_stop';break
                if since_metadata>=100:
                    try:h.metadata(s.read(h.CATALOG));since_metadata=0
                    except Exception:halted=True;reason='catalog_drift';break
                job=pending[0];reserve=h.reservation(job)
                if prior_cost+spent+reserve>Decimal('2.50'):halted=True;reason='budget';break
                if stop.exists():halted=True;reason='operator_stop';break
                provider,body=s.body_for(job)
                s.durable(attempts,dict(id=job['id'],request_sha256=s.digest(body),provider=provider,reserved_cost=str(reserve),started=now()))
                try:public,native=transport(s.HF+'/chat/completions',secret['HF_TOKEN'],body,timeout=120)
                except Exception:public,native=dict(http_status=None,error='unexpected_request_error'),None
                normal,known=s.safe_response(native,job['model']);ri,ro=s.rates(job['model']);usage=normal.get('usage')
                cost=(usage['input_tokens']*ri+usage['output_tokens']*ro)/1000000 if known else reserve;spent+=cost
                opener=getattr(transport,'opener',None)
                row=dict(id=job['id'],model=job['model'],metadata=job['metadata'],provider=provider,transport=public,
                    response=normal,known_usage=known,estimated_cost=str(cost),native_response=native,
                    service_overload=bool(getattr(opener,'service_overload',False)),capture_failed=bool(getattr(opener,'capture_failed',False)),
                    error_receipt=getattr(opener,'last_receipt',None),finished=now())
                opened=c.numeric(getattr(opener,'last_open_started',None));base=clock() if opened is None else opened;wait_after=0.
                if h.transient(row):
                    total_transients+=1;streak+=1;wait_after=max(60,c.numeric(getattr(opener,'retry_after_delay',0)) or 0)
                    if streak>=8:wait_after=max(wait_after,600);streak=0
                else:streak=0
                next_start=max(base+30,clock()+wait_after);row['next_delay_seconds']=max(0,next_start-clock())
                row=s.scrub(row,secret.values());s.durable(responses,row);rows.append(row);pending.pop(0);since_metadata+=1
                if h.fatal(row):halted=True;reason='fatal_transport_profile_or_capture'
                elif total_transients>=256:halted=True;reason='transient_allowance'
                elif prior_cost+spent>Decimal('2.50'):halted=True;reason='provider_cost_overrun'
        summary=dict(planned=len(jobs),returned=len(rows),unstarted=len(pending),complete=len(rows)==len(jobs),halted=halted,
            stop_reason=reason,new_transient_errors=total_transients,prior_terminals=9,prior_estimated_cost=str(prior_cost),
            new_estimated_cost=str(spent),combined_estimated_cost=str(prior_cost+spent),freeze_sha256=s.sha(FREEZE))
        (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8',newline='\n')
        return summary


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=('freeze','verify','run'));parser.add_argument('--continue-unstarted',action='store_true');args=parser.parse_args()
    result=execute(args.continue_unstarted) if args.command=='run' else globals()[args.command]()
    if args.command=='verify':result=dict(valid=True,remaining=1889,inference_calls=0)
    print(json.dumps(result,indent=2))
