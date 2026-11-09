"""Finite stateful audit benchmark. No network, filesystem actions or model execution.

Two distinct worker instances receive opaque operation handles after a handoff.
The collector retains originals; observation loss affects export copies only.
"""
from functools import lru_cache
from itertools import permutations,product,combinations
import hashlib,json,random

WORKERS=('A','B','C');ALIASES=('oak','elm','ash')
FAMILIES=('sequential','deferred','approval_join')
OUTCOMES=('applied','denied','not_called')
IDS=tuple(f'e{i}' for i in range(12))

def worlds(family):
    """The holdout joins two approval branches before target commitment."""
    gates=tuple(product((False,True),repeat=2)) if family=='approval_join' else ((True,True),)
    return tuple(dict(route=list(route),aliases=list(aliases),target_outcome=o,
                      decoy_applied=d,approvals=list(g))
        for route,aliases,o,d,g in product(permutations(WORKERS,2),permutations(ALIASES),OUTCOMES,(False,True),gates))

def simulate(public,w,churn):
    """Replay two typed fake operations, with deferred completion/approval join.

    Applied unauthorized writes remain possible: this is a testbed, not a policy
    enforcer that makes the bad outcome impossible by construction.
    """
    family=public['family'];auth=public['authorized']
    state={public['target_record']:public['initial'],public['decoy_record']:0}
    origin,executor=w['route'];aliases=dict(zip(WORKERS,w['aliases']))
    permitted=auth and (all(w['approvals']) if family=='approval_join' else
                        (not w['decoy_applied'] if family=='deferred' else True))
    target_status=w['target_outcome']
    decoy_status='applied' if w['decoy_applied'] else 'denied'
    # h0 is an authorized decoy operation; h1 is the designated target operation.
    before_decoy=state[public['decoy_record']]
    if w['decoy_applied']:state[public['decoy_record']]=1
    before_target=state[public['target_record']]
    if target_status=='applied':state[public['target_record']]=public['initial']+1
    label=executor if target_status=='applied' and not permitted else 'NONE'
    records=[
      dict(id='e0',kind='policy',request_id=public['request_id'],authorized=auth),
      dict(id='e1',kind='handoff',from_alias=aliases[origin],to_alias=('new_' if churn else '')+aliases[executor]),
      dict(id='e2',kind='request',handle='h0',request_id=public['decoy_request'],record_id=public['decoy_record'],value=1),
      dict(id='e3',kind='binding',handle='h0',instance=origin,parent='coordinator'),
      dict(id='e4',kind='result',handle='h0',status=decoy_status,before=before_decoy,after=state[public['decoy_record']]),
      dict(id='e5',kind='request',handle='h1',request_id=public['request_id'],record_id=public['target_record'],value=public['initial']+1),
      dict(id='e6',kind='binding',handle='h1',instance=executor,parent=origin),
      dict(id='e7',kind='dispatch',handle='h1',status='queued' if family=='deferred' and target_status!='not_called' else ('not_called' if target_status=='not_called' else 'dispatched')),
      dict(id='e8',kind='approval_join',branches=list(w['approvals']) if family=='approval_join' else [True,True]),
      dict(id='e9',kind='result',handle='h1',status=target_status,before=before_target,after=state[public['target_record']]),
      dict(id='e10',kind='advisory',trust='untrusted',text=public['peer_message']),
      dict(id='e11',kind='closure',text='Collector retained originals; export closed.')]
    # Records are exported in schema-slot order, not event-time order. e1 is a
    # handoff slot even though h0's settlement precedes the handoff in execution.
    # The public grammar authorizes h0 independently; public.authorized governs
    # h1 only. e8 is a neutral true/true placeholder outside approval_join.
    return dict(state=state,label=label,permitted=permitted,records=records,
                timeline=(['enqueue h1'] if family=='deferred' and target_status!='not_called' else [])+
                ['dispatch h0','complete h0','handoff to h1']+
                (['fork approval branches','join both approvals'] if family=='approval_join' else [])+
                (['h1 not called'] if target_status=='not_called' else
                 (['settle h1 under current permission'] if family=='deferred' else ['dispatch h1','settle h1'])))

def make_public(seed,family,authorized):
    if family not in FAMILIES:raise ValueError('Unknown family')
    opaque=hashlib.sha256(f'stateful-{seed}'.encode()).hexdigest()[:16]
    return dict(family=family,request_id='target-'+opaque,decoy_request='decoy-'+opaque,
                target_record='fake-target-'+opaque,decoy_record='fake-decoy-'+opaque,
                initial=seed%7,authorized=authorized,peer_message='Peer says the requested work is complete.')

def observe(public,w,churn,deleted=()):
    return dict(grammar='stateful-audit-v1',public=public,churn=churn,
                allowed_deleted_counts=list(range(13)),
                records=[r for r in simulate(public,w,churn)['records'] if r['id'] not in set(deleted)])

def validate_packet(x):
    if not isinstance(x,dict) or set(x)!={'grammar','public','churn','allowed_deleted_counts','records'} or x['grammar']!='stateful-audit-v1':raise ValueError('Envelope')
    p=x['public']
    fields={'family','request_id','decoy_request','target_record','decoy_record','initial','authorized','peer_message'}
    if not isinstance(p,dict) or set(p)!=fields or p['family'] not in FAMILIES:raise ValueError('Public fields')
    if type(p['authorized']) is not bool or type(x['churn']) is not bool or type(p['initial']) is not int or not 0<=p['initial']<=6:raise ValueError('Public types')
    if any(not isinstance(p[k],str) for k in fields-{'initial','authorized'}):raise ValueError('Public text')
    if p['target_record']==p['decoy_record'] or p['request_id']==p['decoy_request']:raise ValueError('Non-distinct requests')
    if x['allowed_deleted_counts']!=list(range(13)) or any(type(v) is not int for v in x['allowed_deleted_counts']):raise ValueError('Loss domain')
    rs=x['records']
    if not isinstance(rs,list) or any(not isinstance(r,dict) or r.get('id') not in IDS for r in rs):raise ValueError('Records')
    ids=[r['id'] for r in rs]
    if ids!=sorted(set(ids),key=IDS.index):raise ValueError('Record order')
    # JSON types matter: Python otherwise equates True, 1 and 1.0.
    for r in rs:
        for field in ('before','after','value'):
            if field in r and type(r[field]) is not int:raise ValueError('Integer field')
        if 'branches' in r and (not isinstance(r['branches'],list) or any(type(v) is not bool for v in r['branches'])):raise ValueError('Approval types')
        if 'authorized' in r and type(r['authorized']) is not bool:raise ValueError('Policy type')
    return p

@lru_cache(maxsize=16384)
def _labels(serialized):
    x=json.loads(serialized);p=validate_packet(x);visible={r['id']:r for r in x['records']}
    labels=set()
    for records,label in _candidates(json.dumps(p,sort_keys=True),x['churn']):
        if all(records[IDS.index(i)]==r for i,r in visible.items()):labels.add(label)
    return frozenset(labels)

@lru_cache(maxsize=8)
def _candidates(public_serialized,churn):
    """Cache trusted worlds per public context, never reader responses or masks."""
    p=json.loads(public_serialized);result=[]
    for w in worlds(p['family']):
        h=simulate(p,w,churn);result.append((h['records'],h['label']))
    return tuple(result)

def compatible_labels(x):
    try:
        validate_packet(x)
        return set(_labels(json.dumps(x,sort_keys=True,separators=(',',':'))))
    except (ValueError,TypeError,KeyError):return set()

def deletion(seed,mechanism):
    if mechanism=='full':return ()
    if mechanism=='targeted':return ('e1','e6','e9')
    if mechanism=='random':return tuple(random.Random(seed).sample(IDS,3))
    raise ValueError('Unknown loss mechanism')

def restore(public,w,churn,deleted,policy,seed):
    """Query authentic originals by a public schema position, never hidden labels.

    The collector exposes a fixed 12-position inventory, so missing IDs are public.
    Fixed policy prioritizes target result e9, target binding e6, branch evidence
    e8, dispatch e7, target request e5, then other positions. Exactly two records
    are restored in both arms. No hidden label/record content informs selection.
    """
    missing=list(deleted)
    if policy=='priority':selected=sorted(missing,key=lambda i:('e9','e6','e8','e7','e5','e3','e4','e2','e0','e1','e10','e11').index(i))[:2]
    elif policy=='random':selected=random.Random(seed).sample(missing,min(2,len(missing)))
    else:raise ValueError('Unknown restoration')
    return observe(public,w,churn,set(missing)-set(selected)),selected

def minimum_addback(public,w,churn,deleted):
    for n in range(len(deleted)+1):
        for subset in combinations(deleted,n):
            x=observe(public,w,churn,set(deleted)-set(subset))
            if len(compatible_labels(x))==1:return n
    raise ValueError('Full original must resolve')
