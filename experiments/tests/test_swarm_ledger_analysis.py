"""Independent synthetic controls for grouping, causality and artifact admission."""
from copy import deepcopy
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from experiments import swarm_ledger_analysis as a
from experiments.tests.test_swarm_ledger_study import ctx,previous


class AnalysisTests(unittest.TestCase):
    def setUp(self):self.context=ctx();self.src=a.study.source_worlds([self.context],previous(self.context))[0]

    def scored(self,label='NONE',source=None,view='full',admitted=True):
        source=source or self.src;packet={v['view']:v['packet'] for v in a.engine.views(source['public'],source['world'])}[view]
        labels=a.reference.reference_labels(packet)
        metadata={k:source[k] for k in ('source_id','block_id','arm','worker_profile','policy','layout','split')}
        metadata.update(view=view,procedure='direct',packet_sha256=a.engine.digest(packet),compatible_labels=sorted(labels),restored_ids=[],restored_bytes=0)
        job=a.study.job('case','g26',[dict(role='system',content=a.study.DIRECT),dict(role='user',content=a.engine.serialize(packet,source['layout']))],metadata)
        text=json.dumps(dict(status='EXECUTOR' if label in list('ABCDE') else label,worker_id=label if label in list('ABCDE') else None))
        row=dict(response=dict(output_text=text,status='completed',usage=dict(input_tokens=1,output_tokens=1)),
                 transport=dict(http_status=200 if admitted else 503),known_usage=True,anomaly=False,estimated_cost='0.01')
        return a.score_case(job,row,source,packet),job,row,packet

    def test_ungated_semantics_vs_admission_and_strict_encoding(self):
        case,job,row,packet=self.scored(admitted=False)
        self.assertTrue(case['correct_definite']);self.assertFalse(case['gated_correct_definite'])
        row['response']['output_text']='```json\n'+row['response']['output_text']+'\n```'
        fenced=a.score_case(job,row,self.src,packet)
        self.assertTrue(fenced['semantic_valid']);self.assertFalse(fenced['strict_json'])

    def test_actual_positive_exact_attribution_and_assigned_clearance_denominators(self):
        src=deepcopy(self.src);src['world']['dx']=2;src['world']['dy']=2
        src['host']=a.engine.simulate(src['public'],src['world'])
        right=self.scored(src['world']['y_worker'],src)[0]
        wrong=self.scored(next(x for x in 'ABCDE' if x!=src['world']['y_worker']),src)[0]
        none=self.scored('NONE',src)[0];negative=self.scored()[0]
        result=a.metric_summary([right,wrong,none,negative])
        self.assertEqual(result['exact_attribution_recall'],1/3)
        self.assertEqual(result['any_executor_on_positive'],2/3)
        self.assertEqual(result['dangerous_clearance_itt'],1/4)
        self.assertEqual(result['unsafe_none_on_positive'],1/3)
        onlynegative=a.metric_summary([negative]);self.assertIsNone(onlynegative['exact_attribution_recall'])

    def test_ambiguous_missing_evidence_has_own_abstention_target(self):
        case,_,_,_=self.scored('ABSTAIN',view='selective_loss')
        self.assertFalse(case['answerable']);self.assertTrue(case['correct_supported'])
        self.assertFalse(case['correct_definite'])

    def test_baselines_count_sources_not_reader_calls_and_credit_abstention(self):
        negative=self.scored()[0];positive=deepcopy(negative)
        positive.update(source_id='positive',block_id='positive',actual_label='D',actual_positive=True,compatible_labels=['D'])
        extra=deepcopy(negative);extra['profile_id']='other-reader'
        ambiguous=self.scored('ABSTAIN',view='selective_loss')[0]
        result=a.baseline_summary([negative,positive,extra,ambiguous])
        full=result['full:honest'];self.assertEqual(full['unique_source_views'],2)
        self.assertEqual(full['always_none']['correct_supported_rate'],.5)
        self.assertEqual(full['actual_positive'],1);self.assertEqual(full['actual_negative'],1)
        missing=result['selective_loss:honest'];self.assertEqual(missing['always_abstain']['correct_supported'],1)
        self.assertEqual(missing['finite_domain_reference']['correct_definite'],0)
        self.assertFalse(missing['finite_domain_reference']['learned_monitor'])
        extra['compatible_labels']=['D']
        with self.assertRaises(ValueError):a.baseline_summary([negative,extra])

    def test_reader_packet_and_wording_corruption_rejected(self):
        _,job,row,packet=self.scored();job['messages'][1]['content']+=' extra'
        with self.assertRaises(ValueError):a.score_case(job,row,self.src,packet)
        job['messages'][1]['content']=a.engine.serialize(packet,self.src['layout']);packet['records'][0]['payload']['issued']=False
        with self.assertRaises(ValueError):a.score_case(job,row,self.src,packet)

    def test_cached_support_is_immutable_and_metadata_still_checked(self):
        case,job,row,packet=self.scored();a.packet_support.cache_clear()
        original=a.reference.reference_labels
        with patch.object(a.reference,'reference_labels',wraps=original) as oracle:
            a.score_case(job,row,self.src,packet);a.score_case(job,row,self.src,packet)
            self.assertEqual(oracle.call_count,1)
            job['metadata']['compatible_labels']=['not-a-worker']
            with self.assertRaises(ValueError):a.score_case(job,row,self.src,packet)
        self.assertIsInstance(a.packet_support(a.engine.canonical(packet)),frozenset)

    def test_cluster_bootstrap_and_arm_mean_no_pseudoreplication(self):
        cases=[];left=('g26','full','procedure');right=('g26','full','direct')
        for block in range(3):
            for arm in a.ARMS:
                for condition in (left,right):
                    cases.append(dict(block_id=str(block),arm=arm,profile_id=condition[0],view=condition[1],procedure=condition[2],
                                      worker_profile='family',policy='p',layout='l',correct_definite=condition==left))
        result=a.block_contrast(cases,left,right,draws=50)
        self.assertEqual(result['blocks'],3);self.assertEqual(result['estimate'],1)
        self.assertEqual(result['lower'],1);self.assertEqual(result['upper'],1)
        with self.assertRaises(ValueError):a.block_contrast(cases[:-1],left,right,draws=5)
        with self.assertRaises(ValueError):a.block_contrast(cases+[cases[0]],left,right,draws=5)

    def test_bootstrap_preserves_stratum_weights_and_is_reproducible(self):
        values=[(('small',),1.)]+[(('large',),0.)]*3
        one=a.stratified_bootstrap(values,50);two=a.stratified_bootstrap(values,50)
        self.assertEqual(one,two);self.assertEqual(one['estimate'],.25)
        self.assertEqual(one['lower'],.25);self.assertEqual(one['upper'],.25)

    def test_complete_assigned_grid_is_required_before_outcome_analysis(self):
        contexts=[]
        for family in a.study.config()['worker_profiles']:
            for policy in a.study.POLICIES:
                for layout in ('canonical','shuffled'):
                    for repetition in range(2):
                        c=ctx(str(len(contexts)),repetition=repetition)
                        c.update(worker_profile=family,policy=policy,layout=layout);contexts.append(c)
        a.validate_contexts(contexts,2)
        with self.assertRaises(ValueError):a.validate_contexts(contexts[:-1],2)
        with self.assertRaises(ValueError):a.validate_contexts(contexts+[contexts[0]],2)

    def test_actor_factorial_interaction_and_no_attack_success_selection(self):
        sources=a.study.source_worlds([self.context],previous(self.context))
        # The fixture writes1+1 in honest/X/Y and2+2 in both at B3.
        result=a.actor_effects(sources,draws=20)
        self.assertEqual(result['violation']['interaction']['estimate'],1)
        self.assertEqual(result['violation']['x_assignment']['estimate'],.5)
        self.assertEqual(result['violation']['y_assignment']['estimate'],.5)
        self.assertEqual(result['violation']['interaction']['blocks'],1)
        with self.assertRaises(ValueError):a.actor_effects(sources[:-1],draws=5)

    def test_useful_completion_requires_valid_receiver(self):
        self.assertTrue(a.useful_completion(self.src))
        invalid=deepcopy(self.src);invalid['actor_valid'][3]=False
        self.assertFalse(a.useful_completion(invalid))
        forbidden=deepcopy(self.src);forbidden['world']['issued']=False;forbidden['world']['dy']=0
        self.assertFalse(a.useful_completion(forbidden));self.assertTrue(a.policy_correct_response(forbidden))

    def test_influence_pairs_share_source_and_remain_exploratory(self):
        sources=[]
        for condition,delta in [('neutral',0),('deceptive',2),('warning',0)]:
            src=deepcopy(self.src);src['influence']=condition;src['receiver_valid']=True
            src['world']['dx']=2;src['world']['dy']=delta
            src['host']=a.engine.simulate(src['public'],src['world']);sources.append(src)
        result=a.influence_effects(sources,20)
        self.assertEqual(result['violation:deceptive-neutral']['estimate'],1)
        self.assertEqual(result['violation:warning-deceptive']['estimate'],-1)
        self.assertEqual(result['violation:deceptive-neutral']['blocks'],1)
        with self.assertRaises(ValueError):a.influence_effects(sources[:-1],5)

    def test_public_export_cannot_bypass_private_admission(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(a.study,'ROOT',Path(temp)):
            with self.assertRaisesRegex(ValueError,'admission'):a.export({},Path(temp)/'public',5)
            self.assertFalse((Path(temp)/'public').exists())
            data={'cases':[],'_admission':dict(data_sha256='tampered',driver_state='dead',registration_sha256='r')}
            with patch.object(a.study,'registration'),patch.object(a,'release_idle'),patch.object(a.study,'sha',return_value='r'):
                with self.assertRaisesRegex(ValueError,'changed'):a.export(data,Path(temp)/'public',5)

    def test_bounded_shards_and_checksums(self):
        with tempfile.TemporaryDirectory() as temp:
            rows=[dict(case=i,text='x'*60) for i in range(13)]
            parts=a.write_shards(temp,'case',rows,max_bytes=200)
            recovered=[]
            for part in parts:
                raw=(Path(temp)/part['file']).read_bytes();self.assertLessEqual(len(raw),200)
                self.assertEqual(hashlib.sha256(raw).hexdigest(),part['sha256'])
                recovered.extend(json.loads(line) for line in raw.splitlines())
            self.assertEqual(recovered,rows)
            a.write_shards(temp,'influence-receivers',[{'case':'receiver'}],max_bytes=200)
            self.assertEqual(len(a.write_shards(temp,'influence',[{'case':'source'}],max_bytes=200)),1)
            with self.assertRaises(ValueError):a.write_shards(temp,'case',rows,max_bytes=200)
            with self.assertRaises(ValueError):a.write_shards(temp,'huge',[{'s':'x'*300}],max_bytes=200)

    def test_no_network_or_credentials_in_pure_analysis(self):
        with patch.object(a.study,'credentials',side_effect=AssertionError('credential access')):
            a.stratified_bootstrap([(('stratum',),0.)],5)
            self.scored()


class AdmissionTests(unittest.TestCase):
    def test_native_codec_reservation_and_receipt_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp);(out/'native').mkdir();j=a.study.job('fixture','g26',[dict(role='system',content='fixture'),dict(role='user',content='synthetic')],{'stage':'principal'})
            native=dict(model=a.study.profile('g26')['model'],status='completed',output_text='{"issued":true,"note":"ok"}',usage=dict(input_tokens=1,output_tokens=2))
            response,known,anomaly=a.study.normalize(native,a.study.profile('g26'))
            receipt=out/'native'/(a.study.digest(j['id'])+'.json');receipt.write_text(json.dumps({'native_response':native,'headers':{'secret':'PRIVATE'}}))
            row=dict(id=j['id'],profile_id=j['profile_id'],metadata=j['metadata'],transport={'http_status':200},
                     response=response,known_usage=known,anomaly=anomaly,estimated_cost=str(a.study.actual_cost(j,response)),
                     native_receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest())
            attempt=dict(id=j['id'],profile_id=j['profile_id'],request_sha256=a.study.digest(a.study.body_for(j)),reserved_cost=str(a.study.reservation(j)),started='synthetic')
            (out/'plan.json').write_text(json.dumps(dict(ids=[j['id']],jobs_sha256=a.study.digest([j]))))
            a.study.durable(out/'attempts.jsonl',attempt);a.study.durable(out/'responses.jsonl',row)
            rows,coverage=a.admit_phase(out,[j]);self.assertTrue(coverage['complete']);self.assertEqual(len(rows),1)
            receipt.write_text('{}')
            with self.assertRaisesRegex(ValueError,'receipt'):a.admit_phase(out,[j])


class PublicReplayTests(unittest.TestCase):
    @a.study.verified_config()
    def test_entire_registered_public_graph_replays_without_private_files(self):
        """64,000 synthetic reader terminals, not empirical results or serving."""
        started=time.perf_counter()
        def progress(stage):
            print('Synthetic public replay: '+stage+'; elapsed='+str(round(time.perf_counter()-started,1))+'s',flush=True)
        def contexts(split,repetitions):
            out=[]
            for family in a.study.config()['worker_profiles']:
                for policy in a.study.POLICIES:
                    for layout in ('canonical','shuffled'):
                        for repetition in range(repetitions):
                            c=ctx(split+'-'+str(len(out)),split,repetition)
                            c.update(worker_profile=family,policy=policy,layout=layout,revoked=policy=='B4revoked',
                                     time_y=13 if policy=='B4expiry' else 12)
                            c['public']['budget']=int(policy[1]);out.append(c)
            return out
        def row(j):
            role=j['metadata'].get('stage');arm=j['metadata'].get('arm')
            if role=='principal':answer={'issued':True,'note':'synthetic'}
            elif role=='coordinator':answer={'gx':True,'gy':True,'note':'synthetic'}
            elif role=='reporter':answer={'claimed_done':True,'note':'synthetic'}
            elif role in ('x','y','influence'):answer={'action':'write','delta':2 if arm=='both' else 1,'note':'synthetic'}
            else:
                labels=j['metadata'].get('compatible_labels',['NONE']);label=labels[0] if len(labels)==1 else 'ABSTAIN'
                answer={'status':'EXECUTOR' if label in list('ABCDE') else label,'worker_id':label if label in list('ABCDE') else None}
            response=dict(status='completed',output_text=json.dumps(answer),usage=dict(input_tokens=1,output_tokens=1),
                          returned_model=a.study.profile(j['profile_id'])['model'])
            return a.study.apply_host_action(dict(id=j['id'],profile_id=j['profile_id'],metadata=j['metadata'],response=response,
                        transport=dict(http_status=200,latency_seconds=.01),known_usage=True,anomaly=False,
                        estimated_cost=str(a.study.actual_cost(j,response)),native_receipt_sha256='1'*64))
        def actors(ctxs):
            previous={};jobs={}
            for role in a.ROLES:
                planned=a.study.actor_jobs(role,ctxs,previous);jobs.update({j['id']:j for j in planned})
                previous.update({j['id']:row(j) for j in planned})
            return previous,jobs
        main=contexts('main',16);dev=contexts('development',2)
        main_rows,actor_jobs=actors(main);dev_rows,dev_jobs=actors(dev)
        progress('actor graph constructed')
        sources=a.study.source_worlds(main,main_rows);dev_sources=a.study.source_worlds(dev,dev_rows)
        reader_jobs=a.study.reader_jobs(sources);cases=[];packets={}
        progress('64000 reader jobs planned')
        def score_jobs(source_list,jobs):
            lookup={s['source_id']:s for s in source_list};out=[];cache={}
            for j in jobs:
                src=lookup[j['metadata']['source_id']];sid=src['source_id']
                if sid not in cache:cache[sid]={('receipt_only7' if v['view']=='sufficient' else v['view']):v['packet'] for v in a.engine.views(src['public'],src['world'])}
                out.append(a.score_case(j,row(j),src,cache[sid][j['metadata']['view']]))
            return out
        cases=score_jobs(sources,reader_jobs)
        progress('64000 synthetic reader rows scored')
        cal_sources=a.study.calibration_sources();cal_jobs=a.study.reader_jobs(cal_sources)
        influence_jobs=a.study.influence_jobs(main,main_rows);influence_rows=[row(j) for j in influence_jobs]
        dev_readers=a.study.reader_jobs(dev_sources);technical=a.study.technical_jobs()
        artifacts={'contexts':main,'worlds':sources,'actors':a.public_actor_records(list(main_rows.values()),actor_jobs),
                   'influence':list(reversed(a.study.influence_worlds(main,main_rows,influence_rows))),
                   'influence_receivers':a.public_actor_records(influence_rows,{j['id']:j for j in influence_jobs}),
                   'calibration':score_jobs(cal_sources,cal_jobs),'engineering_contexts':dev,
                   'engineering_technical':a.public_actor_records([row(j) for j in technical],{j['id']:j for j in technical}),
                   'engineering_actors':a.public_actor_records(list(dev_rows.values()),dev_jobs),
                   'engineering_readers':a.public_actor_records([row(j) for j in dev_readers],{j['id']:j for j in dev_readers})}
        for profile in a.study.config()['reader_profiles']:artifacts['cases:'+profile]=[c for c in cases if c['profile_id']==profile]
        registrations={'main':{'contexts_sha256':a.study.digest(main)},'development':{'contexts_sha256':a.study.digest(dev)}}
        def forbidden(*args,**kwargs):raise AssertionError('Private data or credential access')
        with patch.object(a.study,'registration',side_effect=lambda split:registrations.get(split,{})),\
             patch.object(a.study,'contexts',side_effect=forbidden),patch.object(a.study,'folder',side_effect=forbidden),\
             patch.object(a.study,'credentials',side_effect=forbidden):
            replayed=a.replay_public(artifacts)
        progress('all public jobs, actions, evidence and verdicts replayed')
        if a.os.name=='nt':
            import ctypes
            from ctypes import wintypes
            class Counters(ctypes.Structure):
                _fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in
                    ('peak','current','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile')]
            memory=Counters();memory.cb=ctypes.sizeof(memory)
            ctypes.windll.kernel32.GetCurrentProcess.restype=wintypes.HANDLE
            psapi=ctypes.windll.psapi;psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD]
            if psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(),ctypes.byref(memory),memory.cb):
                print('Synthetic public replay: peak process working set='+str(round(memory.peak/1048576,1))+'MiB',flush=True)
        self.assertEqual(len(replayed['cases']),64000);self.assertEqual(len(replayed['sources']),2560)
        self.assertTrue(all(c['complete'] for c in replayed['coverage'].values()))
        self.assertEqual(replayed['coverage']['readers']['terminal'],64000)

    def test_public_actor_receipt_and_request_tampering(self):
        c=ctx();raw=previous(c);jobs=a.study.actor_jobs('x',[c],raw);j=jobs[0];row=raw[j['id']]
        row['metadata']=j['metadata']
        row['native_receipt_sha256']='1'*64;row['estimated_cost']=str(a.study.actual_cost(j,row['response']))
        record=a.public_actor_records([row],{j['id']:j})[0]
        self.assertEqual(a.public_row(record,j,True)['host_action'],row['host_action'])
        changed=deepcopy(record);changed['host_action']['delta']=99
        with self.assertRaises(ValueError):a.public_row(changed,j,True)
        changed=deepcopy(record);changed['request_sha256']='0'*64
        with self.assertRaises(ValueError):a.public_row(changed,j,True)
        changed=deepcopy(record);changed['headers']={'private':'forbidden'}
        with self.assertRaises(ValueError):a.public_row(changed,j,True)

    def test_public_inventory_hashes_and_offline_verifier(self):
        with tempfile.TemporaryDirectory() as temp,ExitStack() as stack:
            root=Path(temp);cfg=a.study.config();config=root/'source-config.json';config.write_text(json.dumps(cfg,indent=2)+'\n')
            source=root/'source';source.mkdir();public=root/'public';public.mkdir()
            registrations={split:{'split':split,'source_sha256':{'fixture':'hash'}} for split in ('technical','development','main')}
            for split,value in registrations.items():(source/(split+'.json')).write_text(json.dumps(value))
            stack.enter_context(patch.object(a.study,'CONFIG',config))
            stack.enter_context(patch.object(a.study,'freeze_path',side_effect=lambda split:source/(split+'.json')))
            stack.enter_context(patch.object(a.study,'registration',side_effect=lambda split:registrations[split]))
            groups={*('cases:'+p for p in cfg['reader_profiles']),'contexts','worlds','influence','calibration','actors','influence_receivers',
                    'engineering_contexts','engineering_technical','engineering_actors','engineering_readers'}
            artifacts={}
            for group in groups:
                stem='cases-'+group.split(':')[1] if group.startswith('cases:') else group.replace('_','-')
                artifacts[group]=a.write_shards(public,stem,[{'synthetic':True}])
            report={'primary':{'draws':10000,'seed':a.BOOTSTRAP_SEED},'synthetic':True}
            (public/'report.json').write_text(json.dumps(report))
            (public/'config.json').write_text(json.dumps(cfg))
            for split,value in registrations.items():
                filename='registration.json' if split=='main' else 'registration-'+split+'.json'
                (public/filename).write_text(json.dumps(value))
            manifest=dict(schema_version=1,study_id=cfg['study_id'],scope=a.PUBLIC_SCOPE,artifacts=artifacts,
                          report_sha256=hashlib.sha256((public/'report.json').read_bytes()).hexdigest(),
                          configuration_sha256=a.study.sha(config),registration_sha256=a.study.sha(source/'main.json'),
                          provenance_limit=a.PROVENANCE_LIMIT)
            (public/'manifest.json').write_text(json.dumps(manifest))
            def forbidden(*args,**kwargs):raise AssertionError('private/API/credential access')
            for method in ('credentials','folder','contexts'):
                stack.enter_context(patch.object(a.study,method,side_effect=forbidden))
            stack.enter_context(patch.object(a,'build_private',side_effect=forbidden))
            stack.enter_context(patch.object(a,'stopped_driver',side_effect=forbidden))
            with patch.object(a,'replay_public',return_value={'synthetic':True}),patch.object(a,'analyze',return_value=report):
                self.assertTrue(a.verify_public(public)['valid'])
                with patch.object(a,'analyze',return_value={'different_report':True}):
                    with self.assertRaisesRegex(ValueError,'report differs'):a.verify_public(public)
                extra=public/'private-headers.json';extra.write_text('{}')
                with self.assertRaises(ValueError):a.verify_public(public)
                extra.unlink()
                part=next(public.glob('cases-*.jsonl'));part.write_text('tampered\n')
                with self.assertRaises(ValueError):a.verify_public(public)


if __name__=='__main__':unittest.main()
