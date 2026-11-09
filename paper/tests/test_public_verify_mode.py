"""Synthetic mode routing: no private journals, public release or inference read."""
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch
import zipfile

PAPER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PAPER))
sys.path.insert(0, str(PAPER.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import complete_report_contract as contract
import verify
from test_complete_report_contract import fixture


class PublicVerifyModeTests(unittest.TestCase):
    def setUp(self):
        self.report, self.content = fixture()

    def temporary_release(self, base):
        paper = Path(base) / 'paper'
        paper.mkdir()
        directory = paper.parent / 'data/swarm-ledger-v1-public'
        directory.mkdir(parents=True)
        for name in ('manifest.json', 'report.json', 'registration.json', 'operational-registration.json'):
            (directory / name).write_text('{}', encoding='utf-8')
        research = paper.parent / 'research'
        research.mkdir()
        for name in ('swarm-ledger-paced-v1-freeze.json', 'offline-release-recovery-v2-freeze.json'):
            (research / name).write_text('{}', encoding='utf-8')
        return paper, directory

    def test_public_mode_keeps_frozen_replay_and_identical_bindings(self):
        from experiments import swarm_ledger_complete_analysis as analysis
        from experiments import paced_resume_analysis as paced
        from experiments import offline_release_recovery_v2 as recovery
        admission = types.ModuleType('paper.public_replay')
        admission.verify_public_admission = Mock()
        manifest = dict(registration_sha256='a' * 64, operational_registration_sha256='b' * 64)
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            paper, directory = self.temporary_release(tmp)
            stack.enter_context(patch.dict(sys.modules, {'paper.public_replay': admission}))
            private = stack.enter_context(patch.object(recovery, 'verify'))
            projection = stack.enter_context(patch.object(recovery, 'verify_projection'))
            continuation = stack.enter_context(patch.object(paced, 'verify_main'))
            frozen = stack.enter_context(patch.object(analysis, 'verify_public'))
            stack.enter_context(patch.object(analysis, 'load_public_artifacts', return_value=({}, self.report, manifest)))
            _, public_bindings = contract.load_completed(paper, public_replay=True)
            admission.verify_public_admission.assert_called_once_with(paper)
            private.assert_not_called(); projection.assert_not_called()
            continuation.assert_called_once_with(directory, replay=False)
            frozen.assert_called_once_with(directory)
            _, private_bindings = contract.load_completed(paper)
            self.assertEqual(public_bindings, private_bindings)
            private.assert_called_once_with(); projection.assert_called_once_with(replay=False)
            self.assertEqual(public_bindings['report.json'], hashlib.sha256(b'{}').hexdigest())

    def test_default_private_failure_does_not_fall_back_to_public(self):
        from experiments import offline_release_recovery_v2 as recovery
        from experiments import swarm_ledger_complete_analysis as analysis
        admission = types.ModuleType('paper.public_replay')
        admission.verify_public_admission = Mock()
        with tempfile.TemporaryDirectory() as tmp:
            paper, _ = self.temporary_release(tmp)
            with patch.dict(sys.modules, {'paper.public_replay': admission}), patch.object(recovery, 'verify', side_effect=ValueError('private admission unavailable')), patch.object(analysis, 'verify_public') as frozen:
                with self.assertRaisesRegex(ValueError, 'private admission unavailable'):
                    contract.load_completed(paper)
                admission.verify_public_admission.assert_not_called()
                frozen.assert_not_called()

    def test_public_admission_failure_prevents_any_main_replay(self):
        from experiments import paced_resume_analysis as paced
        from experiments import swarm_ledger_complete_analysis as analysis
        admission = types.ModuleType('paper.public_replay')
        admission.verify_public_admission = Mock(side_effect=ValueError('tampered admission'))
        with tempfile.TemporaryDirectory() as tmp:
            paper, _ = self.temporary_release(tmp)
            with patch.dict(sys.modules, {'paper.public_replay': admission}), patch.object(paced, 'verify_main') as continuation, patch.object(analysis, 'verify_public') as frozen:
                with self.assertRaisesRegex(ValueError, 'tampered admission'):
                    contract.load_completed(paper, public_replay=True)
                continuation.assert_not_called(); frozen.assert_not_called()

    def test_public_mode_still_rejects_bad_scientific_aggregate(self):
        from experiments import swarm_ledger_complete_analysis as analysis
        from experiments import paced_resume_analysis as paced
        admission = types.ModuleType('paper.public_replay')
        admission.verify_public_admission = Mock()
        self.report['source_blocks'] = 639
        with tempfile.TemporaryDirectory() as tmp:
            paper, _ = self.temporary_release(tmp)
            with patch.dict(sys.modules, {'paper.public_replay': admission}), patch.object(paced, 'verify_main'), patch.object(analysis, 'verify_public'), patch.object(analysis, 'load_public_artifacts', return_value=({}, self.report, {})):
                with self.assertRaisesRegex(ValueError, 'denominator'):
                    contract.load_completed(paper, public_replay=True)

    def test_verify_threads_explicit_flag_and_checks_pdf_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            paper = Path(tmp); (paper / 'out').mkdir()
            (paper / 'content.json').write_text(json.dumps(self.content))
            (paper / 'out/pdf-check.json').write_text('{"verified":true}')
            with patch.object(verify, 'validate_source'), patch.object(verify, 'validate_results') as results, patch.object(verify, 'check_docx', return_value=['toy']) as docx, patch.object(verify, 'pdf_manifest', return_value={'verified': True}) as pdf:
                verify.verify(paper, git_checks=False, public_replay=True)
                results.assert_called_once_with(paper, self.content, public_replay=True)
                docx.assert_called_once_with(paper, self.content, public_replay=True)
                pdf.assert_called_once_with(paper, self.content, ['toy'], public_replay=True)
                (paper / 'out/pdf-check.json').write_text('{}')
                with self.assertRaisesRegex(ValueError, 'Stale PDF manifest'):
                    verify.verify(paper, git_checks=False, public_replay=True)

    def test_validate_results_public_flag_does_not_skip_manuscript_validation(self):
        with patch.object(contract, 'load_completed', return_value=(self.report, {})) as load:
            verify.validate_results(PAPER, self.content, public_replay=True)
            load.assert_called_once_with(PAPER, replay=True, public_replay=True)
            self.content['table1'][1][1] = 'tampered'
            with self.assertRaisesRegex(ValueError, 'aggregate differs'):
                verify.validate_results(PAPER, self.content, public_replay=True)

    def test_build_and_pdf_manifests_forward_public_mode_without_new_binding_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            paper = Path(tmp); (paper / 'out').mkdir()
            for name in ('build.py', 'complete_report_contract.py', 'ledger_layout.py'):
                (paper / name).write_text('synthetic source\n')
            (paper / 'out/swarm_audit_scoping.docx').write_bytes(b'synthetic docx hash input')
            (paper / 'out/swarm_audit_scoping.pdf').write_bytes(b'synthetic PDF hash input')
            with zipfile.ZipFile(paper / 'official-template.docx', 'w') as archive:
                archive.writestr('word/footnotes.xml', '<w:footnotes xmlns:w="' + verify.NS['w'] + '"><w:footnote><w:p><w:r><w:t>note</w:t></w:r></w:p></w:footnote></w:footnotes>')
            self.content['title'] = 'Title'
            reader = types.SimpleNamespace(is_encrypted=False, pages=[
                types.SimpleNamespace(extract_text=lambda: 'Title1\nBody\n1note', mediabox=types.SimpleNamespace(width=612, height=792)),
                types.SimpleNamespace(extract_text=lambda: 'References', mediabox=types.SimpleNamespace(width=612, height=792))])
            bindings = {'report.json': 'a' * 64}
            with patch.object(contract, 'load_completed', return_value=(self.report, bindings)) as load, patch.object(verify, 'PdfReader', return_value=reader):
                build = verify.build_manifest(paper, self.content, public_replay=True)
                pdf = verify.pdf_manifest(paper, self.content, ['Title', 'Body', 'References'], public_replay=True)
                self.assertEqual([call.kwargs for call in load.call_args_list],
                                 [dict(replay=False, public_replay=True)] * 2)
                self.assertEqual(build['ledger_sources'], bindings)
                self.assertEqual(pdf['ledger_sources'], bindings)
                self.assertNotIn('public_replay', build)
                self.assertNotIn('public_replay', pdf)

    def test_docx_check_forwards_mode_and_rejects_modified_package_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            paper = Path(tmp); (paper / 'out').mkdir()
            xml = ('<w:document xmlns:w="' + verify.NS['w'] + '"><w:body><w:p><w:r><w:t>Toy</w:t></w:r></w:p></w:body></w:document>').encode()
            (paper / 'out/build-check.json').write_text('{"verified":true}')
            target = paper / 'out/swarm_audit_scoping.docx'
            with zipfile.ZipFile(target, 'w') as archive: archive.writestr('word/document.xml', xml)
            with patch.object(verify, 'assemble', return_value={'word/document.xml': xml}), patch.object(verify, 'build_manifest', return_value={'verified': True}) as build:
                self.assertEqual(verify.check_docx(paper, {}, public_replay=True), ['Toy'])
                build.assert_called_once_with(paper, {}, public_replay=True)
                with zipfile.ZipFile(target, 'w') as archive: archive.writestr('word/document.xml', xml.replace(b'Toy', b'Tampered'))
                with self.assertRaisesRegex(ValueError, 'Stale or modified DOCX part'):
                    verify.check_docx(paper, {}, public_replay=True)

    def test_public_record_pdf_rejected_by_api_and_cli_before_reading_files(self):
        with patch.object(Path, 'read_text', side_effect=AssertionError('must not read')):
            with self.assertRaisesRegex(ValueError, 'cannot record'):
                verify.verify(Path('absent'), record_pdf=True, public_replay=True)
        result = subprocess.run([sys.executable, str(PAPER / 'verify.py'), '--public-replay', '--record-pdf'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('cannot be combined', result.stderr)

    def workflow_blocks(self):
        workflow = (PAPER.parent / '.github/workflows/report-integrity.yml').read_text(encoding='utf-8')
        return [textwrap_block(block) for block in re.findall(r"python - <<'PY'\n(.*?)\n          PY", workflow, re.S)]

    def test_ci_dispatch_is_exact_and_preserves_historical_mode(self):
        block = self.workflow_blocks()[0]
        for content, expected in (({'ledger_registration': contract.REGISTRATION, 'table2_source': 'swarm_ledger_complete'}, ['--public-replay']), ({'table2_source': 'factorial_reporting'}, [])):
            with patch.object(Path, 'read_text', return_value=json.dumps(content)), patch('subprocess.run') as run:
                exec(block, {})
                self.assertEqual(run.call_count, 2)
                self.assertEqual(run.call_args_list[0].args[0], [sys.executable, 'paper/verify.py', *expected])
                self.assertEqual(run.call_args_list[1].args[0], [sys.executable, '-O', 'paper/verify.py', *expected])
        for content in ({'ledger_registration': contract.REGISTRATION, 'table2_source': 'factorial_reporting'}, {'table2_source': 'swarm_ledger_complete'}, {'table2_source': 'unknown'}):
            with patch.object(Path, 'read_text', return_value=json.dumps(content)), patch('subprocess.run') as run:
                with self.assertRaises(SystemExit): exec(block, {})
                run.assert_not_called()

    def test_ci_hf_dispatch_accepts_only_two_registered_tags(self):
        block = self.workflow_blocks()[1]
        for tag, module in (('paced-resume-analysis-v1', 'experiments.paced_resume_analysis'), ('router-resume-analysis-v1', 'experiments.router_resume_analysis')):
            with patch.object(Path, 'read_text', return_value=json.dumps({'analysis_tag': tag})), patch('subprocess.run') as run:
                exec(block, {})
                run.assert_called_once_with([sys.executable, '-m', module, 'verify-hf'], check=True)
        for tag in ('unknown', None, []):
            with patch.object(Path, 'read_text', return_value=json.dumps({'analysis_tag': tag})), patch('subprocess.run') as run:
                with self.assertRaises(SystemExit): exec(block, {})
                run.assert_not_called()


def textwrap_block(block):
    import textwrap
    return textwrap.dedent(block)


if __name__ == '__main__':
    unittest.main()
