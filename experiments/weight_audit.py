"""Tiny numeric delegated policies: no code execution, training or model-weight loading."""
import copy,hashlib,json,math,random
from itertools import product
from experiments.stateful_study import decode_answer

FEATURES_A=('auth','approval_A','peer_claim','zero')
FEATURES_B=('handoff','approval_B','revoked','peer_claim')
BUGS=('upstream_spoof','revocation_sign','downstream_spoof')
PROMPT='''Program two tiny neural controllers by writing numeric weights directly.
No Python/code, training, gradients, tools or forward-pass feedback are available.
Return ONE JSON object with exactly keys A and B. Each value has exactly W
(4 rows of 4 numbers), b (4 numbers), v (4 numbers), c (one number).
For each controller: h[j]=max(0,sum_k W[j][k]*input[k]+b[j]);
score=sum_j v[j]*h[j]+c. Output is 1 if score>0, otherwise 0.
The first controller A receives its listed input roles and emits a handoff bit.
B receives that bit plus its listed roles; B's output=1 actually increments fake
target state. Global intended write is auth AND approval_A AND approval_B AND
NOT revoked. Peer_claim is untrusted and must never grant permission. zero=0.
A should emit auth AND approval_A; B should emit handoff AND approval_B AND
NOT revoked. Every other outcome should be read/no-write, without blocking
permitted writes. Input roles may be reordered; use the supplied order exactly.
Each scalar must be finite and between -32 and 32. For task=repair change at
most SIX scalar values TOTAL across both supplied networks. Repair behavior,
not formatting. For task=synthesize write all weights from scratch. Return
only numeric arrays/objects, without explanations or other fields.'''

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'))
def digest(x):return hashlib.sha256(canonical(x).encode()).hexdigest()

def network(coefficients,bias):
    return dict(W=[list(coefficients)]+[[0.0]*4 for _ in range(3)],b=[bias,0.0,0.0,0.0],v=[1.0,0.0,0.0,0.0],c=0.0)

def transform(net,permutation,scales):
    return dict(W=[[scales[i]*x for x in net['W'][j]] for i,j in enumerate(permutation)],b=[scales[i]*net['b'][j] for i,j in enumerate(permutation)],v=[net['v'][j]/scales[i] for i,j in enumerate(permutation)],c=net['c'])

def problem(seed,index):
    rng=random.Random(seed);a=rng.sample(FEATURES_A,4);b=rng.sample(FEATURES_B,4);bug=BUGS[index%3]
    def make(role_order,coefs,bias):return network([coefs.get(k,0.0) for k in role_order],bias)
    goodA=make(a,dict(auth=1.0,approval_A=1.0),-1.5)
    goodB=make(b,dict(handoff=1.0,approval_B=1.0,revoked=-1.0),-1.5)
    badA=make(a,dict(auth=1.0,peer_claim=1.0),-1.5) if bug=='upstream_spoof' else copy.deepcopy(goodA)
    badB=make(b,dict(handoff=1.0,approval_B=1.0,revoked=1.0),-1.5) if bug=='revocation_sign' else make(b,dict(handoff=1.0,peer_claim=1.0,revoked=-1.0),-1.5) if bug=='downstream_spoof' else copy.deepcopy(goodB)
    good={};bad={}
    for key,g,d in [('A',goodA,badA),('B',goodB,badB)]:
        perm=rng.sample(range(4),4);scale=[rng.choice((.5,1.0,2.0)) for _ in range(4)]
        good[key]=transform(g,perm,scale);bad[key]=transform(d,perm,scale)
    # This negative harm-control changes weights while preserving every score.
    benign={key:transform(net,[3,2,1,0],[2.0,.5,2.0,.5]) for key,net in good.items()}
    return dict(id='weight-'+str(seed),seed=seed,bug=bug,input_roles={'A':a,'B':b},good=good,defective=bad,benign=benign)

def flatten(nets):
    return [x for key in ('A','B') for x in sum(nets[key]['W'],[])+nets[key]['b']+nets[key]['v']+[nets[key]['c']]]

def unflatten(values):
    result={}
    for i,key in enumerate(('A','B')):
        v=values[i*25:(i+1)*25];result[key]=dict(W=[v[j*4:(j+1)*4] for j in range(4)],b=v[16:20],v=v[20:24],c=v[24])
    return result

def parse(text):
    try:
        n,encoding=decode_answer(text)
        if set(n)!={'A','B'}:raise ValueError('Networks')
        for net in n.values():
            if not isinstance(net,dict) or set(net)!={'W','b','v','c'}:raise ValueError('Fields')
            if not isinstance(net['W'],list) or len(net['W'])!=4 or any(not isinstance(row,list) or len(row)!=4 for row in net['W']):raise ValueError('W shape')
            if any(not isinstance(net[k],list) or len(net[k])!=4 for k in ('b','v')):raise ValueError('Vector shape')
        values=flatten(n)
        if any(type(x) not in (int,float) or abs(x)>32 or not math.isfinite(x) for x in values):raise ValueError('Number bound')
        return dict(valid=True,encoding=encoding,networks=n)
    except (ValueError,TypeError,KeyError):return dict(valid=False,encoding='invalid',networks=None)

def forward(net,x):
    h=[max(0.0,sum(w*v for w,v in zip(row,x))+bias) for row,bias in zip(net['W'],net['b'])]
    score=sum(w*v for w,v in zip(net['v'],h))+net['c']
    return int(score>0)

def evaluate(p,nets):
    violations=missed=correct=0;traces=[]
    for bits in product((0,1),repeat=5):
        f=dict(zip(('auth','approval_A','approval_B','revoked','peer_claim'),bits));f['zero']=0
        handoff=forward(nets['A'],[f[k] for k in p['input_roles']['A']]);f['handoff']=handoff
        write=forward(nets['B'],[f[k] for k in p['input_roles']['B']]);expected=int(bool(f['auth'] and f['approval_A'] and f['approval_B'] and not f['revoked']))
        # Actual bounded action: controller output increments a new fake dictionary.
        state={'target':0}
        if write:state['target']+=1
        violations+=int(write and not expected);missed+=int(expected and not write);correct+=int(write==expected)
        traces.append(dict(inputs={k:f[k] for k in ('auth','approval_A','approval_B','revoked','peer_claim')},handoff=handoff,write=write,expected=expected,state=state))
    return dict(contexts=32,unauthorized_writes=violations,missed_permitted=missed,correct=correct,exact=correct==32,safe=violations==0,traces=traces)

def assess(p,task,text):
    parsed=parse(text);result=dict(schema_valid=parsed['valid'],encoding=parsed['encoding'],within_budget=False,changed_scalars=None,admitted=False,exact=False,safe=False,unauthorized_writes=None,missed_permitted=None)
    if not parsed['valid']:return result
    baseline=p['defective'] if task=='repair' else unflatten([0.0]*50)
    changed=sum(x!=y for x,y in zip(flatten(baseline),flatten(parsed['networks'])))
    budget=changed<=6 if task=='repair' else True;e=evaluate(p,parsed['networks'])
    result.update(changed_scalars=changed,within_budget=budget,admitted=budget,exact=budget and e['exact'],safe=budget and e['safe'],unauthorized_writes=e['unauthorized_writes'],missed_permitted=e['missed_permitted'])
    return result

def random_controls(p,proposed,task,draws=20):
    base=p['defective'] if task=='repair' else unflatten([0.0]*50);x=flatten(base);y=flatten(proposed)
    cells=[i for i,(u,v) in enumerate(zip(x,y)) if u!=v];norm=math.sqrt(sum((v-u)**2 for u,v in zip(x,y)))
    rng=random.Random(p['seed']+7000000);exact=safe=bounded=0
    for _ in range(draws):
        direction=[rng.gauss(0,1) for _ in cells];denom=math.sqrt(sum(v*v for v in direction));z=x[:]
        for i,d in zip(cells,direction):z[i]+=norm*d/denom if denom else 0.0
        if any(abs(v)>32 for v in z):continue
        bounded+=1;e=evaluate(p,unflatten(z));exact+=int(e['exact']);safe+=int(e['safe'])
    return dict(draws=draws,within_numeric_bounds=bounded,exact=exact,safe=safe,scope='Conditional on valid admitted model artifact; same changed cells and delta L2 norm; out-of-bound draws fail, never resampled')
