"""One separately tagged serving diagnostic. Import/verify never use network."""
import argparse
import ctypes
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from experiments import factorial_study as s
from experiments.factorial_continue import retry_after, verify_original_sources
from experiments.access import SameOriginRedirect
from experiments.live_study import config as live_config

CONFIG = s.ROOT/'research/hf-diagnostic-config.json'
FREEZE = s.ROOT/'research/hf-diagnostic-freeze.json'
SOURCES = ('experiments/hf_diagnostic.py','experiments/tests/test_hf_diagnostic.py',
           'research/HF_DIAGNOSTIC_PROTOCOL.md','research/hf-diagnostic-config.json',
           'experiments/factorial_continue.py')
CATEGORIES = {'insufficient_quota':'quota','rate_limit_exceeded':'quota',
              'insufficient_funds':'balance','insufficient_balance':'balance',
              'capacity_exceeded':'capacity','server_overloaded':'capacity',
              'RATE_LIMIT_EXCEEDED':'quota','TOKEN_LIMIT_EXCEEDED':'quota',
              'NOT_ENOUGH_BALANCE':'balance','SERVICE_NOT_AVAILABLE':'capacity'}


class NoDiagnosticRedirect(SameOriginRedirect):
    """Even same-origin redirects would add an unregistered HTTP request."""
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise HTTPError(req.full_url,code,'Diagnostic redirect refused',headers,fp)


def config():
    value = s.read(CONFIG)
    expected = dict(diagnostic_id='hf-serving-diagnostic-v1',registration_tag='hf-serving-diagnostic-v1',
                    model='meta-llama/Llama-3.3-70B-Instruct:novita',hf_input_rate='0.135',hf_output_rate='0.40',
                    prompt='Reply exactly OK',temperature=0,max_tokens=16,input_byte_cap=4096,
                    cap_usd='0.001',error_body_byte_cap=16384,retries=0,
                    output_directory='runs/hf-serving-diagnostic-v1',
                    driver_state='runs/factorial-driver-v1/state.json',
                    finalizer_state='runs/factorial-finalize-v1/state.json',
                    driver_pid=16772,finalizer_pid=82520,minimum_main_429=5)
    if s.canonical(value) != s.canonical(expected):
        raise ValueError('Diagnostic configuration changed')
    original = s.config()
    if (value['model'] != original['hf_model'] or
            any(Decimal(value[name]) != Decimal(original[name]) for name in ('hf_input_rate','hf_output_rate'))):
        raise ValueError('Original serving profile changed')
    if reservation(value) > Decimal(value['cap_usd']):
        raise ValueError('Diagnostic reservation exceeds cap')
    return value


def reservation(value):
    return (value['input_byte_cap']*Decimal(value['hf_input_rate'])+
            value['max_tokens']*Decimal(value['hf_output_rate']))/1000000


def body(value):
    result = dict(model=value['model'],messages=[dict(role='user',content=value['prompt'])],
                  temperature=value['temperature'],max_tokens=value['max_tokens'],stream=False)
    if len(json.dumps(result).encode()) > value['input_byte_cap']:
        raise ValueError('Diagnostic byte cap')
    return result


def freeze():
    """Explicit offline creation only; root commits and tags the resulting JSON."""
    verify_original_sources();value=config()
    if FREEZE.exists():
        raise ValueError('Diagnostic registration already exists')
    if subprocess.check_output(['git','status','--porcelain'],cwd=s.ROOT).strip():
        raise ValueError('Commit source files before registration')
    record=dict(schema_version=1,config=value,source_sha256={name:s.sha(s.ROOT/name) for name in SOURCES},
                original_freeze_sha256=s.sha(s.FREEZE),
                base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=s.ROOT,text=True).strip())
    with FREEZE.open('x',encoding='utf-8') as file:
        file.write(json.dumps(record,indent=2)+'\n')
    return dict(created=True,registration_tag=value['registration_tag'])


def verify():
    verify_original_sources();value=config();record=s.read(FREEZE)
    if set(record) != {'schema_version','config','source_sha256','original_freeze_sha256','base_commit'}:
        raise ValueError('Diagnostic registration schema')
    if (type(record['schema_version']) is not int or record['schema_version'] != 1 or s.canonical(record['config']) != s.canonical(value) or
            record['original_freeze_sha256'] != s.sha(s.FREEZE) or
            record['source_sha256'] != {name:s.sha(s.ROOT/name) for name in SOURCES}):
        raise ValueError('Diagnostic registration/source mismatch')
    for name in (*SOURCES,'research/'+FREEZE.name):
        blob=subprocess.check_output(['git','show',value['registration_tag']+':'+name],cwd=s.ROOT)
        if blob.replace(b'\r\n',b'\n') != (s.ROOT/name).read_bytes().replace(b'\r\n',b'\n'):
            raise ValueError('Diagnostic tag mismatch')
    if subprocess.run(['git','merge-base','--is-ancestor',record['base_commit'],
                       value['registration_tag']+'^{}'],cwd=s.ROOT,capture_output=True).returncode:
        raise ValueError('Diagnostic registration ancestry')
    return value


def pid_alive(pid):
    if type(pid) is not int or pid <= 0:
        raise ValueError('Invalid guard PID')
    if os.name == 'nt':
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.restype=ctypes.c_void_p
        kernel.OpenProcess.argtypes=(ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong)
        kernel.GetExitCodeProcess.argtypes=(ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong))
        kernel.CloseHandle.argtypes=(ctypes.c_void_p,)
        handle=kernel.OpenProcess(0x1000,False,pid)
        if not handle:
            if ctypes.get_last_error()==87:return False
            raise ValueError('Cannot establish process termination')
        try:
            code=ctypes.c_ulong()
            if not kernel.GetExitCodeProcess(handle,ctypes.byref(code)):
                raise ValueError('Cannot establish process termination')
            return code.value==259
        finally:kernel.CloseHandle(handle)
    try:os.kill(pid,0)
    except ProcessLookupError:return False
    except PermissionError:return True
    return True


def guards(value):
    """Inspect operational metadata only; never read scientific response text."""
    for name,pidname,stage in (('driver_state','driver_pid','audits'),
                               ('finalizer_state','finalizer_pid','collection')):
        state=s.read(s.ROOT/value[name])
        if state.get('status')!='stopped' or state.get('stage')!=stage:
            raise ValueError('Main driver/finalizer has not stopped')
        if name=='finalizer_state' and state.get('completed')!=[]:
            raise ValueError('Authoring finalizer state changed')
        if state.get('pid') != value[pidname] or pid_alive(value[pidname]):
            raise ValueError('Known driver/finalizer is active or mismatched')
    audits=s.folder('audits')
    if (audits/'STOP').exists():
        raise ValueError('Operator STOP also blocks diagnostic')
    if (audits/'continuation.lock').exists() or s.read(audits/'summary.json').get('halted') is not True:
        raise ValueError('Collector has not reached a terminal halt')
    total=0
    for stage in ('smoke','issue','delegate','settle','audits'):
        folder=s.folder(stage)
        if not (folder/'attempts.jsonl').exists() or not (folder/'responses.jsonl').exists():
            raise ValueError('Missing phase ledger')
        # Parse lines privately, retain only IDs and transport/provider metadata.
        starts=[];terminals=[]
        for filename,target in (('attempts.jsonl',starts),('responses.jsonl',terminals)):
            with (folder/filename).open(encoding='utf-8') as file:
                for line in file:
                    row=json.loads(line);target.append(row['id'])
                    if stage=='audits' and filename=='responses.jsonl':
                        total+=int(row.get('provider')=='hf' and row.get('transport',{}).get('http_status')==429)
        if len(set(starts))!=len(starts) or len(set(terminals))!=len(terminals) or set(starts)!=set(terminals):
            raise ValueError('Duplicate or unresolved main phase start')
    if total < value['minimum_main_429']:
        raise ValueError('Main registered hard stop has not been reached')


def category(raw):
    try:
        parsed=json.loads(raw)
        error=parsed.get('error') if isinstance(parsed,dict) else None
        code=error.get('code') if isinstance(error,dict) else parsed.get('code') if isinstance(parsed,dict) else None
        return CATEGORIES.get(code,'notdeterminable') if isinstance(code,str) else 'notdeterminable'
    except (ValueError,TypeError):return 'notdeterminable'


def request(url,key,output,label,payload=None,opener=None,secrets=()):
    """Bound and scrub private receipts; return safe metadata plus private data."""
    if url not in (s.HF+'/models',s.HF+'/chat/completions'):
        raise ValueError('Only registered HTTPS HF routes are allowed')
    opener=opener or build_opener(NoDiagnosticRedirect())
    req=Request(url,data=None if payload is None else json.dumps(payload).encode(),
                headers={'Authorization':'Bearer '+key,'Content-Type':'application/json',
                         'User-Agent':'swarm-alignment-pilot/0.1'},method='GET' if payload is None else 'POST')
    private={};native=None;public=dict(http_status=None,category='notdeterminable')
    try:
        with opener.open(req,timeout=120) as reply:
            limit=2097152 if payload is None else 65536
            raw=reply.read(limit+1)
            if len(raw)>limit:raise ValueError('Successful receipt exceeds private byte cap')
            native=json.loads(raw)
            public['http_status']=reply.status
            private=dict(response_headers=dict(reply.headers),native_response=native)
    except HTTPError as error:
        raw=error.read(16384).decode('utf-8',errors='replace')
        public.update(http_status=error.code,category=category(raw))
        delay=retry_after(error.headers.get('Retry-After')) if error.headers else None
        if delay is not None:public['retry_after_seconds']=delay
        private=dict(response_headers=dict(error.headers or {}),error_body=raw,error_body_byte_cap=16384)
    except (URLError,TimeoutError,OSError,ValueError):
        private=dict(error='transport_or_json_error')
    clean=s.scrub(private,list(secrets)+[key])
    (output/(label+'-private.json')).write_text(json.dumps(clean,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
    return public,native


def catalog_matches(data,value):
    if not isinstance(data,dict) or not isinstance(data.get('data'),list):return False
    model,provider=value['model'].rsplit(':',1)
    candidates=[entry for item in data['data'] if isinstance(item,dict) and item.get('id')==model
                for entry in item.get('providers',[]) if isinstance(entry,dict) and entry.get('provider')==provider]
    if len(candidates)!=1 or candidates[0].get('status')!='live':return False
    try:return all(Decimal(str(candidates[0]['pricing'][name]))==Decimal(value['hf_'+name+'_rate'])
                   for name in ('input','output'))
    except (KeyError,ValueError,ArithmeticError,TypeError,AttributeError):return False


def run(authorized=False,opener=None):
    if not authorized:raise ValueError('Explicit --run required')
    value=verify();guards(value)
    output=(s.ROOT/value['output_directory']).resolve()
    if not output.is_relative_to((s.ROOT/'runs').resolve()):raise ValueError('Ignored output required')
    keys=s.credentials();key=keys.get('HF_TOKEN')
    if not key:raise ValueError('HF credential unavailable')
    output.mkdir(parents=True,exist_ok=False)
    with (output/'events.jsonl').open('x',encoding='utf-8') as events:
        s.durable(events,dict(event='catalog_start'))
        try:
            public,data=request(s.HF+'/models',key,output,'catalog',opener=opener,secrets=keys.values())
        except Exception:
            public,data=dict(http_status=None,category='notdeterminable'),None
        s.durable(events,dict(event='catalog_terminal',**public))
        if public['http_status']!=200:return public
        if not catalog_matches(data,value):return dict(http_status=None,category='notdeterminable')
        guards(value)  # Refuse if anything restarted during the GET.
        payload=body(value)
        s.durable(events,dict(event='inference_start',request_sha256=s.digest(payload),
                              reserved_cost=str(reservation(value)),started=datetime.now(timezone.utc).isoformat()))
        try:
            public,data=request(s.HF+'/chat/completions',key,output,'inference',payload,
                                opener=opener,secrets=keys.values())
        except Exception:
            public,data=dict(http_status=None,category='notdeterminable'),None
        usage=(data or {}).get('usage') if isinstance(data,dict) else None
        known=(isinstance(usage,dict) and all(type(usage.get(name)) is int and usage[name]>=0
                                            for name in ('prompt_tokens','completion_tokens')))
        cost=((usage['prompt_tokens']*Decimal(value['hf_input_rate'])+
               usage['completion_tokens']*Decimal(value['hf_output_rate']))/1000000 if known else reservation(value))
        profile_ok=(public['http_status']==200 and known and
                    data.get('model') in live_config()['hf_allowed_returned_models'] and
                    usage['prompt_tokens']<=value['input_byte_cap'] and usage['completion_tokens']<=value['max_tokens'])
        s.durable(events,dict(event='inference_terminal',**public,known_usage=known,
                              estimated_cost=str(cost),profile_ok=profile_ok,
                              reported_cost_over_cap=cost>Decimal(value['cap_usd'])))
        return public


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('freeze','verify','run'))
    parser.add_argument('--run',action='store_true',dest='authorized')
    args=parser.parse_args()
    if args.command=='run':result=run(args.authorized)
    elif args.command=='freeze':result=freeze()
    else:verify();result={'valid':True,'mode':'offline source/tag verification'}
    print(json.dumps(result))


if __name__=='__main__':main()
