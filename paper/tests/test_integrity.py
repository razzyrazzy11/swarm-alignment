"""Regression tests for stale artifacts and guards that must survive -O."""
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
from verify import verify, validate_source, build_manifest


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'paper'
        self.root.mkdir()
        for name in ('content.json','official-template.docx','build.py','verify.py'):
            shutil.copy2(PAPER/name,self.root/name)
        shutil.copytree(PAPER/'out',self.root/'out')
        (self.root.parent/'research').mkdir()
        shutil.copy2(PAPER.parent/'research/pilot-results.json',self.root.parent/'research/pilot-results.json')
        for name in ('stateful-config.json','stateful-freeze.json','stateful-qualification.json'):
            if (PAPER.parent/'research'/name).exists():
                shutil.copy2(PAPER.parent/'research'/name,self.root.parent/'research'/name)

    def source(self):
        return json.loads((self.root/'content.json').read_text(encoding='utf-8'))

    def save(self,d):
        (self.root/'content.json').write_text(json.dumps(d,ensure_ascii=False),encoding='utf-8')

    def test_current_package(self):
        verify(self.root,git_checks=False)

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
        del d['sections'][0][1][1]
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
