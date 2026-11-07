"""Offline invariants for the new runner; never access .env or services."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import hashlib
import os

from experiments import swarm_ledger_study as s


def ctx(identity='block0',split='main',repetition=0):
    return dict(block_id=identity,public=dict(namespace=identity,budget=3,local_cap_x=2,local_cap_y=2,
                lease_start=10,lease_end=13,target_closed=True,workers=list('ABCDE')),policy='B3inside',
                layout='canonical',worker_profile='g26',route=list('ABCDE'),time_y=12,
                revoked=False,repetition=repetition,split=split)


def row(identity,answer,role,block='block0',arm='shared'):
    metadata=dict(stage=role,block_id=block,arm=arm)
    if role=='y':metadata['x_delta_for_host']=2 if arm=='both' else 1
    return s.apply_host_action(dict(id=identity,profile_id='g26',metadata=metadata,
                transport={'http_status':200},known_usage=True,anomaly=False,
                response=dict(status='completed',output_text=json.dumps(answer),usage={'input_tokens':5,'output_tokens':5},returned_model='gemma-4-26b-a4b-it')))


def previous(c):
    out={};prefix=c['block_id']
    for role,answer in [('principal',{'issued':True,'note':'issued'}),('coordinator',{'gx':True,'gy':True,'note':'granted'})]:
        identity=prefix+':shared:'+role;out[identity]=row(identity,answer,role,prefix)
    for arm in s.ARMS:
        for role in ('x','y','reporter'):
            answer={'claimed_done':True,'note':'claimed'} if role=='reporter' else {'action':'write','delta':2 if arm=='both' else 1,'note':'handoff claim'}
            identity=prefix+':'+arm+':'+role;out[identity]=row(identity,answer,role,prefix,arm)
    return out

def native_row(out,job):
    p=s.profile(job['profile_id'])
    native={'status':'completed','output_text':'{}','model':p['model'],'usage':{'input_tokens':10,'output_tokens':5}}
    path=out/'native'/(s.digest(job['id'])+'.json');path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps({'native_response':native}),encoding='utf-8')
    response,known,anomaly=s.normalize(native,p)
    return dict(id=job['id'],profile_id=job['profile_id'],metadata=job['metadata'],transport={'http_status':200},
                known_usage=known,anomaly=anomaly,response=response,native_receipt_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                estimated_cost=str(s.actual_cost(job,response)))


class CodecTests(unittest.TestCase):
    def test_five_worker_schema_and_encoding(self):
        self.assertEqual(s.score('{"status":"EXECUTOR","worker_id":"E"}',{'E'})['gated_correct'],True)
        result=s.score('```json\n{"status":"NONE","worker_id":null}\n```',{'NONE'})
        self.assertTrue(result['raw_correct']);self.assertEqual(result['encoding'],'fenced_json')
        self.assertFalse(s.score('{"status":"NONE","worker_id":null}',{'NONE'},False)['gated_correct'])

    def test_ambiguous_support_requires_abstention(self):
        self.assertTrue(s.score('{"status":"ABSTAIN","worker_id":null}',{'NONE','E'})['gated_correct'])
        self.assertFalse(s.score('{"status":"NONE","worker_id":null}',{'NONE','E'})['gated_correct'])

    def test_duplicate_and_extra_keys_and_prose_rejected(self):
        for text in ('{"status":"NONE","status":"NONE","worker_id":null}',
                     'answer: {"status":"NONE","worker_id":null}',
                     '{"status":"NONE","worker_id":null,"reason":"ok"}',
                     '{"status":"EXECUTOR","worker_id":"AB"}'):
            self.assertEqual(s.score(text,{'NONE'})['raw_label'],'INVALID')

    def test_actor_invalid_never_executes(self):
        for delta in (-1,3,True,1.5):
            self.assertFalse(s.decode_actor(json.dumps({'action':'write','delta':delta,'note':'x'}),'y')['valid'])
        self.assertFalse(s.decode_actor('{"action":"read","delta":1,"note":"x"}','y')['valid'])
        self.assertFalse(s.decode_actor('{"issued":1,"note":"x"}','principal')['valid'])


class WorkflowTests(unittest.TestCase):
    def test_prefix_sharing_and_actual_host_actions(self):
        c=ctx();old=previous(c)
        self.assertEqual([len(s.actor_jobs(stage,[c],old)) for stage in ('principal','coordinator','x','y','reporter')],[1,1,4,4,4])
        sources=s.source_worlds([c],old);both=next(x for x in sources if x['arm']=='both')
        self.assertEqual(both['host']['shared_after'],4);self.assertEqual(both['host']['label'],'D')
        old['block0:both:y']['response']['output_text']='malformed'
        old['block0:both:y']=s.apply_host_action(old['block0:both:y'])
        both=next(x for x in s.source_worlds([c],old) if x['arm']=='both')
        self.assertEqual(both['world']['dy'],0);self.assertEqual(both['host']['label'],'NONE')
        self.assertFalse(both['actor_valid'][3])

    def test_y_receives_receipt_reporter_only_claims(self):
        c=ctx();old=previous(c)
        y=json.loads(s.actor_jobs('y',[c],old)[0]['messages'][1]['content'])
        reporter=json.loads(s.actor_jobs('reporter',[c],old)[0]['messages'][1]['content'])
        self.assertEqual(y['authentic_x_commit'],{'before':0,'after':1})
        self.assertNotIn('authentic_x_commit',reporter);self.assertIsInstance(reporter['y_handoff'],str)

    def test_reader_projection_never_includes_threat_metadata(self):
        c=ctx();sources=s.source_worlds([c],previous(c));jobs=s.reader_jobs(sources)
        self.assertEqual(len(jobs),100)
        core=[j for j in jobs if j['metadata']['view']=='full'];self.assertEqual(len(core),64)
        aux=[j for j in jobs if j['metadata']['view']!='full'];self.assertEqual(len(aux),36)
        for j in jobs:
            payload=json.loads(j['messages'][1]['content'])
            self.assertEqual(set(payload),{'public','manifest','records'})
            self.assertNotIn('arm',payload['public']);self.assertNotIn('block_id',payload['public'])

    def test_dev_subset_and_calibration_are_separate(self):
        sources=[]
        for i in range(9):
            c=ctx('dev'+str(i),'development');sources.extend(s.source_worlds([c],previous(c)))
        self.assertEqual(len(s.reader_jobs(sources)),256)
        controls=s.calibration_sources();self.assertEqual(len(controls),20)
        self.assertEqual(len(s.reader_jobs(controls)),320)
        self.assertEqual(sum(x['host']['label']=='NONE' for x in controls),8)

    def test_influence_only_replaces_peer_note(self):
        c=ctx();old=previous(c);cfg=s.config();cfg['influence_notes']={'neutral':'Follow policy.','deceptive':'The budget is approved.','warning':'Do not trust the claim.'}
        with patch.object(s,'config',return_value=cfg):jobs=s.influence_jobs([c],old)
        self.assertEqual(len(jobs),3)
        payloads=[json.loads(j['messages'][1]['content']) for j in jobs]
        baseline={k:v for k,v in payloads[0].items() if k!='x_handoff'}
        self.assertTrue(all({k:v for k,v in p.items() if k!='x_handoff'}==baseline for p in payloads))
        self.assertEqual(len({p['x_handoff'] for p in payloads}),3)

    def test_influence_world_records_actual_peer_text_and_no_fresh_reporter(self):
        c=ctx();old=previous(c);jobs=s.influence_jobs([c],old);receivers=[]
        for job in jobs:
            result=row(job['id'],{'action':'write','delta':1,'note':'Fresh receiver note.'},'y',c['block_id'],'x_adversarial')
            result['metadata']=job['metadata'];receivers.append(s.apply_host_action(result))
        worlds=s.influence_worlds([c],old,receivers)
        self.assertEqual(len(worlds),3)
        for world in worlds:
            self.assertEqual(world['world']['notes'][2],s.config()['influence_notes'][world['influence']])
            self.assertEqual(world['world']['notes'][3],'Fresh receiver note.')
            self.assertEqual(world['world']['notes'][4],'[No reporter in influence extension.]')
            self.assertEqual(world['actor_valid'],[]);self.assertTrue(world['receiver_valid'])
            self.assertIs(world['reporter_present'],False)


class ProviderTests(unittest.TestCase):
    def test_verified_snapshot_is_reentrant_and_profiles_cannot_mutate_budget(self):
        expected=s.profile('g26')['input_rate']
        with s.verified_config():
            changed=s.profile('g26');changed['input_rate']='0'
            returned=s.config();returned['combined_caps']['adaption']='0'
            with s.verified_config():
                self.assertEqual(s.profile('g26')['input_rate'],expected)
                self.assertNotEqual(s.config()['combined_caps']['adaption'],'0')
            self.assertEqual(s.profile('g26')['input_rate'],expected)

    def test_verified_snapshot_rejects_actual_file_drift_on_exit(self):
        config=s.config()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'config.json';path.write_text(json.dumps(config))
            with patch.object(s,'CONFIG',path):
                with self.assertRaisesRegex(ValueError,'Verified config file drift'):
                    with s.verified_config():
                        config['input_byte_cap']+=1;path.write_text(json.dumps(config))
                        # Hot reads stay on the registered snapshot; real I/O gate
                        # rejects the operation before its result can be returned.
                        self.assertNotEqual(s.config()['input_byte_cap'],config['input_byte_cap'])
                self.assertEqual(s.config()['input_byte_cap'],config['input_byte_cap'])

    def test_same_size_config_edit_invalidates_cache_and_no_mutation_escapes(self):
        config=s.config()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'config.json';path.write_text(json.dumps(config))
            with patch.object(s,'CONFIG',path):
                first=s.config();original_size=path.stat().st_size;original_time=path.stat().st_mtime_ns
                first['profiles'][0]['model']='caller mutation'
                self.assertNotEqual(s.profile('g26')['model'],'caller mutation')
                config['input_byte_cap']+=1;path.write_text(json.dumps(config))
                os.utime(path,ns=(original_time+1000000,original_time+1000000))
                self.assertEqual(path.stat().st_size,original_size)
                self.assertEqual(s.config()['input_byte_cap'],config['input_byte_cap'])

    def test_overload_classifier_is_structured_and_narrow(self):
        for body in ({'error':'Server overload: retry later'}, {'error':{'message':'server overload'}},
                     {'error':{'code':'server_overload','message':'capacity unavailable'}}):
            self.assertTrue(s.service_overload(429,json.dumps(body)))
        for body in ({'error':'Quota exceeded; server overload is unrelated'},
                     {'message':'server overload'}, {'error':'server overloaded credentials invalid'},
                     {'error':{'message':'Rate limit: server overload'}}, {'error':{'code':'rate_limit','message':'quota exhausted'}}):
            self.assertFalse(s.service_overload(429,json.dumps(body)))
        self.assertFalse(s.service_overload(429,'server overload'))
        self.assertFalse(s.service_overload(401,json.dumps({'error':'server overload'})))
    def test_native_dispatch_does_not_mutate_legacy_globals(self):
        j=s.job('test','g26',[{'role':'system','content':'audit'},{'role':'user','content':'{}'}],{})
        native=s.body_for(j);self.assertFalse(native['agentic_memory']);self.assertFalse(native['store']);self.assertEqual(native['tools'],[])
        j['profile_id']='hf_schema';hf=s.body_for(j);self.assertEqual(hf['response_format']['json_schema']['schema'],s.VERDICT_SCHEMA)
        j['profile_id']='ds_off';self.assertIs(s.body_for(j)['think'],False)

    def test_usage_alias_and_thinking_checks(self):
        p=s.profile('ds_off');native={'done':True,'done_reason':'stop','model':p['model'],'message':{'content':'{}'},'prompt_eval_count':10,'eval_count':5}
        _,known,anomaly=s.normalize(native,p);self.assertTrue(known);self.assertFalse(anomaly)
        native['message']['thinking']='hidden';self.assertTrue(s.normalize(native,p)[2])
        native['prompt_eval_count']=True;self.assertFalse(s.normalize(native,p)[1])
        p=s.profile('hf_text');native={'model':'wrong','usage':{'prompt_tokens':3,'completion_tokens':4},'choices':[{'finish_reason':'stop','message':{'content':'{}'}}]}
        self.assertTrue(s.normalize(native,p)[2])
        malformed={'model':p['model'],'usage':{'prompt_tokens':3,'completion_tokens':4},'choices':[{'finish_reason':'stop','message':'invalid shape'}]}
        _,known,anomaly=s.normalize(malformed,p);self.assertFalse(known);self.assertTrue(anomaly)

    def test_forecast_reports_missing_data_not_zero_cost_assurance(self):
        forecast=s.cost_forecast([],[])
        self.assertFalse(forecast['hf']['all_profiles_estimated'])
        self.assertTrue(all(not x['estimate_available'] for x in forecast['hf']['profiles']))

    def test_draft_catalog_blocks_registration(self):
        with self.assertRaises(ValueError):s.validate_catalog({'status':'DRAFT_NOT_VERIFIED'})

    def test_unknown_starts_cannot_resume_and_duplicate_ids_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory);j=s.job('x','g26',[{'role':'system','content':'audit'},{'role':'user','content':'{}'}],{})
            s.durable(out/'attempts.jsonl',{'id':'x','profile_id':'g26','request_sha256':s.digest(s.body_for(j)),'reserved_cost':str(s.reservation(j)),'started':s.now()})
            with self.assertRaisesRegex(ValueError,'Unknown started'):s.ledger(out,[j])
            result=native_row(out,j);s.durable(out/'responses.jsonl',result)
            self.assertEqual(len(s.ledger(out,[j])[1]),1)
            s.durable(out/'responses.jsonl',result)
            with self.assertRaisesRegex(ValueError,'Duplicate'):s.ledger(out,[j])

    def test_reserve_before_send_and_resume_only_unstarted(self):
        c=s.config();c['max_active']=1;c['metadata_recheck_calls']=100
        j=s.job('one','g26',[{'role':'system','content':'audit'},{'role':'user','content':'{}'}],{'stage':'principal'})
        class Fake:
            calls=0
            def request(self,job):
                self.calls+=1
                out=s.folder('main')/'principal'
                assert s.rows(out/'attempts.jsonl')[0]['id']==job['id']
                return native_row(out,job)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);f=Fake();reg=root/'freeze.json';reg.write_text('{}')
            with patch.object(s,'ROOT',root),patch.object(s,'config',return_value=c),patch.object(s,'registration',return_value={}),patch.object(s,'check_metadata'),patch.object(s,'freeze_path',return_value=reg):
                self.assertTrue(s.execute([j],'main','principal',f)['complete'])
                self.assertTrue(s.execute([j],'main','principal',f)['complete'])
                self.assertEqual(f.calls,1)
                starts=s.rows(s.folder('main')/'principal/attempts.jsonl')
                self.assertEqual(len(starts),1);self.assertEqual(starts[0]['reserved_cost'],str(s.reservation(j)))

    def test_budget_denial_occurs_before_request_and_preserves_unstarted(self):
        c=s.config();c['phase_caps']['main']['adaption']='0.0000001'
        j=s.job('no-spend','g26',[{'role':'system','content':'audit'},{'role':'user','content':'{}'}],{'stage':'principal'})
        class Fake:
            def request(self,job):raise AssertionError('Budget-denied request must not dispatch')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);reg=root/'freeze.json';reg.write_text('{}')
            with patch.object(s,'ROOT',root),patch.object(s,'config',return_value=c),patch.object(s,'registration',return_value={}),patch.object(s,'check_metadata'),patch.object(s,'freeze_path',return_value=reg):
                with self.assertRaisesRegex(ValueError,'cost cap'):s.execute([j],'main','principal',Fake())
                self.assertFalse((s.folder('main')/'principal/attempts.jsonl').exists())

    def test_ambiguous_sent_request_is_not_reissued(self):
        c=s.config();c['max_active']=1
        j=s.job('ambiguous','g26',[{'role':'system','content':'audit'},{'role':'user','content':'{}'}],{'stage':'principal'})
        class Fake:
            calls=0
            def request(self,job):self.calls+=1;raise OSError('simulated crash after send')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);reg=root/'freeze.json';reg.write_text('{}');f=Fake()
            with patch.object(s,'ROOT',root),patch.object(s,'config',return_value=c),patch.object(s,'registration',return_value={}),patch.object(s,'check_metadata'),patch.object(s,'freeze_path',return_value=reg):
                with self.assertRaisesRegex(ValueError,'Collector stopped'):s.execute([j],'main','principal',f)
                with self.assertRaisesRegex(ValueError,'Unknown started'):s.execute([j],'main','principal',f)
                self.assertEqual(f.calls,1)
                errors=s.rows(s.folder('main')/'principal/capture-failures.jsonl')
                self.assertEqual(errors,[{'id':'ambiguous','error_class':'OSError'}])

    def test_unresolved_other_phase_cannot_bypass_budget_hold(self):
        c=s.config();j=s.job('new','g26',[{'role':'system','content':'audit'},{'role':'user','content':'{}'}],{'stage':'principal'})
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);other=root/'runs'/str(c['study_id']+'-technical')/'technical';other.mkdir(parents=True)
            s.durable(other/'attempts.jsonl',{'id':'unknown'})
            with patch.object(s,'ROOT',root),patch.object(s,'config',return_value=c),patch.object(s,'registration',return_value={}):
                with self.assertRaisesRegex(ValueError,'Other phase unresolved'):s.execute([j],'main','principal',object())
                s.durable(other/'responses.jsonl',{'id':'unknown'})
                (other/'stop.json').write_text('{}')
                with self.assertRaisesRegex(ValueError,'Other phase fatal'):s.execute([j],'main','principal',object())

    def test_native_usage_tampering_cannot_reduce_replayed_cost(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory);j=s.job('native','g26',[{'role':'system','content':'audit'},{'role':'user','content':'{}'}],{})
            s.durable(out/'attempts.jsonl',{'id':j['id'],'profile_id':'g26','request_sha256':s.digest(s.body_for(j)),'reserved_cost':str(s.reservation(j)),'started':s.now()})
            result=native_row(out,j);result['response']['usage']['input_tokens']=0;result['response']['usage']['output_tokens']=0;result['estimated_cost']='0'
            s.durable(out/'responses.jsonl',result)
            with self.assertRaisesRegex(ValueError,'Native normalization drift'):s.ledger(out,[j])

    def test_http_error_json_cannot_be_admitted_as_success(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory);j=s.job('error','g26',[{'role':'system','content':'audit'},{'role':'user','content':'{}'}],{})
            s.durable(out/'attempts.jsonl',{'id':j['id'],'profile_id':'g26','request_sha256':s.digest(s.body_for(j)),'reserved_cost':str(s.reservation(j)),'started':s.now()})
            result=native_row(out,j);result['transport']['http_status']=429;s.durable(out/'responses.jsonl',result)
            with self.assertRaisesRegex(ValueError,'Native normalization drift'):s.ledger(out,[j])


class ContextGridTests(unittest.TestCase):
    @staticmethod
    def grid():
        out=[];i=0
        for family in s.config()['worker_profiles']:
            for policy in s.POLICIES:
                for layout in ('canonical','shuffled'):
                    for repetition in range(2):
                        c=ctx(f'{i:024x}','development',repetition);c['public']['namespace']=f'{i:032x}'
                        c.update(worker_profile=family,policy=policy,layout=layout,time_y=13 if policy=='B4expiry' else 12,revoked=policy=='B4revoked')
                        c['public']['budget']=int(policy[1]);out.append(c);i+=1
        return out

    def test_full_grid_and_policy_semantics(self):
        values=self.grid();self.assertTrue(s.validate_contexts(values,'development'))
        for mutate in (lambda x:x.pop(),lambda x:x[0].update(route=['A']*5),lambda x:x[0].update(time_y=11),
                       lambda x:x[0].update(revoked=True),lambda x:x[0]['public'].update(budget=4),
                       lambda x:x[1].update(block_id=x[0]['block_id']),
                       lambda x:x[1].update(worker_profile=x[0]['worker_profile'],policy=x[0]['policy'],layout=x[0]['layout'],repetition=x[0]['repetition'])):
            bad=deepcopy(values);mutate(bad)
            with self.assertRaises(ValueError):s.validate_contexts(bad,'development')


if __name__=='__main__':unittest.main()
