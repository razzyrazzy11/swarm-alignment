"""Build from the retained official template; preserve every other package part."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import zipfile
from lxml import etree as E

ROOT = Path(__file__).resolve().parent
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
W = '{' + NS['w'] + '}'
SHA = '20bb4d221e722f7eca33c7bd3add4c749ddc76d346b12cdb9ada271083e3a36d'

def text(el):
    return ''.join(el.xpath('.//w:t/text()', namespaces=NS))

def replace(p, value, keep_footnote=False):
    props = deepcopy(p.find(W+'pPr'))
    runs = p.findall(W+'r')
    rprops = next((deepcopy(r.find(W+'rPr')) for r in runs if r.find(W+'rPr') is not None), None)
    notes = [deepcopy(r) for r in runs if r.find(W+'footnoteReference') is not None] if keep_footnote else []
    for ch in list(p):
        p.remove(ch)
    # Cloned paragraph IDs must not be duplicated.
    p.attrib.clear()
    if props is not None:
        p.append(props)
    r = E.SubElement(p,W+'r')
    if rprops is not None:
        r.append(rprops)
    t = E.SubElement(r,W+'t')
    t.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
    t.text = value
    for n in notes:
        p.append(n)
    return p

def main():
    template = ROOT/'official-template.docx'
    assert hashlib.sha256(template.read_bytes()).hexdigest() == SHA, 'Template changed'
    content = json.loads((ROOT/'content.json').read_text(encoding='utf-8'))
    assert 150 <= len(content['abstract'].split()) <= 250
    with zipfile.ZipFile(template) as z:
        parts = {i.filename:z.read(i.filename) for i in z.infolist()}
    doc = E.fromstring(parts['word/document.xml'])
    body = doc.find(W+'body')
    original_section = E.tostring(body.find(W+'sectPr'))
    paras = body.findall(W+'p')
    heading = deepcopy(next(p for p in paras if text(p)=='1. Introduction'))
    normal = deepcopy(next(p for p in paras if text(p).startswith('What problem are you addressing')))
    # Remove italic instructional emphasis while retaining the template font/size.
    for el in normal.xpath('.//w:i | .//w:iCs | .//w:numPr', namespaces=NS):
        el.getparent().remove(el)
    pr = normal.find(W+'pPr')
    if pr is None:
        pr = E.SubElement(normal,W+'pPr')
    sp = E.SubElement(pr,W+'spacing')
    sp.set(W+'after','120')
    title_table = body.findall(W+'tbl')[0]
    title = next(p for p in title_table.xpath('.//w:p',namespaces=NS) if text(p)=='PROJECT TITLE')
    replace(title,content['title'],True)
    # Fix the source's narrow six-author table using one source-derived paragraph.
    author_cell = next(c for c in title_table.xpath('.//w:tc',namespaces=NS) if any(text(p).startswith('Author name 1') for p in c.findall(W+'p')))
    author_table = author_cell.getparent().getparent()
    author_p = deepcopy(author_cell.find(W+'p'))
    replace(author_p, content['author']+' | '+content['affiliation'])
    parent = author_table.getparent()
    parent.replace(author_table,author_p)
    abstract_p = next(p for p in title_table.xpath('.//w:p',namespaces=NS) if text(p).startswith('Summarize your project'))
    replace(abstract_p,content['abstract'])
    for el in abstract_p.xpath('.//w:i | .//w:iCs | .//w:u',namespaces=NS):
        el.getparent().remove(el)
    # Subtitle is a cloned centered author paragraph, directly below the title.
    subtitle = deepcopy(author_p)
    replace(subtitle,content['subtitle'])
    title.addnext(subtitle)
    section = deepcopy(body.find(W+'sectPr'))
    for ch in list(body):
        if ch is not title_table:
            body.remove(ch)

    def add(value, is_heading=False, page=False):
        p = deepcopy(heading if is_heading else normal)
        replace(p,value)
        if page:
            props = p.find(W+'pPr')
            E.SubElement(props,W+'pageBreakBefore')
        body.append(p)
        return p

    def table(rows,widths):
        t=E.SubElement(body,W+'tbl')
        props=E.SubElement(t,W+'tblPr')
        tw=E.SubElement(props,W+'tblW');tw.set(W+'w','9360');tw.set(W+'type','dxa')
        borders=E.SubElement(props,W+'tblBorders')
        for name in ['top','left','bottom','right','insideH','insideV']:
            b=E.SubElement(borders,W+name);b.set(W+'val','single');b.set(W+'sz','4');b.set(W+'color','AAAAAA')
        grid=E.SubElement(t,W+'tblGrid')
        for width in widths:
            col=E.SubElement(grid,W+'gridCol');col.set(W+'w',str(width))
        for i,row in enumerate(rows):
            tr=E.SubElement(t,W+'tr')
            trpr=E.SubElement(tr,W+'trPr');E.SubElement(trpr,W+'cantSplit')
            if i==0:E.SubElement(trpr,W+'tblHeader')
            for val,width in zip(row,widths):
                cell=E.SubElement(tr,W+'tc');cp=E.SubElement(cell,W+'tcPr')
                cw=E.SubElement(cp,W+'tcW');cw.set(W+'w',str(width));cw.set(W+'type','dxa')
                p=deepcopy(normal);replace(p,val);cell.append(p)
                if i==0:
                    for rp in p.xpath('.//w:rPr',namespaces=NS):E.SubElement(rp,W+'b')
        return t

    for name,paragraphs in content['sections']:
        add(name,True)
        for value in paragraphs:
            if value=='TABLE1':
                add('Table 1. Existing results and the narrower proposed test. These are research-design comparisons, not measured performance.')
                table([
                    ['Prior work','Already established','Proposed extension'],
                    ['Trace tampering [3]','Integrity and completeness matter','Targeted loss × identity churn'],
                    ['Evidence binding [6]','Supported findings differ from correct guesses','Coordinated multi-worker missingness'],
                    ['HELIOS [7]','Joint inference from activation sensors','Black-box preservation tradeoff']
                ],[2200,3400,3760])
            elif value=='FIGURE1':
                table([
                    ['Hidden history','Visible packet after erasure','Correct actor'],
                    ['H_A: worker A updates record','Update complete; actor link absent','A'],
                    ['H_B: worker B updates record','Update complete; actor link absent','B']
                ],[2600,4800,1960])
                add('Figure 1. Two histories collapse to identical evidence. Any monitor restricted to this packet must guess or abstain. Retaining a trustworthy actor–operation receipt makes the observations differ. This construction is analytical, not an observed agent run.')
            else:add(value)
    add('References',True,True)
    for ref in content['references']:add(ref)
    for i,(name,paragraphs) in enumerate(content['appendix']):
        add(name,True,i==0)
        for value in paragraphs:add(value)
    body.append(section)
    assert E.tostring(section)==original_section
    all_text=text(doc)
    assert 'Author name' not in all_text and 'How to use this template' not in all_text
    assert all_text.count('Swarm Alignment') >= 1
    parts['word/document.xml']=E.tostring(doc,xml_declaration=True,encoding='UTF-8',standalone=True)
    out=ROOT/'out';out.mkdir(exist_ok=True)
    target=out/'swarm_audit_scoping.docx'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in parts.items():z.writestr(name,data)
    with zipfile.ZipFile(template) as a,zipfile.ZipFile(target) as b:
        changed=[n for n in a.namelist() if a.read(n)!=b.read(n)]
    assert changed==['word/document.xml'],changed
    (out/'build-check.json').write_text(json.dumps({'abstract_words':len(content['abstract'].split()),'template_sha256':SHA,'changed_package_parts':changed,'empirical_experiments':0},indent=2)+'\n',encoding='utf-8')
    print(target)

if __name__=='__main__':main()
