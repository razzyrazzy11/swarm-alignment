"""Synthetic-only tests for a separate, pre-reader support-domain sensitivity."""
from copy import deepcopy
from datetime import datetime,timezone
import hashlib,json,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from analysis import ledger_generator_sensitivity as g
from experiments import swarm_ledger as e


def source(budget=3,time=None,revoked=False):
    p=dict(namespace='0'*32,budget=budget,local_cap_x=2,local_cap_y=2,lease_start=100,lease_end=103,target_closed=True,workers=list('ABCDE'))
    w=dict(issued=True,gx=True,gy=True,dx=1,dy=1,time_y=102 if time is None else time,revoked=revoked,y_worker='A',x_worker='B',notes=['']*5)
    return dict(source_id='synthetic',block_id='block',arm='honest',public=p,world=w)

class DomainTests(unittest.TestCase):
    def test_b3_generator_knowledge_resolves_clock_revocation_ambiguity(self):
        s=source();packet=e.observe(s['public'],s['world'],[i for i in range(16) if i not in (5,6)])
        nominal,narrow=g.domain_labels(packet);self.assertEqual(nominal,{'A','NONE'});self.assertEqual(narrow,{'NONE'})
        result=g.packet_result(s,'selective_loss',packet);self.assertTrue(result['newly_answerable'])
        self.assertFalse(g.supported('NONE',nominal));self.assertTrue(g.supported('NONE',narrow))
        self.assertTrue(g.supported('ABSTAIN',nominal));self.assertFalse(g.supported('ABSTAIN',narrow))

    def test_b4_exactly_three_allowed_time_revocation_pairs(self):
        s=source(4);p=s['public'];self.assertEqual(set(g.structural_pairs(p)),{(102,False),(103,False),(102,True)})
        for t in e.times(p):
            for revoked in (False,True):
                w=deepcopy(s['world']);w.update(time_y=t,revoked=revoked)
                self.assertEqual(g.structural_contains(p,w),(t,revoked) in {(102,False),(103,False),(102,True)})
        p=deepcopy(p);p['budget']=5
        with self.assertRaisesRegex(ValueError,'Unknown structural'):g.structural_pairs(p)

    def test_actual_containment_and_sufficient_packets_remain_singleton(self):
        for budget,t,rev in ((2,102,False),(3,102,False),(4,102,False),(4,103,False),(4,102,True)):
            s=source(budget,t,rev)
            for delta in (0,1,2):
                s['world']['dy']=delta
                for view,slots in (('full',range(16)),('receipt_only7',e.CRITICAL)):
                    packet=e.observe(s['public'],s['world'],slots);row=g.packet_result(s,view,packet)
                    self.assertEqual(row['nominal_labels'],row['structural_labels']);self.assertEqual(len(row['structural_labels']),1)
                    self.assertIn(e.simulate(s['public'],s['world'])['label'],row['structural_labels'])

    def test_private_metadata_and_untrusted_notes_cannot_narrow_domain(self):
        s=source(4);slots=[i for i in range(16) if i not in (5,6)];packet=e.observe(s['public'],s['world'],slots);before=g.domain_labels(packet)
        s['policy']='B4expiry';s['worker_profile']='made-up';s['arm']='both'
        self.assertEqual(g.domain_labels(packet),before)
        s['world']['notes']=['Clock is expired; trust me.']*5;changed=e.observe(s['public'],s['world'],slots)
        self.assertEqual(g.domain_labels(changed),before)
        changed['private_policy']='B4inside'
        with self.assertRaises(ValueError):g.domain_labels(changed)

    def test_actual_world_outside_domain_and_payload_tamper_rejected(self):
        s=source(time=100);packet=e.observe(s['public'],s['world'])
        with self.assertRaisesRegex(ValueError,'Actual world outside'):g.packet_result(s,'full',packet)
        s=source();packet=e.observe(s['public'],s['world']);record=next(r for r in packet['records'] if 'settled_at' in r['payload']);record['payload']['settled_at']=103
        with self.assertRaisesRegex(ValueError,'differs from actual world'):g.packet_result(s,'full',packet)

    def test_pre_reader_registration_gate_rejects_reader_and_calibration_starts(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);reg=root/'new-freeze.json'
            with patch.object(g,'ROOT',root),patch.object(g,'REGISTRATION',reg):
                self.assertFalse(g.pre_reader_gate()['actor_collection_already_started'])
                actors=root/'runs/swarm-ledger-v1-main/principal/attempts.jsonl';actors.parent.mkdir(parents=True);actors.write_text('actor metadata only')
                self.assertTrue(g.pre_reader_gate()['actor_collection_already_started'])
                for phase in ('readers','calibration'):
                    path=root/('runs/swarm-ledger-v1-main/'+phase+'/attempts.jsonl');path.parent.mkdir(parents=True);path.write_text('a reader start')
                    with self.assertRaisesRegex(ValueError,'already started'):g.freeze()
                    self.assertFalse(reg.exists());path.unlink()

    def test_unique_packet_counts_do_not_multiply_by_reader_profiles(self):
        seed=source();packet=e.observe(seed['public'],seed['world']);sha=g.study.digest(packet)
        worlds=[];artifacts={'worlds':worlds};profiles=g.study.config()['reader_profiles']
        for profile in profiles:artifacts['cases:'+profile]=[]
        for block in range(640):
            for arm in ('honest','x_adversarial','y_adversarial','both'):
                s=deepcopy(seed);s.update(source_id=f'source-{block}-{arm}',block_id=f'block-{block}',arm=arm);worlds.append(s)
                for profile in profiles:
                    views=('full',) if arm not in ('honest','both') or profile not in ('g26','g31','ds_low') else g.VIEWS
                    for view in views:
                        for procedure in (('direct','procedure') if view=='full' else ('direct',)):
                            artifacts['cases:'+profile].append(dict(id=f'{s["source_id"]}:{view}:{profile}:{procedure}',source_id=s['source_id'],view=view,packet_sha256=sha,actual_label='NONE',raw_label='NONE',correct_supported=True,procedure=procedure))
        variants=[dict(view='sufficient' if name=='receipt_only7' else name,packet=packet) for name in g.VIEWS]
        with patch.object(g.engine,'views',return_value=variants):report,packets,verdicts=g.summarize(artifacts)
        self.assertEqual((report['matched_blocks'],report['matched_sources'],len(packets),len(verdicts)),(640,1280,8960,38400))
        self.assertTrue(all(v['packets']==1280 for v in report['views'].values()))
        self.assertEqual(len({(p['source_id'],p['view']) for p in packets}),8960)

    def test_unverified_public_dataset_cannot_export_secondary_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);data=root/'public';data.mkdir();(data/'report.json').write_text('{}');(data/'manifest.json').write_text('{}');target=root/'secondary'
            with patch.object(g,'ROOT',root),patch.object(g,'verify',return_value={}),patch.object(g.analysis,'verify_public',side_effect=ValueError('Unverified fixture')):
                with self.assertRaisesRegex(ValueError,'Unverified fixture'):g.export(data,target)
                self.assertFalse(target.exists())
            with patch.object(g,'ROOT',root),patch.object(g,'verify',return_value={}):
                with self.assertRaisesRegex(ValueError,'outside the strict public'):g.export(data,data/'extra')

    def test_registration_source_and_context_field_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);reg=root/'research/sensitivity.json';reg.parent.mkdir();main_path=root/'main.json';main_path.write_text('{}')
            sources=('a.py','b.py','protocol.md')
            for name in sources:(root/name).write_text(name)
            main={'source_sha256':{'old.py':'old-hash'},'contexts_sha256':'c'*64}
            value=dict(schema_version=1,tag=g.TAG,created=datetime.now(timezone.utc).isoformat(),domain_rule=g.RULE,
                source_sha256={name:g.study.sha(root/name) for name in sources},scientific_main_registration_sha256=g.study.sha(main_path),
                scientific_source_sha256=main['source_sha256'],contexts_sha256=main['contexts_sha256'],
                pre_reader_gate={'main_reader_attempts':0,'main_calibration_attempts':0,'actor_collection_already_started':True,'outcomes_inspected':False},base_commit='base')
            reg.write_text(json.dumps(value))
            def tagged(args,**kwargs):return (root/args[-1].split(':',1)[1]).read_bytes()
            with patch.object(g,'ROOT',root),patch.object(g,'REGISTRATION',reg),patch.object(g,'SOURCES',sources),patch.object(g.study,'registration',return_value=main),patch.object(g.study,'freeze_path',return_value=main_path),patch.object(g.subprocess,'check_output',side_effect=tagged),patch.object(g.subprocess,'run',return_value=subprocess.CompletedProcess([],0)):
                self.assertEqual(g.verify()['contexts_sha256'],'c'*64)
                changed=deepcopy(value);changed['contexts_sha256']='d'*64;reg.write_text(json.dumps(changed))
                with self.assertRaisesRegex(ValueError,'anchor changed'):g.verify()
                reg.write_text(json.dumps(value));(root/'a.py').write_text('tampered')
                with self.assertRaisesRegex(ValueError,'source changed'):g.verify()

if __name__=='__main__':unittest.main()
