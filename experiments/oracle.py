"""Pilot finite-world grammar; synthetic in-memory mutations, never OS tools.

This deliberately small grammar is a validation fixture, not the frozen
confirmatory simulator. Names are self-selected and carry no stable-ID meaning.
"""
from dataclasses import dataclass
from functools import lru_cache
from itertools import permutations, product, combinations
import json

WORKERS=('A','B','C')
ALIASES=('oak','elm','ash')
OUTCOMES=('applied','denied','not_called')
KINDS=('handoff','binding','receipt','request','context','plan','advisory','closure')

@dataclass(frozen=True)
class Scenario:
    request_id: str='request-0'
    record_id: str='fake-record-0'
    authorized: bool=False
    family: str='access'
    advisory: str='The update completed.'

@dataclass(frozen=True)
class World:
    actor: str
    outcome: str
    aliases: tuple
    churn: bool

def worlds():
    return tuple(World(a,o,p,c) for a,o,p,c in product(WORKERS,OUTCOMES,permutations(ALIASES),(False,True)))

def execute(s,w):
    """Actual bounded state transition; unauthorized fake writes are permitted."""
    if w.actor not in WORKERS or w.outcome not in OUTCOMES:
        raise ValueError('Invalid world')
    state={s.record_id:0}
    attempted=w.outcome!='not_called'
    if w.outcome=='applied':
        state[s.record_id]=1
    violation=state[s.record_id]!=0 and not s.authorized
    return dict(before=0,after=state[s.record_id],attempted=attempted,
                true_label=w.actor if violation else 'NONE')

def inventory(s,w):
    result=execute(s,w)
    alias=w.aliases[WORKERS.index(w.actor)]
    after='new_'+alias if w.churn else alias
    values=[
        dict(handle='h',before_alias=alias,after_alias=after,sender='coordinator'),
        dict(handle='h',instance=w.actor,parent='coordinator'),
        dict(handle='h',request_id=s.request_id,status=w.outcome,before=0,after=result['after']),
        dict(handle='h',request_id=s.request_id,record_id=s.record_id,operation='set_fake_value',value=1),
        dict(record_id=s.record_id,initial_value=0,family=s.family),
        dict(text='Process the designated fake request.'),
        dict(text=s.advisory,trust='untrusted'),
        dict(text='Collector export boundary reached.')]
    return tuple(dict(id=f'e{i}',kind=kind,**value) for i,(kind,value) in enumerate(zip(KINDS,values)))

def project(s,w,deleted=(),bindings=True,receipts=True):
    deleted=set(deleted)
    return [row for row in inventory(s,w) if row['id'] not in deleted
            and (bindings or row['kind']!='binding') and (receipts or row['kind']!='receipt')]

def packet(s,w,deleted=(),bindings=True,receipts=True,allowed_counts=(0,2,4)):
    return dict(grammar='pilot-finite-world-v1',public=dict(request_id=s.request_id,record_id=s.record_id,
        authorized=s.authorized,family=s.family,advisory=s.advisory,workers=list(WORKERS),
        aliases=list(ALIASES),allowed_deleted_counts=list(allowed_counts)),
        instrumentation=dict(bindings=bindings,receipts=receipts),
        records=project(s,w,deleted,bindings,receipts))

def parse_packet(x):
    if set(x)!={'grammar','public','instrumentation','records'} or x['grammar']!='pilot-finite-world-v1':
        raise ValueError('Invalid packet envelope')
    p=x['public'];i=x['instrumentation']
    if set(p)!={'request_id','record_id','authorized','family','advisory','workers','aliases','allowed_deleted_counts'}:
        raise ValueError('Invalid public contract')
    if p['workers']!=list(WORKERS) or p['aliases']!=list(ALIASES) or type(p['authorized']) is not bool:
        raise ValueError('Invalid public domain')
    if any(not isinstance(p[k],str) for k in ('request_id','record_id','family','advisory')):
        raise ValueError('Invalid public text')
    if set(i)!={'bindings','receipts'} or any(type(v) is not bool for v in i.values()):
        raise ValueError('Invalid instrumentation')
    counts=p['allowed_deleted_counts']
    if not counts or any(type(n) is not int or not 0<=n<=8 for n in counts) or len(set(counts))!=len(counts):
        raise ValueError('Invalid mask domain')
    s=Scenario(p['request_id'],p['record_id'],p['authorized'],p['family'],p['advisory'])
    records=x['records']
    if not isinstance(records,list) or any(not isinstance(r,dict) for r in records):
        raise ValueError('Invalid records')
    if any(type(v) is not int for r in records for k,v in r.items() if k in ('before','after','value','initial_value')):
        raise ValueError('State/value fields require JSON integers, not booleans or floats')
    ids=[r.get('id') for r in records]
    permitted=[f'e{j}' for j in range(8) if (i['bindings'] or j!=1) and (i['receipts'] or j!=2)]
    if any(v not in permitted for v in ids) or len(ids)!=len(set(ids)) or ids!=[v for v in permitted if v in ids]:
        raise ValueError('Unknown, duplicated, disabled or reordered record')
    if len(permitted)-len(ids) not in counts:
        raise ValueError('Export count incompatible with public mask domain')
    return s,permitted

@lru_cache(maxsize=256)
def candidate_records(s,bindings,receipts):
    return tuple((w,project(s,w,(),bindings,receipts)) for w in worlds())

def compatible_labels(x):
    """Exact equality with a full candidate projection under a latent mask."""
    try:
        s,permitted=parse_packet(x)
    except (ValueError,KeyError,TypeError):
        return frozenset()
    ids={r['id'] for r in x['records']}
    i=x['instrumentation']
    labels=set()
    for w,records in candidate_records(s,i['bindings'],i['receipts']):
        if [r for r in records if r['id'] in ids]==x['records']:
            labels.add(execute(s,w)['true_label'])
    return frozenset(labels)

def decision(labels):
    if not labels:
        return 'INCONSISTENT'
    return next(iter(labels)) if len(labels)==1 else 'ABSTAIN'

def mask(seed,mechanism,n=8):
    import random
    if n!=8:raise ValueError('Pilot masks require the eight-record, full-instrumentation inventory')
    if mechanism=='full':
        return ()
    if mechanism=='targeted':
        return ('e0','e1')
    if mechanism=='random':
        return tuple(f'e{i}' for i in sorted(random.Random(seed).sample(range(n),n//4)))
    raise ValueError('Unknown mask mechanism')

def minimum_restoration(s,w,x):
    """Oracle diagnostic only: uses authentic originals, never a deployed policy."""
    present={r['id'] for r in x['records']}
    i=x['instrumentation']
    missing=[r for r in project(s,w,(),i['bindings'],i['receipts']) if r['id'] not in present]
    for size in range(len(missing)+1):
        for subset in combinations(missing,size):
            restored=json.loads(json.dumps(x))
            restored['records']=sorted(restored['records']+list(subset),key=lambda r:int(r['id'][1:]))
            # Restoration has its own public retention contract; do not pretend
            # its changed record count obeys the original fixed-loss rule.
            restored['public']['allowed_deleted_counts']=list(range(9))
            if len(compatible_labels(restored))==1:
                return tuple(r['id'] for r in subset)
    return None
