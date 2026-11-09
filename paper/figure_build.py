"""Opt-in scientific PNGs over the unchanged official-template text builder.

No rendering or empirical figure generation occurs on import or assembly.
"""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import struct
import zipfile
import zlib

from lxml import etree as E
import build as legacy

ROOT=Path(__file__).resolve().parent
W=legacy.W
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
REL='http://schemas.openxmlformats.org/package/2006/relationships'
CT='http://schemas.openxmlformats.org/package/2006/content-types'
WP='http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
PIC='http://schemas.openxmlformats.org/drawingml/2006/picture'
IMAGE_REL=R+'/image'
KEYS={'id','path','sha256','source_files','width_inches','caption','alt_text'}
require=legacy.require


def sha(value):return hashlib.sha256(value).hexdigest()


def _hash(value):return type(value) is str and re.fullmatch(r'[0-9a-f]{64}',value) is not None


def _relative(root,value,prefixes):
    require(type(value) is str and '\\' not in value and ':' not in value,'Unsafe figure/source path')
    path=PurePosixPath(value)
    require(not path.is_absolute() and path.parts and all(v not in ('','.','..') for v in path.parts)
            and str(path)==value and path.parts[0] in prefixes,'Unsafe figure/source path')
    resolved=(Path(root)/value).resolve()
    require(resolved.is_relative_to(Path(root).resolve()),'Figure/source path escaped root')
    require(resolved.is_file(),'Missing figure/source file: '+value)
    return resolved


def png_size(data):
    """Validate bounded noninterlaced 8-bit PNG structure/deflate without Pillow."""
    require(type(data) is bytes and len(data)<=15_000_000 and data[:8]==b'\x89PNG\r\n\x1a\n','Invalid/oversize PNG')
    offset=8;chunks=[];compressed=[];ended=False
    while offset<len(data):
        require(offset+12<=len(data),'Truncated PNG chunk')
        length=struct.unpack('>I',data[offset:offset+4])[0]
        kind=data[offset+4:offset+8];end=offset+8+length
        require(end+4<=len(data),'Truncated PNG payload')
        payload=data[offset+8:end];crc=struct.unpack('>I',data[end:end+4])[0]
        require(zlib.crc32(kind+payload)&0xffffffff==crc,'PNG CRC mismatch')
        chunks.append((kind,payload))
        if kind==b'IDAT':compressed.append(payload)
        if kind==b'IEND':
            require(length==0 and end+4==len(data),'PNG IEND/trailing data invalid')
            ended=True;break
        offset=end+4
    require(ended and chunks and chunks[0][0]==b'IHDR' and len(chunks[0][1])==13
            and sum(k==b'IHDR' for k,_ in chunks)==1 and compressed,'PNG structure invalid')
    width,height,depth,color,compression,filter_,interlace=struct.unpack('>IIBBBBB',chunks[0][1])
    channels={0:1,2:3,4:2,6:4}
    require(0<width<=12000 and 0<height<=12000 and depth==8 and color in channels
            and compression==filter_==interlace==0,'Unsupported PNG dimensions/encoding')
    rowbytes=width*channels[color];expected=(rowbytes+1)*height
    require(expected<=64_000_000,'Decoded PNG exceeds size cap')
    try:
        decoder=zlib.decompressobj();raw=decoder.decompress(b''.join(compressed),expected+1)
    except zlib.error as exc:raise ValueError('Invalid PNG deflate') from exc
    require(len(raw)==expected and decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,'PNG decoded length invalid')
    require(all(raw[i*(rowbytes+1)] in range(5) for i in range(height)),'Invalid PNG row filter')
    return width,height


def registry(content,root):
    values=content.get('figures')
    require(type(values) is list and values,'PNG registry must be a nonempty list')
    seen=set();out=[];markers=[v for _,ps in content['sections']+content.get('appendix',[]) for v in ps]
    for value in values:
        require(type(value) is dict and set(value)==KEYS,'Figure registry field allowlist')
        ident=value['id'];require(type(ident) is str and re.fullmatch(r'FIGURE[1-9]\d*',ident) is not None and ident not in seen,'Invalid/duplicate figure ID')
        seen.add(ident);require(markers.count(ident)==1,'Figure marker must occur exactly once in sections')
        image=_relative(root,value['path'],{'figures'})
        require(image.suffix=='.png' and _hash(value['sha256']),'Figure must be SHA-bound PNG')
        data=image.read_bytes();require(sha(data)==value['sha256'],'Figure PNG hash mismatch')
        width,height=png_size(data)
        sources=value['source_files'];require(type(sources) is dict and sources,'Figure public source commitments required')
        for name,expected in sources.items():
            source=_relative(Path(root).parent,name,{'research','data'})
            require(source.suffix in ('.json','.jsonl','.csv','.tsv','.md') and _hash(expected),'Invalid public figure source commitment')
            require(sha(source.read_bytes())==expected,'Figure source hash mismatch: '+name)
        inches=value['width_inches']
        require(type(inches) in (float,int) and math.isfinite(inches) and 0<inches<=6.5,'Figure width must be at most 6.5 inches')
        height_inches=inches*height/width
        require(height_inches<=8.5,'Figure aspect height exceeds page region')
        require(round(inches*914400)>0 and round(height_inches*914400)>0,'Figure dimensions round to zero')
        require(type(value['caption']) is str and value['caption'].startswith('Figure '+ident[6:]+'.') and len(value['caption'])<=10000,'Figure caption missing/number mismatch')
        require(type(value['alt_text']) is str and 0<len(value['alt_text'])<=1024,'Figure alternative text required')
        out.append(dict(value,pixel_width=width,pixel_height=height,width_emu=round(inches*914400),
            height_emu=round(height_inches*914400),image_part='word/media/swarm-ledger-'+value['sha256']+'.png',data=data))
    return out


def _sub(parent,namespace,localname,**attrs):
    return E.SubElement(parent,'{'+namespace+'}'+localname,{str(k):str(v) for k,v in attrs.items()})


def _drawing(paragraph,item,rid,number):
    legacy.replace(paragraph,'')
    props=paragraph.find(W+'pPr')
    if props.find(W+'keepNext') is None:props.insert(sum(ch.tag==W+'pStyle' for ch in props),E.Element(W+'keepNext'))
    run=E.SubElement(paragraph,W+'r');drawing=E.SubElement(run,W+'drawing',nsmap={'wp':WP,'a':A,'pic':PIC,'r':R})
    inline=_sub(drawing,WP,'inline',distT=0,distB=0,distL=0,distR=0)
    _sub(inline,WP,'extent',cx=item['width_emu'],cy=item['height_emu'])
    _sub(inline,WP,'effectExtent',l=0,t=0,r=0,b=0)
    _sub(inline,WP,'docPr',id=number,name=item['id'],descr=item['alt_text'])
    locks=_sub(inline,WP,'cNvGraphicFramePr');_sub(locks,A,'graphicFrameLocks',noChangeAspect=1)
    graphic=_sub(inline,A,'graphic');gd=_sub(graphic,A,'graphicData',uri=PIC)
    picture=_sub(gd,PIC,'pic');nv=_sub(picture,PIC,'nvPicPr')
    _sub(nv,PIC,'cNvPr',id=0,name=Path(item['path']).name);_sub(nv,PIC,'cNvPicPr')
    fill=_sub(picture,PIC,'blipFill');blip=_sub(fill,A,'blip');blip.set('{'+R+'}embed',rid)
    stretch=_sub(fill,A,'stretch');_sub(stretch,A,'fillRect')
    shape=_sub(picture,PIC,'spPr');transform=_sub(shape,A,'xfrm')
    _sub(transform,A,'off',x=0,y=0);_sub(transform,A,'ext',cx=item['width_emu'],cy=item['height_emu'])
    geometry=_sub(shape,A,'prstGeom',prst='rect');_sub(geometry,A,'avLst')


def _author_layout(doc,content):
    """Opt-in author presentation over the template-derived paragraph only."""
    if 'author_layout' not in content:return
    require(content['author_layout']=='stacked','Unknown author layout')
    combined=content['author']+' | '+content['affiliation']
    matches=[p for p in doc.xpath('//w:p',namespaces=legacy.NS) if legacy.text(p)==combined]
    require(len(matches)==1,'Stacked author paragraph must be unique and present')
    original=matches[0]
    props=original.find(W+'pPr')
    require(props is not None and props.find(W+'jc') is not None and props.find(W+'jc').get(W+'val')=='center',
            'Stacked author requires original centered template paragraph')
    paragraphs=[]
    for value,bold in ((content['author'],True),(content['affiliation'],False)):
        paragraph=deepcopy(original);legacy.replace(paragraph,value)
        run=paragraph.find(W+'r');rprops=run.find(W+'rPr')
        if rprops is None:rprops=E.Element(W+'rPr');run.insert(0,rprops)
        for tag in ('b','bCs'):
            for previous in rprops.findall(W+tag):rprops.remove(previous)
        # b/bCs follow rFonts in CT_RPr; every existing font/size/property stays.
        position=sum(child.tag in (W+'rStyle',W+'rFonts') for child in rprops)
        for offset,tag in enumerate(('b','bCs')):
            flag=E.Element(W+tag);flag.set(W+'val','1' if bold else '0');rprops.insert(position+offset,flag)
        paragraphs.append(paragraph)
    original.getparent().replace(original,paragraphs[0]);paragraphs[0].addnext(paragraphs[1])


def assemble(content,template):
    template=Path(template);items=registry(content,template.parent)
    edited=deepcopy(content)
    identities={item['id'] for item in items}
    sentinels={name:'__SWARM_PNG_SLOT_'+name+'__' for name in identities}
    edited['sections']=[[name,[sentinels.get(v,v) for v in ps]] for name,ps in edited['sections']]
    edited['appendix']=[[name,[sentinels.get(v,v) for v in ps]] for name,ps in edited.get('appendix',[])]
    if content.get('ledger_registration'):
        from ledger_layout import assemble as ledger_assemble
        parts=ledger_assemble(edited,template)
    else:
        parts=legacy.assemble(edited,template)
    doc=E.fromstring(parts['word/document.xml']);section=E.tostring(doc.find(W+'body').find(W+'sectPr'))
    _author_layout(doc,content)
    relname='word/_rels/document.xml.rels';rels=E.fromstring(parts[relname]);old_rels=[E.tostring(v) for v in rels]
    used={v.get('Id') for v in rels};numbers=[int(v) for v in doc.xpath('//*[local-name()="docPr"]/@id')]
    start=max(numbers,default=0)+1
    for index,item in enumerate(items):
        ident=item['id'];rid='rIdSwarmFigure'+str(index+1)
        require(rid not in used,'Owned image relationship ID collision');used.add(rid)
        matches=[p for p in doc.xpath('//w:p',namespaces=legacy.NS) if legacy.text(p)==sentinels[ident]]
        require(len(matches)==1,'Figure slot not unique')
        paragraph=matches[0];caption=deepcopy(paragraph);legacy.replace(caption,item['caption'])
        _drawing(paragraph,item,rid,start+index);paragraph.addnext(caption)
        parts[item['image_part']]=item['data']
        _sub(rels,REL,'Relationship',Id=rid,Type=IMAGE_REL,Target=item['image_part'].removeprefix('word/'))
    require([E.tostring(v) for v in list(rels)[:len(old_rels)]]==old_rels,'Original relationship semantics changed')
    parts[relname]=E.tostring(rels,xml_declaration=True,encoding='UTF-8',standalone=True)
    types=E.fromstring(parts['[Content_Types].xml'])
    png=[v for v in types if v.tag=='{'+CT+'}Default' and v.get('Extension','').lower()=='png']
    require(len(png)<=1 and all(v.get('ContentType')=='image/png' for v in png),'Existing PNG content type invalid')
    if not png:
        _sub(types,CT,'Default',Extension='png',ContentType='image/png')
        parts['[Content_Types].xml']=E.tostring(types,xml_declaration=True,encoding='UTF-8',standalone=True)
    require(E.tostring(doc.find(W+'body').find(W+'sectPr'))==section,'Figure changed original section geometry')
    parts['word/document.xml']=E.tostring(doc,xml_declaration=True,encoding='UTF-8',standalone=True)
    package_delta(parts,template,items)
    return parts


def package_delta(parts,template,items=None):
    with zipfile.ZipFile(template) as z:original={name:z.read(name) for name in z.namelist()}
    added=sorted(set(parts)-set(original));removed=set(original)-set(parts)
    modified=sorted(name for name in original if name in parts and original[name]!=parts[name])
    require(not removed,'Original package part removed')
    require(set(modified)<={'word/document.xml','word/_rels/document.xml.rels','[Content_Types].xml'},'Preserved template part modified')
    if items is not None:require(set(added)=={v['image_part'] for v in items},'Unregistered/orphan package parts')
    return dict(changed_package_parts=modified,added_package_parts=added)


def figure_manifest(content,root):
    items=registry(content,root)
    return [{k:v for k,v in item.items() if k!='data'}|dict(relationship_id='rIdSwarmFigure'+str(i+1)) for i,item in enumerate(items)]


def main():
    content=json.loads((ROOT/'content.json').read_text(encoding='utf-8'))
    parts=assemble(content,ROOT/'official-template.docx')
    out=ROOT/'out';out.mkdir(exist_ok=True)
    with zipfile.ZipFile(out/'swarm_audit_scoping.docx','w',zipfile.ZIP_DEFLATED) as z:
        for name,data in parts.items():z.writestr(name,data)
    from verify import build_manifest
    (out/'build-check.json').write_text(json.dumps(build_manifest(ROOT,content),indent=2)+'\n',encoding='utf-8')
    print(out/'swarm_audit_scoping.docx')


if __name__=='__main__':main()
