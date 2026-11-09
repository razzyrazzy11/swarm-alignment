"""Regression tests for stale artifacts and guards that must survive -O."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

PAPER=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PAPER))
from build import assemble
from verify import verify, validate_source, validate_results, build_manifest


HISTORICAL_FIXTURE=PAPER/'tests/fixtures/results-v3'
HISTORICAL_SOURCE_COMMIT='166da1cd1d5b725455b03fb9a47aaf1e2b8dabe5'
HISTORICAL_MANIFEST_SHA256='68359087a58a5e3df4fdae4f3f4fb687130eabaa94beb6339776d3ea4140a4fa'
HISTORICAL_FILES={'content.json','out/swarm_audit_scoping.docx','out/swarm_audit_scoping.pdf',
                  'out/build-check.json','out/pdf-check.json'}


def verified_historical_fixture(root=HISTORICAL_FIXTURE):
    """Pin the last green legacy paper; never read the live manuscript as a toy."""
    root=Path(root)
    raw=(root/'manifest.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=HISTORICAL_MANIFEST_SHA256:
        raise ValueError('Historical paper fixture manifest hash differs')
    manifest=json.loads(raw)
    if (manifest.get('schema_version')!=1 or manifest.get('source_commit')!=HISTORICAL_SOURCE_COMMIT
            or set(manifest.get('files_sha256',{}))!=HISTORICAL_FILES):
        raise ValueError('Historical paper fixture manifest differs')
    for name,expected in manifest['files_sha256'].items():
        path=root/name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise ValueError('Historical paper fixture hash differs: '+name)
    return root


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'paper'
        self.root.mkdir()
        historical=verified_historical_fixture()
        shutil.copy2(historical/'content.json',self.root/'content.json')
        for name in ('official-template.docx','build.py','verify.py'):
            shutil.copy2(PAPER/name,self.root/name)
        shutil.copytree(historical/'out',self.root/'out')
        (self.root.parent/'research').mkdir()
        shutil.copy2(PAPER.parent/'research/pilot-results.json',self.root.parent/'research/pilot-results.json')
        for name in ('stateful-config.json','stateful-main-v2-freeze.json','stateful-main-v2-continuation-v1-freeze.json','stateful-qualification.json','hf-stateful-config.json','stateful-hf-v3-freeze.json','stateful-results.json'):
            if (PAPER.parent/'research'/name).exists():
                shutil.copy2(PAPER.parent/'research'/name,self.root.parent/'research'/name)
        for name in ('live-config.json','live-audit-v2-freeze.json','live-audit-v2-continuation-v1-freeze.json','live-qualification-v1.json','live-results.json','weight-config.json','weight-audit-v1-freeze.json','weight-results.json'):
            if (PAPER.parent/'research'/name).exists():shutil.copy2(PAPER.parent/'research'/name,self.root.parent/'research'/name)
        for name in ('factorial-config.json','factorial-audit-v1-freeze.json','factorial-results.json'):
            if (PAPER.parent/'research'/name).exists():shutil.copy2(PAPER.parent/'research'/name,self.root.parent/'research'/name)
        if self.source().get('table2_source') == 'factorial_reporting':
            # The amended branch validates its exact public-report contract and
            # hashes these sources into the build manifest. Require every
            # fixture dependency rather than hiding missing files in tests.
            shutil.copy2(PAPER/'factorial_report_contract.py',self.root/'factorial_report_contract.py')
            for name in ('factorial-reporting-freeze.json','factorial-report.json',
                         'ollama-reader-v1-freeze.json'):
                shutil.copy2(PAPER.parent/'research'/name,self.root.parent/'research'/name)

    def source(self):
        return json.loads((self.root/'content.json').read_text(encoding='utf-8'))

    def save(self,d):
        (self.root/'content.json').write_text(json.dumps(d,ensure_ascii=False),encoding='utf-8')

    def test_current_package(self):
        verify(self.root,git_checks=False)

    def test_reader_call_denominator_is_exact(self):
        d=self.source()
        import re
        if d.get('table2_source') == 'factorial_reporting':
            observed, planned = d['table2'][1][1].split('/')
            d['table2'][1][1] = observed+'/'+str(int(planned)+1)
            with self.assertRaisesRegex(ValueError,'Amended paper field differs from public report: table2'):
                validate_results(self.root,d)
            return
        d['table2'][1][0]=re.sub(r'\((\d+)\)$',lambda m:'('+m[1]+'0)',d['table2'][1][0])
        with self.assertRaisesRegex(ValueError,'Reader table differs'):
            validate_results(self.root,d)

    def test_hf_matched_source_denominator_is_exact(self):
        d=self.source()
        import re
        if d.get('table2_source') == 'factorial_reporting':
            # The original HF reader is partial: its 192 planned source units
            # remain explicit in table1; table3 now contains extension contrasts.
            before = d['table1'][3][0]
            d['table1'][3][0]=re.sub(r'\((\d+)\)$',lambda m:'('+str(int(m[1])+1)+')',before)
            self.assertNotEqual(before,d['table1'][3][0])
            with self.assertRaisesRegex(ValueError,'Amended paper field differs from public report: table1'):
                validate_results(self.root,d)
            return
        d['table3'][3][0]=re.sub(r'\((\d+)\)$',lambda m:'('+m[1]+'0)',d['table3'][3][0])
        with self.assertRaisesRegex(ValueError,'Weight variant denominator' if d.get('table2_source')=='live' else 'Effect source denominator'):
            validate_results(self.root,d)

    def test_unrebuilt_prose_fails(self):
        d=self.source()
        d['sections'][0][1][0]+=' Changed source without rebuilding.'
        self.save(d)
        with self.assertRaisesRegex(ValueError,'Stale or modified DOCX'):
            verify(self.root,git_checks=False)

    def test_modified_preserved_part_fails(self):
        path=self.root/'out/swarm_audit_scoping.docx'
        with zipfile.ZipFile(path) as z:
            parts={n:z.read(n) for n in z.namelist()}
        parts['word/styles.xml']+=b' '
        with zipfile.ZipFile(path,'w') as z:
            for name,data in parts.items():
                z.writestr(name,data)
        with self.assertRaisesRegex(ValueError,'Stale or modified DOCX'):
            verify(self.root,git_checks=False)

    def test_pdf_bytes_tampering_fails(self):
        path=self.root/'out/swarm_audit_scoping.pdf'
        path.write_bytes(path.read_bytes()+b'\n% modified export\n')
        with self.assertRaisesRegex(ValueError,'Stale PDF manifest'):
            verify(self.root,git_checks=False)

    def test_pdf_content_missing_fails(self):
        from pypdf import PdfReader,PdfWriter
        path=self.root/'out/swarm_audit_scoping.pdf'
        reader=PdfReader(path)
        writer=PdfWriter()
        writer.add_page(reader.pages[0])
        writer.write(path)
        with self.assertRaisesRegex(ValueError,'PDF text missing/stale'):
            verify(self.root,git_checks=False)

    def test_unknown_marker_fails(self):
        d=self.source()
        d['sections'][0][1].append('TABLE99')
        with self.assertRaisesRegex(ValueError,'Unknown content marker'):
            assemble(d,self.root/'official-template.docx')

    def test_removed_prose_left_in_pdf_cannot_be_attested(self):
        d=self.source()
        # Remove citation-free prose so citation validation still passes and
        # this test reaches the PDF's extra-text guard.
        d['sections'][0][1][0]=d['sections'][0][1][0].partition('. ')[2]
        self.save(d)
        parts=assemble(d,self.root/'official-template.docx')
        with zipfile.ZipFile(self.root/'out/swarm_audit_scoping.docx','w') as z:
            for name,data in parts.items():
                z.writestr(name,data)
        (self.root/'out/build-check.json').write_text(json.dumps(build_manifest(self.root,d)),encoding='utf-8')
        previous=(self.root/'out/pdf-check.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'PDF has extra/stale/reordered text'):
            verify(self.root,record_pdf=True,git_checks=False)
        self.assertEqual(previous,(self.root/'out/pdf-check.json').read_bytes())

    def test_orphan_reference_fails(self):
        d=self.source()
        d['references'].append(f"[{len(d['references'])+1}] Unused source.")
        with self.assertRaisesRegex(ValueError,'Citation/reference mismatch'):
            validate_source(d)

    def test_optimized_python_rejects_invalid_source(self):
        d=self.source()
        d['abstract']='Too short.'
        self.save(d)
        result=subprocess.run([sys.executable,'-O',str(self.root/'verify.py')],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('FAIL:',result.stderr)


if __name__=='__main__':
    unittest.main()
