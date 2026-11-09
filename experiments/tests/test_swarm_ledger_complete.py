import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments import swarm_ledger_complete as s
from experiments import swarm_ledger_study as old

class CompleteAdapterTests(unittest.TestCase):
    def sources(self,split='main'):
        public=dict(namespace='a'*32,budget=3,local_cap_x=2,local_cap_y=2,
                    lease_start=10,lease_end=13,target_closed=True,workers=list('ABCDE'))
        world=dict(issued=True,gx=True,gy=True,dx=1,dy=1,time_y=12,revoked=False,
                   x_worker='C',y_worker='D',notes=['']*5)
        return [dict(source_id=s.digest(['synthetic',arm])[:24],block_id='b'*24,arm=arm,
                     worker_profile='g26',policy='B3inside',layout='canonical',split=split,
                     public=public,world=world,host=s.engine.simulate(public,world),actor_valid=[True]*5)
                for arm in s.ARMS]

    def test_config_rejects_material_drift(self):
        c=s.config();s._validate_config(c)
        for field,value in [('model','other'),('output_rate','9.0'),('max_output_tokens',8192)]:
            bad=json.loads(json.dumps(c));bad['profiles'][0][field]=value
            with self.assertRaises(ValueError):s._validate_config(bad)
        bad=json.loads(json.dumps(c));bad['phase_caps']['main']['hf']='5.00'
        with self.assertRaises(ValueError):s._validate_config(bad)

    def test_main_and_calibration_grids(self):
        with s.verified_config():
            jobs=s.reader_jobs(self.sources())
            self.assertEqual(len(jobs),84)
            self.assertEqual({j['profile_id'] for j in jobs},set(s.config()['reader_profiles']))
            self.assertEqual(len([j for j in jobs if j['profile_id']=='g31' and j['metadata']['view']!='full']),12)
            self.assertEqual(len(s.reader_jobs(s.calibration_sources())),240)

    def test_engineering_is_original_eight_reader_graph(self):
        with s.verified_config():
            sources=self.sources('development')
            self.assertEqual(s.reader_jobs(sources),old.reader_jobs(sources))
            self.assertEqual(len(s.reader_jobs(sources)),32)

    def test_body_and_prices_are_original_for_every_profile(self):
        with s.verified_config():
            for p in s.config()['profiles']:
                j=s.job('synthetic-body',p['id'],[{'role':'system','content':'test'},{'role':'user','content':'test'}],{})
                self.assertEqual(s.body_for(j),old.body_for(j))
                self.assertEqual(s.reservation(j),old.reservation(j))

    def test_context_design_writes_only_explicit_root(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(s,'ROOT',Path(tmp)):
            result=s.make_contexts();self.assertEqual(result['blocks'],640)
            self.assertTrue((Path(tmp)/'runs/swarm-ledger-v1-main/contexts-private.json').is_file())
            self.assertEqual(len(s.contexts('main')),640)
            with self.assertRaises(ValueError):s.make_contexts()

    def test_snapshot_copy_and_real_byte_drift(self):
        c=s.config()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'config.json';path.write_text(json.dumps(c),encoding='utf-8')
            with patch.object(s,'CONFIG',path):
                with s.verified_config() as returned:
                    returned['reader_profiles'].clear()
                    self.assertEqual(len(s.config()['reader_profiles']),6)
                with self.assertRaises(ValueError):
                    with s.verified_config():path.write_text(json.dumps(c)+' ',encoding='utf-8')

    def test_wallet_cache_uses_explicit_root(self):
        class Wallet:
            calls=0
            def metadata(self,*args):
                self.calls+=1
                return {'included':{'balance_usd':'50'},'purchased':{'balance_usd':'0'}}
        from decimal import Decimal
        with tempfile.TemporaryDirectory() as tmp,patch.object(s,'ROOT',Path(tmp)):
            w=Wallet();s.BalanceGuard(w).check(Decimal('0.1'),Decimal('0.01'))
            s.BalanceGuard(w).check(Decimal('0.1'),Decimal('0.01'))
            self.assertEqual(w.calls,1)
            self.assertTrue((Path(tmp)/'runs/swarm-ledger-v1-guard/balance-private.json').is_file())

    def test_wallet_metadata_lock_does_not_repeat_remote_read(self):
        class Wallet:
            calls=0
            def metadata(self,*args):
                self.calls+=1
                return {'included':{'balance_usd':'50'},'purchased':{'balance_usd':'0'}}
        from decimal import Decimal
        original=Path.replace;attempts=[]
        def temporarily_locked(path,target):
            attempts.append(1)
            if len(attempts)<3:raise PermissionError('Synthetic sharing violation')
            return original(path,target)
        with tempfile.TemporaryDirectory() as tmp,patch.object(s,'ROOT',Path(tmp)),patch.object(Path,'replace',temporarily_locked):
            w=Wallet();s.BalanceGuard(w).check(Decimal('0.1'),Decimal('0.01'))
            self.assertEqual(w.calls,1);self.assertEqual(len(attempts),3)

if __name__=='__main__':unittest.main()
