"""Unit tests for experiments.live_study runner. No network, env vars or real credentials."""
import json
import tempfile
import unittest
from contextlib import ExitStack
from decimal import Decimal
from pathlib import Path
from unittest import mock

from experiments import live_study as ls

BASE = dict(study_id='s', hf_model='hf-m', hf_input_rate='1', hf_output_rate='1',
            concurrency=4, hf_concurrency=2, input_byte_cap=100000, max_output_tokens=50,
            hf_phase_cap='1000', adaption_phase_cap='1000', gateway_error_allowance_per_phase=8,
            incomplete_allowance_per_phase=2, hf_allowed_returned_models=['hf-m'],
            seed_start=0, qualification_seed_start=900000, episodes_per_family=2,
            qualification_per_family=6, families=['F'], actor_model='actor',
            monitors=['actor', 'm2', 'hf-m'], influence_per_family=1, request_order_seed=7)


def canon(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':'))


def native(model, status='completed', text='ok', usage=(2, 3), **over):
    d = dict(status=status, output_text=text, model=model,
             usage=dict(input_tokens=usage[0], output_tokens=usage[1]))
    d.update(over)
    return d


def hf_native(model='hf-m', **over):
    d = dict(status='completed', output_text='x', model=model,
             usage=dict(prompt_tokens=2, completion_tokens=3))
    d.update(over)
    return d


class LiveRunnerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def cfg(self, **over):
        c = dict(BASE); c.update(over); return c

    def j(self, i, **kw):
        return ls.job('j' + str(i), 'actor', 'prompt-' + str(i), dict(t=i), **kw)

    def go(self, jobs, cfg=None, responder=None, resume=False, pre=None, extra=(), name='out'):
        rec = dict(calls=[], attempts=[], responses=[])
        c = self.cfg(**(cfg or {}))
        out = self.root / name
        if pre: pre(out)

        def durable(fh, obj):
            fh.write(json.dumps(obj) + '\n')
            rec['attempts' if fh.name.endswith('attempts.jsonl') else 'responses'].append(obj)

        def req(url, key, body, timeout=120):
            rec['calls'].append(dict(url=url, key=key, body=body))
            return responder(len(rec['calls']), url, key, body) if responder else ({'http_status': 200}, native(body['model']))

        def norm(d):
            if not isinstance(d, dict): return dict(status='failed', output_text='')
            n = dict(status=d.get('status', 'failed'), output_text=d.get('output_text', ''))
            if not n['output_text'] or d.get('finish_reason') == 'length': n['status'] = 'incomplete'
            return n

        with ExitStack() as st:
            enter = st.enter_context
            enter(mock.patch.object(ls, 'verify', lambda: None)); enter(mock.patch.object(ls, 'config', lambda: c))
            enter(mock.patch.object(ls, 'credentials', lambda: {'HF_TOKEN': 'hk', 'ADAPTION_API_KEY': 'ak'}))
            enter(mock.patch.object(ls, 'sha', lambda p: 'fsha')); enter(mock.patch.object(ls, 'digest', lambda x: 'dg'))
            enter(mock.patch.object(ls, 'canonical', canon)); enter(mock.patch.object(ls, 'scrub', lambda r, k: r))
            enter(mock.patch.object(ls, 'durable', durable)); enter(mock.patch.object(ls, 'rates', lambda m: (Decimal(1), Decimal(1))))
            enter(mock.patch.object(ls, 'request_json', req)); enter(mock.patch.object(ls, 'normalize', norm))
            for nm, val in extra: enter(mock.patch.object(ls, nm, val))
            summary = ls.execute(jobs, out, resume=resume)
        return summary, rec, out

    def test_response_normalization(self):
        norm = lambda d: dict(status=d.get('status', 'failed'), output_text=d.get('output_text', ''))
        with mock.patch.object(ls, 'config', lambda: {'hf_model': 'hf-m'}), mock.patch.object(ls, 'normalize', norm):
            row, known = ls.response(dict(status='completed', output_text='x', model='hf-m',
                                          usage=dict(prompt_tokens=5, completion_tokens=7)), 'hf-m')
            self.assertTrue(known); self.assertEqual(row['usage'], dict(input_tokens=5, output_tokens=7))
            row, known = ls.response(dict(status='completed', output_text='x', model='hf-m', usage=dict(prompt_tokens=5)), 'hf-m')
            self.assertFalse(known); self.assertIsNone(row['usage'])
            row, known = ls.response(dict(status='completed', output_text='y', model='a',
                                          usage=dict(input_tokens=3, output_tokens=4)), 'a')
            self.assertTrue(known); self.assertEqual(row['usage'], dict(input_tokens=3, output_tokens=4))
            row, known = ls.response(None, 'a')
            self.assertEqual((row['status'], row['output_text'], known, row['returned_model']), ('failed', '', False, None))
            row, known = ls.response(dict(status='completed', output_text=None), 'a')
            self.assertEqual((row['status'], row['output_text']), ('failed', ''))

    def test_contexts_counts_from_config(self):
        ctx = lambda s, f, e: dict(seed=s, family=f, authorized=e)
        plan = dict(main=[ctx(5 + 10000*f+j, family, j % 2 == 0) for f, family in enumerate(['A','B']) for j in range(3)],
                    qualification=[ctx(900 + 100000*f+j, family, j % 2 == 0) for f, family in enumerate(['A','B']) for j in range(2)])
        with mock.patch.object(ls, 'design_plan', lambda: plan):
            main = ls.contexts(); qual = ls.contexts(True)
        self.assertEqual(len(main), 6); self.assertEqual(len(qual), 4)
        self.assertEqual([c['seed'] for c in main[:3]], [5, 6, 7])
        self.assertEqual([c['seed'] for c in qual], [900, 901, 100900, 100901])

    def _receiver_patches(self, ctx):
        return [mock.patch.object(ls, 'config', lambda: self.cfg()),
                mock.patch.object(ls, 'contexts', lambda q=False: [ctx]),
                mock.patch.object(ls, 'origin_rows', lambda q=False: {0: dict(response=dict(output_text='ORIG', status='completed'))}),
                mock.patch.object(ls, 'decode_origin', lambda t: dict(valid=True, decoy_action='mark', handoff_note='note')),
                mock.patch.object(ls, 'canonical', canon)]

    def test_receiver_solo_replays_history_delegated_fresh(self):
        ctx = dict(seed=0, family='F', authorized=True, initial=5, approvals=2, route=['actor', 'peer'])
        with ExitStack() as st:
            for p in self._receiver_patches(ctx): st.enter_context(p)
            jobs = ls.receiver_jobs(False)
        solo = next(j for j in jobs if j['metadata']['mode'] == 'solo')
        dele = next(j for j in jobs if j['metadata']['mode'] == 'delegated')
        self.assertEqual(solo['history'], [dict(role='user', content=canon(ls.origin_input(ctx))), dict(role='assistant', content='ORIG')])
        self.assertEqual(dele['history'], [])
        self.assertEqual((solo['payload']['worker'], dele['payload']['worker']), ('actor', 'peer'))
        self.assertEqual(solo['payload']['first_turn']['handoff_note'], 'note')
        self.assertNotIn('additional_warning', solo['payload'])

    def test_receiver_influence_exposures_and_boundary(self):
        ctx = dict(seed=0, family='F', authorized=True, initial=5, approvals=2, route=['actor', 'peer'])
        with ExitStack() as st:
            for p in self._receiver_patches(ctx): st.enter_context(p)
            jobs = ls.receiver_jobs(False, True)
            st.enter_context(mock.patch.object(ls, 'config', lambda: self.cfg(influence_per_family=0)))
            none = ls.receiver_jobs(False, True)
        mal = next(j for j in jobs if j['metadata']['exposure'] == 'malicious')
        warn = next(j for j in jobs if j['metadata']['exposure'] == 'warning')
        self.assertEqual(len(jobs), 3)
        self.assertEqual({j['metadata']['exposure'] for j in jobs}, {'malicious', 'warning', 'benign'})
        self.assertTrue(all(j['metadata']['mode'] == 'delegated' and j['history'] == [] for j in jobs))
        self.assertTrue(mal['payload']['first_turn']['handoff_note'].rstrip().endswith('report done.'))
        self.assertIn('additional_warning', warn['payload'])
        self.assertEqual(none, [])

    def test_plan_guards(self):
        jobs = [self.j(1), self.j(2)]
        plan = dict(freeze_sha256='fsha', jobs_sha256='dg', ids=['j1', 'j2'], planned=2)

        def mk(out, plan_text=None, attempts=''):
            out.mkdir(parents=True)
            (out / 'plan.json').write_text(plan_text if plan_text is not None else json.dumps(plan))
            if attempts: (out / 'attempts.jsonl').write_text(attempts)
        row = json.dumps(dict(id='j1', request_sha256='dg', reserved_cost='0.1', provider='adaption', started='t'))
        cases = [(lambda o: mk(o), False, 'Output exists'),
                 (lambda o: mk(o, json.dumps({**plan, 'ids': ['j1']})), True, 'Continuation plan changed'),
                 (lambda o: mk(o, attempts=row), True, 'never retry'),
                 (lambda o: mk(o, attempts=json.dumps(dict(id='ghost'))), True, 'never retry'),
                 (lambda o: mk(o, attempts=row + '\n' + row), True, 'never retry')]
        with self.assertRaisesRegex(ValueError, 'Duplicate jobs'): self.go([self.j(1), self.j(1)])
        for index, (pre, resume, msg) in enumerate(cases):
            with self.subTest(msg=msg), self.assertRaisesRegex(ValueError, msg):
                self.go(jobs, pre=pre, resume=resume, name='case'+str(index))

    def test_resume_runs_only_unstarted_complement(self):
        jobs = [self.j(1), self.j(2)]

        def pre(out):
            out.mkdir(parents=True)
            (out / 'plan.json').write_text(json.dumps(plan))
            (out / 'attempts.jsonl').write_text(json.dumps(dict(id='j1', request_sha256='dg', reserved_cost='0.1', provider='adaption', started='t')) + '\n')
            (out / 'responses.jsonl').write_text(json.dumps(dict(id='j1', model='actor', metadata={}, provider='adaption',
                transport=dict(http_status=200), response=dict(status='completed', output_text='ok',
                usage=dict(input_tokens=2, output_tokens=3), returned_model='actor'), known_usage=True,
                estimated_cost='0.000005', native_response={})) + '\n')
        plan = dict(freeze_sha256='fsha', jobs_sha256='dg', ids=['j1', 'j2'], planned=2)
        summary, rec, out = self.go(jobs, resume=True, pre=pre)
        self.assertEqual([c['body']['input'] for c in rec['calls']], [canon(dict(t=2))])
        self.assertTrue(summary['complete']); self.assertEqual(summary['unstarted'], 0)

    def test_resume_rejects_unsafe_prior_row(self):
        resp = lambda n, u, k, b: ({'http_status': 200}, dict(status='completed', output_text='x', model=b['model']))
        s1, rec, out = self.go([self.j(1), self.j(2)], cfg=dict(concurrency=1), responder=resp)
        self.assertTrue(s1['halted']); self.assertEqual(rec['responses'][0]['known_usage'], False)
        with self.assertRaises(ValueError): self.go([self.j(1), self.j(2)], resume=True)

    def test_reservation_budget_halts_then_resume_completes(self):
        s1, rec, out = self.go([self.j(1), self.j(2)], cfg=dict(adaption_phase_cap='0.05'))
        self.assertTrue(s1['halted']); self.assertEqual(s1['unstarted'], 2); self.assertFalse(s1['complete'])
        self.assertEqual(rec['calls'], []); self.assertEqual(rec['attempts'], [])
        s2, rec2, out = self.go([self.j(1), self.j(2)], resume=True)
        self.assertTrue(s2['complete']); self.assertEqual(len(rec2['calls']), 2)

    def test_unknown_usage_halts_and_drains_inflight(self):
        resp = lambda n, u, k, b: ({'http_status': 200}, dict(status='completed', output_text='x', model=b['model']))
        summary, rec, out = self.go([self.j(1), self.j(2), self.j(3)], cfg=dict(concurrency=2), responder=resp)
        self.assertTrue(summary['halted']); self.assertEqual(len(rec['calls']), 2); self.assertEqual(summary['unstarted'], 1)
        self.assertEqual(len(rec['attempts']), 2); self.assertEqual(len(rec['responses']), 2)
        self.assertEqual(Decimal(summary['costs']['adaption']), Decimal('0.20010'))

    def test_auth_error_halts_and_retains_started_batch(self):
        resp = lambda n, u, k, b: ({'http_status': 403}, native(b['model']))
        summary, rec, out = self.go([self.j(1), self.j(2), self.j(3)], cfg=dict(concurrency=2), responder=resp)
        self.assertTrue(summary['halted'])
        self.assertEqual(summary['unstarted'], 1)
        self.assertEqual(len(rec['calls']), 2)
        self.assertEqual(len(rec['attempts']), len(rec['responses']))

    def test_gateway_allowance_eight_halts_on_ninth(self):
        resp = lambda n, u, k, b: ({'http_status': 502}, None)
        s9, rec, out = self.go([self.j(i) for i in range(9)], cfg=dict(concurrency=9), responder=resp, name='out9')
        self.assertTrue(s9['halted']); self.assertEqual(s9['gateway_errors'], 9); self.assertEqual(s9['unstarted'], 0)
        self.assertEqual(len(rec['attempts']), 9)
        s8, rec8, out = self.go([self.j(i) for i in range(8)], cfg=dict(concurrency=8), responder=resp, name='out8')
        self.assertFalse(s8['halted']); self.assertTrue(s8['complete'])

    def test_third_incomplete_halts(self):
        resp = lambda n, u, k, b: ({'http_status': 200}, native(b['model'], status='incomplete', text='p', usage=(1, 1)))
        s3, rec, out = self.go([self.j(i) for i in range(3)], cfg=dict(concurrency=3), responder=resp, name='out3')
        self.assertTrue(s3['halted']); self.assertEqual(s3['incomplete'], 3)
        s2, rec2, out = self.go([self.j(i) for i in range(2)], cfg=dict(concurrency=2), responder=resp, name='out2')
        self.assertFalse(s2['halted']); self.assertTrue(s2['complete'])

    def test_hf_body_concurrency_cap_and_empty_incomplete(self):
        resp = lambda n, u, k, b: ({'http_status': 200}, hf_native(output_text='' if n == 3 else 'x'))
        jobs = [ls.job('h' + str(i), 'hf-m', 'p', dict(t=i)) for i in range(3)]
        summary, rec, out = self.go(jobs, cfg=dict(concurrency=4, hf_concurrency=2), responder=resp)
        self.assertEqual(len(rec['calls']), 3)
        self.assertTrue(all(c['url'] == ls.HF + '/chat/completions' and c['key'] == 'hk' for c in rec['calls']))
        b = rec['calls'][0]['body']
        self.assertEqual(b['messages'], [dict(role='system', content='p'), dict(role='user', content=canon(dict(t=0)))])
        self.assertEqual((b['temperature'], b['max_tokens'], b['stream']), (0, 50, False))
        self.assertEqual(rec['responses'][2]['response']['status'], 'incomplete')
        self.assertTrue(summary['complete']); self.assertFalse(summary['halted'])

    def test_adaption_body_and_success_summary(self):
        summary, rec, out = self.go([self.j(1, source_seed=3)])
        c = rec['calls'][0]; b = c['body']
        self.assertEqual(c['url'], ls.ADAPTION + '/responses'); self.assertEqual(c['key'], 'ak')
        self.assertEqual(b['instructions'], 'prompt-1'); self.assertEqual(b['input'], canon(dict(t=1)))
        self.assertEqual((b['temperature'], b['max_output_tokens'], b['tools'], b['tool_choice'], b['agentic_memory'], b['store']),
                         (0, 50, [], 'none', False, False))
        self.assertTrue(summary['complete']); self.assertEqual(summary['planned'], 1)
        row = rec['responses'][0]
        self.assertEqual((row['provider'], row['known_usage'], row['metadata']['source_seed']), ('adaption', True, 3))
        self.assertGreater(Decimal(summary['costs']['adaption']), Decimal(0))
        self.assertEqual(json.loads((out / 'plan.json').read_text())['ids'], ['j1'])

    def test_input_byte_bound(self):
        with self.assertRaises(ValueError): self.go([self.j(1)], cfg=dict(input_byte_cap=10))

    def test_qualification_encoding_gate_95_no_accuracy(self):
        def stage(nm, rws):
            p = self.root / nm; p.mkdir(parents=True, exist_ok=True)
            (p / 'summary.json').write_text(json.dumps(dict(complete=True)))
            (p / 'responses.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rws))
        def rws(n, bad=0):
            return [dict(id=str(i), model=BASE['monitors'][i % 3], known_usage=True, transport=dict(http_status=200),
                         response=dict(status='completed', output_text='bad' if i < bad else 'good')) for i in range(n)]
        patches = [mock.patch.object(ls, 'folder', lambda s: self.root / s),
                   mock.patch.object(ls, 'config', lambda: self.cfg()),
                   mock.patch.object(ls, 'decode_origin', lambda t: dict(valid=True)),
                   mock.patch.object(ls, 'decode_worker', lambda t: dict(valid=True)),
                   mock.patch.object(ls, 'score_stateful', lambda r, a: dict(status='INVALID' if r['output_text'] == 'bad' else 'VALID'))]
        stage('qualification-origins', rws(6)); stage('qualification-receivers', rws(12)); stage('qualification-audits', rws(252, bad=12))
        with ExitStack() as st:
            for p in patches: st.enter_context(p)
            result = ls.qualification_pass()
        self.assertTrue(result['passed']); self.assertIn('not answer accuracy', result['gate'])
        stage('qualification-audits', rws(252, bad=13))
        with ExitStack() as st:
            for p in patches: st.enter_context(p)
            with self.assertRaises(ValueError): ls.qualification_pass()
        serve = rws(6); serve[0]['known_usage'] = False
        stage('qualification-origins', serve); stage('qualification-audits', rws(252))
        with ExitStack() as st:
            for p in patches: st.enter_context(p)
            with self.assertRaises(ValueError): ls.qualification_pass()


if __name__ == '__main__':
    unittest.main()
