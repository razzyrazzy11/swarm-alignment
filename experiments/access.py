"""Credential-safe, read-only service checks. Never log request headers or keys."""
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
ADAPTION='https://api.prod.adaptionlabs.ai/api/v1'

class SameOriginRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        old=urlparse(req.full_url);new=urlparse(newurl)
        if new.scheme!='https' or new.netloc!=old.netloc:
            raise HTTPError(req.full_url,code,'Cross-origin redirect refused',headers,None)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def credentials(path=None):
    """Parse only literal key=value lines; never execute a dotenv file."""
    allowed={'ADAPTION_API_KEY','HF_TOKEN'}
    values={}
    path=ROOT/'.env' if path is None else Path(path)
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            name,sep,value=line.partition('=')
            name=name.strip()
            if sep and name in allowed:
                value=value.strip()
                if len(value)>1 and value[0]==value[-1] and value[0] in ('"',"'"):
                    value=value[1:-1]
                values[name]=value
    for name in allowed:
        if os.environ.get(name):
            values[name]=os.environ[name]
    return {k:v for k,v in values.items() if v and 'replace_locally' not in v and not v.startswith('YOUR_')}

def request_json(url,key,body=None,timeout=40):
    """Return data privately; errors expose only status/class, never response text."""
    request=Request(url,data=None if body is None else json.dumps(body).encode(),
                    headers={'Authorization':'Bearer '+key,'Content-Type':'application/json','User-Agent':'swarm-alignment-pilot/0.1'},
                    method='GET' if body is None else 'POST')
    start=time.monotonic()
    try:
        with build_opener(SameOriginRedirect()).open(request,timeout=timeout) as response:
            data=json.load(response)
            return {'http_status':response.status,'latency_seconds':round(time.monotonic()-start,3)},data
    except HTTPError as exc:
        return {'http_status':exc.code,'latency_seconds':round(time.monotonic()-start,3),'error':'HTTPError'},None
    except (URLError,TimeoutError,OSError,ValueError):
        return {'http_status':None,'latency_seconds':round(time.monotonic()-start,3),'error':'transport_or_json_error'},None

def check_access():
    keys=credentials()
    report={'mode':'read-only authentication/catalog checks; no inference or training',
            'adaption_key_present':'ADAPTION_API_KEY' in keys,'hf_token_present':'HF_TOKEN' in keys}
    if 'ADAPTION_API_KEY' in keys:
        for label,path in [('hosted_models','/models?type=hosted'),('training_catalog','/autoscientist/models'),('datasets_read','/datasets')]:
            status,data=request_json(ADAPTION+path,keys['ADAPTION_API_KEY'])
            if label=='hosted_models' and isinstance(data,dict):
                status['model_ids']=[m['id'] for m in data.get('data',[]) if isinstance(m,dict) and isinstance(m.get('id'),str)]
            status['access_confirmed']=status.get('http_status')==200
            report[label]=status
    if 'HF_TOKEN' in keys:
        status,data=request_json('https://huggingface.co/api/whoami-v2',keys['HF_TOKEN'])
        status['access_confirmed']=status.get('http_status')==200
        if isinstance(data,dict):
            status['is_pro']=data.get('isPro')
            auth=data.get('auth') or {}
            status['authentication_type']=auth.get('type')
        report['hugging_face_identity']=status
    report['billing_caveat']='Catalog/identity access does not prove award coverage, remaining balance, training-launch permission or inference billing.'
    return report

if __name__=='__main__':
    report=check_access()
    out=ROOT/'runs/access-check'
    out.mkdir(parents=True,exist_ok=True)
    (out/'access.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
