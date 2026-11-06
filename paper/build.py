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

def require(condition, message):
    if not condition:
        raise ValueError(message)


def assemble(content, template):
    require(hashlib.sha256(template.read_bytes()).hexdigest() == SHA, 'Template changed')
    require(150 <= len(content['abstract'].split()) <= 250, 'Abstract must contain 150–250 words')
    require(bool(content.get('table1')), 'Missing source-driven table1')
    require(all(len(row)==3 for row in content['table1']), 'table1 must have three columns')
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
    sp = pr.find(W+'spacing')
    if sp is None:
        sp=E.Element(W+'spacing')
        # Spacing precedes indentation, justification and paragraph rPr.
        later=(W+'ind',W+'contextualSpacing',W+'mirrorIndents',W+'suppressOverlap',W+'jc',W+'textDirection',W+'textAlignment',W+'textboxTightWrap',W+'outlineLvl',W+'divId',W+'cnfStyle',W+'rPr',W+'sectPr',W+'pPrChange')
        pos=next((i for i,ch in enumerate(pr) if ch.tag in later),len(pr))
        pr.insert(pos,sp)
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
            # pageBreakBefore precedes spacing/indentation in CT_PPr.
            earlier=(W+'pStyle',W+'keepNext',W+'keepLines')
            pos=sum(ch.tag in earlier for ch in props)
            props.insert(pos,E.Element(W+'pageBreakBefore'))
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
                    for rp in p.xpath('.//w:rPr',namespaces=NS):
                        # Bold precedes size/language, but follows rStyle/rFonts.
                        pos=sum(ch.tag in (W+'rStyle',W+'rFonts') for ch in rp)
                        rp.insert(pos,E.Element(W+'b'))
        return t

    for name,paragraphs in content['sections']:
        add(name,True)
        for value in paragraphs:
            if value=='TABLE1':
                add('Table 1. Existing results and the narrower proposed test. These are research-design comparisons, not measured performance.')
                table(content['table1'],[2200,3400,3760])
            elif value=='FIGURE1':
                table([
                    ['Hidden history','Visible packet after erasure','Correct actor'],
                    ['H_A: worker A updates record','Update complete; actor link absent','A'],
                    ['H_B: worker B updates record','Update complete; actor link absent','B']
                ],[2600,4800,1960])
                add('Figure 1. Two histories collapse to identical evidence. Any monitor restricted to this packet must guess or abstain. Retaining a trustworthy actor–operation receipt makes the observations differ. This construction is analytical, not an observed agent run.')
            else:
                import re
                require(not re.fullmatch(r'(?:TABLE|FIGURE)\d+',value), 'Unknown content marker: '+value)
                add(value)
    add('References',True,True)
    for ref in content['references']:add(ref)
    for i,(name,paragraphs) in enumerate(content['appendix']):
        add(name,True,i==0)
        for value in paragraphs:add(value)
    body.append(section)
    require(E.tostring(section)==original_section, 'Section geometry changed')
    all_text=text(doc)
    require('Author name' not in all_text and 'How to use this template' not in all_text, 'Template guidance remains')
    parts['word/document.xml']=E.tostring(doc,xml_declaration=True,encoding='UTF-8',standalone=True)
    return parts


def main():
    template=ROOT/'official-template.docx'
    content=json.loads((ROOT/'content.json').read_text(encoding='utf-8'))
    parts=assemble(content,template)
    out=ROOT/'out';out.mkdir(exist_ok=True)
    target=out/'swarm_audit_scoping.docx'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in parts.items():z.writestr(name,data)
    with zipfile.ZipFile(template) as a,zipfile.ZipFile(target) as b:
        changed=[n for n in a.namelist() if a.read(n)!=b.read(n)]
    require(changed==['word/document.xml'], 'Unexpected changed parts: '+str(changed))
    from verify import build_manifest
    (out/'build-check.json').write_text(json.dumps(build_manifest(ROOT,content),indent=2)+'\n',encoding='utf-8')
    print(target)

if __name__=='__main__':main()
