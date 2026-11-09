"""Synthetic-only amended-paper checks; no scientific reports are loaded."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

PAPER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PAPER))
from factorial_report_contract import expected_fields
from verify import validate_results


def synthetic_report():
    def effect():
        return dict(n=192, estimate=.125, ci95=[.0625, .1875])
    def bounds():
        return dict(n=192, estimate_lower=190/192, estimate_upper=191/192,
                    unknown_cells=1, width=1/192)
    def metric(calls=192, correct=100):
        return dict(calls=calls, supported_definite=correct)
    def record(planned, main, cal, observed=None, main_observed=None):
        returned = planned if observed is None else observed
        mr = main if main_observed is None else main_observed
        return dict(availability=dict(planned=planned, returned=returned,
                    unstarted=planned-returned, main_planned=main, main_returned=mr,
                    calibration_planned=cal, calibration_returned=returned-mr,
                    complete=returned == planned),
                    by_view={'sufficient':{p:dict(raw=metric(), gated=metric(correct=192))
                                          for p in ('direct','procedure')}},
                    primary_same_packet_procedure_minus_direct=effect())
    models = {m:record(3880,3840,40) for m in ('g26','g31')}
    hf = record(3880,3840,40,1982,1942)
    hf['observed_by_view'] = hf.pop('by_view')
    hf['observed_by_view']['sufficient']['direct']['raw'] = metric(192,0)
    hf['observed_by_view']['sufficient']['procedure']['raw'] = metric(191,190)
    hf['sufficient_identification_bounds'] = bounds()
    del hf['primary_same_packet_procedure_minus_direct']
    models['hf'] = hf
    conditions = {'ds_off':record(3880,3840,40), 'ds_low':record(424,384,40),
                  'gemma_bridge':record(424,384,40)}
    contrasts = {k:dict(status='complete',result=effect()) for k in
                 ('low_minus_off_direct_sufficient','gemma_bridge_minus_adaption31_direct_sufficient')}
    return dict(status='primary_complete_with_registered_extensions',primary_complete=True,
                original_plan_complete=False,extension_plan_complete=True,
                config=dict(monitors=['g26','g31','hf']),training_runs=0,
                analysis=dict(sources=192,actor_calls=576,original_audit_calls=9742,
                extension_audit_calls=4728,main_audit_calls=14230,calibration_calls=240,
                planned_original_audit_calls=11640,planned_extension_audit_calls=4728,
                models=models,complete_models=['g26','g31'],partial_models=['hf'],
                extensions=dict(conditions=conditions,contrasts=contrasts)))


class AmendedPaperContractTests(unittest.TestCase):
    def test_known_zero_is_not_unstarted(self):
        fields = expected_fields(synthetic_report())
        row = fields['table1'][3]
        self.assertEqual(row[1], '0/192')
        self.assertEqual(row[2], '190/191')
        self.assertIn('(192)', row[0])
        self.assertIn('logical bounds', row[3])
        self.assertNotIn('95%', row[3])

    def test_main_calibration_and_source_units(self):
        f = expected_fields(synthetic_report())
        self.assertEqual(f['table2'][1][1:], ['3840/3840','40/40','0'])
        self.assertEqual(f['table2'][3][1:], ['1942/3840','40/40','1898'])
        self.assertEqual(f['table2'][5][1:], ['384/384','40/40','0'])
        self.assertEqual(f['evidence_status']['source_groups'],192)
        self.assertFalse(f['evidence_status']['original_plan_complete'])

    def test_raw_not_gated(self):
        self.assertEqual(expected_fields(synthetic_report())['table1'][1][1],'100/192')

    def test_partial_extension_is_bounds_not_complete_pair_ci(self):
        r = synthetic_report()
        r['extension_plan_complete'] = False
        contrast = r['analysis']['extensions']['contrasts']['low_minus_off_direct_sufficient']
        contrast.clear()
        contrast.update(status='partial',identification_bounds=dict(n=192,estimate_lower=-1,estimate_upper=1))
        row = expected_fields(r)['table3'][1]
        self.assertEqual(row[1], 'partial')
        self.assertIn('logical bounds',row[2])
        self.assertNotIn('CI',row[2])

    def test_wrong_denominators_and_false_full_plan_rejected(self):
        for change in (lambda r:r.update(original_plan_complete=True),
                       lambda r:r['analysis'].update(sources=9742),
                       lambda r:r['analysis']['models']['g26']['primary_same_packet_procedure_minus_direct'].update(n=3880)):
            r=synthetic_report(); change(r)
            with self.assertRaises(ValueError):expected_fields(r)

    def test_verifier_rejects_table_and_status_tampering(self):
        r=synthetic_report()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'paper';root.mkdir();(root.parent/'research').mkdir()
            (root.parent/'research/factorial-report.json').write_text(json.dumps(r),encoding='utf-8')
            original=dict(table2_source='factorial_reporting',**expected_fields(r))
            validate_results(root,original)
            for key in ('table1','table2','table3'):
                bad=copy.deepcopy(original);bad[key][1][1]+=' tampered'
                with self.assertRaisesRegex(ValueError,'Amended paper field differs'):validate_results(root,bad)
            bad=copy.deepcopy(original);bad['evidence_status']['original_plan_complete']=True
            with self.assertRaisesRegex(ValueError,'Amended paper field differs'):validate_results(root,bad)
            bad=copy.deepcopy(original);bad['table1'][1][1]='192/192'
            with self.assertRaisesRegex(ValueError,'Amended paper field differs'):validate_results(root,bad)


if __name__=='__main__':unittest.main()
