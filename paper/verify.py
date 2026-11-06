"""Check submission constraints and template preservation; no inference calls."""
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as E
import zipfile

ROOT = Path(__file__).resolve().parents[1]
content = json.loads((ROOT/'paper/content.json').read_text(encoding='utf-8'))
assert 150 <= len(content['abstract'].split()) <= 250
assert any('Limitations and Dual-Use / Ethical Considerations' in h for h,_ in content['appendix'])
with zipfile.ZipFile(ROOT/'paper/official-template.docx') as src, zipfile.ZipFile(ROOT/'paper/out/swarm_audit_scoping.docx') as dst:
    assert set(src.namelist()) == set(dst.namelist())
    assert [n for n in src.namelist() if src.read(n)!=dst.read(n)] == ['word/document.xml']
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    a=E.fromstring(src.read('word/document.xml'));b=E.fromstring(dst.read('word/document.xml'))
    assert E.tostring(a.find('w:body/w:sectPr',ns))==E.tostring(b.find('w:body/w:sectPr',ns))
    manuscript=' '.join(t.text or '' for t in b.findall('.//w:t',ns))
    for placeholder in ['PROJECT TITLE','Author name 1','How to use this template','[Reference 1]']:
        assert placeholder not in manuscript
    assert 'No agent-performance experiments are reported.' in manuscript
    assert all(h in manuscript for h,_ in content['sections'])
protected=['.env','.env.production','private.pem','private.key','id_rsa','id_ed25519','.modal.toml','runs/raw.json','nested/runs-test/raw.json']
result=subprocess.run(['git','check-ignore','--no-index',*protected],cwd=ROOT,text=True,capture_output=True,check=True)
assert set(result.stdout.splitlines())==set(protected)
assert subprocess.run(['git','check-ignore','--no-index','.env.example'],cwd=ROOT,capture_output=True).returncode==1
print('PASS: abstract, appendix, template preservation, guidance removal, claim scope and secret/raw-output exclusions')
