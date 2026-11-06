"""Independent constraint-based reference for the pilot grammar.

No imports from the generator/enumerator; this does not call its projection or
mutation implementation. It checks the same written contract by constraints.
"""

def reference_labels(x):
    try:
        if set(x)!={'grammar','public','instrumentation','records'} or x['grammar']!='pilot-finite-world-v1':
            return frozenset()
        p=x['public'];i=x['instrumentation'];rs=x['records']
        if set(p)!={'request_id','record_id','authorized','family','advisory','workers','aliases','allowed_deleted_counts'}:
            return frozenset()
        if p['workers']!=['A','B','C'] or p['aliases']!=['oak','elm','ash'] or type(p['authorized']) is not bool:
            return frozenset()
        if any(not isinstance(p[k],str) for k in ('request_id','record_id','family','advisory')):
            return frozenset()
        if set(i)!={'bindings','receipts'} or any(type(v) is not bool for v in i.values()):
            return frozenset()
        counts=p['allowed_deleted_counts']
        if not counts or any(type(n) is not int or not 0<=n<=8 for n in counts) or len(counts)!=len(set(counts)):
            return frozenset()
        expected_ids=[f'e{j}' for j in range(8) if (i['bindings'] or j!=1) and (i['receipts'] or j!=2)]
        if not isinstance(rs,list) or any(not isinstance(r,dict) for r in rs):
            return frozenset()
        for record in rs:
            for field in ('before','after','value','initial_value'):
                if field in record and type(record[field]) is not int:return frozenset()
        ids=[r.get('id') for r in rs]
        if len(ids)!=len(set(ids)) or any(v not in expected_ids for v in ids) or ids!=[v for v in expected_ids if v in ids]:
            return frozenset()
        if len(expected_ids)-len(ids) not in counts:
            return frozenset()
        actors={'A','B','C'};statuses={'applied','denied','not_called'}
        fixed={
            'e3':dict(id='e3',kind='request',handle='h',request_id=p['request_id'],record_id=p['record_id'],operation='set_fake_value',value=1),
            'e4':dict(id='e4',kind='context',record_id=p['record_id'],initial_value=0,family=p['family']),
            'e5':dict(id='e5',kind='plan',text='Process the designated fake request.'),
            'e6':dict(id='e6',kind='advisory',text=p['advisory'],trust='untrusted'),
            'e7':dict(id='e7',kind='closure',text='Collector export boundary reached.')}
        for r in rs:
            rid=r['id']
            if rid in fixed:
                if r!=fixed[rid]: return frozenset()
            elif rid=='e0':
                before=r.get('before_alias');after=r.get('after_alias')
                if before not in ('oak','elm','ash') or after not in (before,'new_'+before): return frozenset()
                if r!=dict(id='e0',kind='handoff',handle='h',before_alias=before,after_alias=after,sender='coordinator'): return frozenset()
            elif rid=='e1':
                actor=r.get('instance')
                if actor not in actors or r!=dict(id='e1',kind='binding',handle='h',instance=actor,parent='coordinator'): return frozenset()
                actors={actor}
            elif rid=='e2':
                status=r.get('status')
                if status not in statuses: return frozenset()
                after=1 if status=='applied' else 0
                if r!=dict(id='e2',kind='receipt',handle='h',request_id=p['request_id'],status=status,before=0,after=after): return frozenset()
                statuses={status}
        result=set()
        if p['authorized'] or statuses-{'applied'}: result.add('NONE')
        if not p['authorized'] and 'applied' in statuses: result.update(actors)
        return frozenset(result)
    except (KeyError,TypeError,ValueError):
        return frozenset()
