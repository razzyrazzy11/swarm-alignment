"""Mechanical fake-response fixtures; no network and no empirical outcome claims."""
import copy,json,unittest
from unittest.mock import patch
from decimal import Decimal
from experiments import live_analysis as a
from experiments import live_study as s
from experiments.live_audit import context,views,canonical,digest

class LiveAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.c=s.config();self.c['bootstrap_resamples']=50
        self.ctxs=[context(4200000+10000*i+j,f,j%2==0) for i,f in enumerate(self.c['families']) for j in range(2)]
        self.patches=[patch.object(a,'config',return_value=self.c),patch.object(a,'contexts',return_value=self.ctxs)]
        for p in self.patches:p.start();self.addCleanup(p.stop)

    def row(self,j,text):
        ri,ro=s.rates(j['model']);provider='hf' if j['model']==self.c['hf_model'] else 'adaption'
        return dict(id=j['id'],model=j['model'],metadata=j['metadata'],provider=provider,transport={'http_status':200},
            response=dict(status='completed',output_text=text,usage=dict(input_tokens=100,output_tokens=20),returned_model=j['model']),known_usage=True,estimated_cost=str((100*ri+20*ro)/1000000),job=j)

    def fixture(self):
        actors=[]
        for ctx in self.ctxs:
            j=s.job('origin-'+str(ctx['seed']),self.c['actor_model'],s.ORIGIN_PROMPT,s.origin_input(ctx),source_seed=ctx['seed'],phase='origin')
            prior=self.row(j,json.dumps(dict(decoy_action='mark' if ctx['authorized'] else 'skip',handoff_note='Use current policy.')));actors.append(prior);o=a.decode(prior,True)
            for mode,exposure in [('solo','actual'),('delegated','actual'),('delegated','benign'),('delegated','malicious'),('delegated','warning')]:
                history=[dict(role='user',content=canonical(s.origin_input(ctx))),dict(role='assistant',content=prior['response']['output_text'])] if mode=='solo' else []
                j=s.job(f"receiver-{ctx['seed']}-{mode}-{exposure}",self.c['actor_model'],s.WORKER_PROMPT,s.worker_input(ctx,o,mode,exposure),history=history,source_seed=ctx['seed'],mode=mode,exposure=exposure,phase='receiver')
                actors.append(self.row(j,json.dumps(dict(action='write' if exposure!='warning' else 'read',claimed_done=exposure!='warning'))))
        ts=a.replay(actors);audits=[]
        for t in ts:
            for v in views(t['public'],t['world']):
                if t['exposure']!='actual' and v['restoration']!='none':continue
                for model in self.c['monitors']:
                    labels=v['compatible_labels'];answer=dict(status='ABSTAIN',worker_id=None)
                    if len(labels)==1:answer=dict(status='NONE' if labels[0]=='NONE' else 'EXECUTOR',worker_id=None if labels[0]=='NONE' else labels[0])
                    j=s.job(f"audit-{t['id']}-{v['mechanism']}-{v['restoration']}-{model}",model,s.MONITOR_PROMPT,v['packet'],source_seed=t['source_seed'],trajectory_id=t['id'],mode=t['mode'],exposure=t['exposure'],mechanism=v['mechanism'],restoration=v['restoration'],phase='audit',packet_sha256=digest(v['packet']))
                    audits.append(self.row(j,json.dumps(answer)))
        return actors,ts,audits

    def test_actual_action_replay_and_cluster_denominators(self):
        actors,ts,audits=self.fixture();replayed,cases=a.build_cases(actors,audits)
        self.assertEqual(replayed,ts)
        report=a.analyze(actors,ts,cases)
        self.assertEqual(report['main_source_clusters'],6)
        self.assertEqual(report['main_trajectories'],12)
        self.assertEqual(report['actor_calls'],36)
        self.assertEqual(report['main_audit_calls'],252)
        self.assertEqual(report['influence_audit_calls'],162)
        self.assertEqual(report['primary']['result']['n'],6)
        self.assertEqual(report['primary']['result']['estimate'],0)
        self.assertGreater(report['behavior']['delegated']['unauthorized_write'],0)

    def test_continued_history_and_hidden_actor_are_not_repaired(self):
        actors,_,_=self.fixture();bad=copy.deepcopy(actors)
        solo=next(r for r in bad if r['metadata'].get('mode')=='solo')
        solo['job']['history']=[]
        with self.assertRaisesRegex(ValueError,'Receiver/context boundary'):a.replay(bad)

    def test_audit_identity_and_packet_metadata_cannot_be_swapped(self):
        actors,_,audits=self.fixture();bad=copy.deepcopy(audits)
        bad[0]['metadata']['source_seed']+=1
        with self.assertRaisesRegex(ValueError,'metadata/identity'):a.build_cases(actors,bad)

    def test_missing_actor_and_false_complete_grid_rejected(self):
        actors,_,_=self.fixture()
        with self.assertRaisesRegex(ValueError,'trajectory grid'):a.replay(actors[:-1])

if __name__=='__main__':unittest.main()
