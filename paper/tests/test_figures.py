"""Toy PNG/PDF fixtures only; never authors or renders the actual manuscript."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import unittest
import zipfile
import zlib

PAPER=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PAPER))
import build
import figure_build as f
import verify as v
import test_integrity as fixtures
from lxml import etree as E


def toy_png(width=2,height=1):
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    raw=(b'\0'+b'\xff\0\0'*width)*height
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')


def toy_pdf(path,paint=True,pages=1):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject,NameObject,NumberObject,DecodedStreamObject
    writer=PdfWriter();page=writer.add_blank_page(width=612,height=792)
    image=DecodedStreamObject();image.set_data(b'\xff\0\0\0\xff\0')
    image.update({NameObject('/Type'):NameObject('/XObject'),NameObject('/Subtype'):NameObject('/Image'),
        NameObject('/Width'):NumberObject(2),NameObject('/Height'):NumberObject(1),
        NameObject('/ColorSpace'):NameObject('/DeviceRGB'),NameObject('/BitsPerComponent'):NumberObject(8)})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/XObject'):DictionaryObject({NameObject('/ImToy'):writer._add_object(image)})})
    stream=DecodedStreamObject();stream.set_data(b'q 100 0 0 50 0 0 cm /ImToy Do Q' if paint else b'')
    page[NameObject('/Contents')]=writer._add_object(stream)
    for _ in range(pages-1):writer.add_blank_page(width=612,height=792)
    writer.write(path)
    return v.PdfReader(path)


class FigureTests(unittest.TestCase):
    def test_complete_ledger_tables_and_png_use_opt_in_adapter(self):
        from test_ledger_layout import LedgerLayoutTests
        content=LedgerLayoutTests().content()
        content['ledger_registration']='swarm-ledger-complete-v1-main'
        content['figures']=deepcopy(self.content['figures'])
        content['sections'][0][1].append('FIGURE2')
        parts=f.assemble(content,self.root/'official-template.docx')
        doc=E.fromstring(parts['word/document.xml'])
        self.assertIn('TWO-LAST',build.text(doc))
        self.assertIn('THREE-LAST',build.text(doc))
        self.assertNotIn('unused',build.text(doc))
        self.assertEqual(len(doc.xpath('//*[local-name()="drawing"]')),1)
        self.assertEqual(len([n for n in parts if n.startswith('word/media/swarm-ledger-')]),1)
        with zipfile.ZipFile(self.root/'official-template.docx') as original:
            for name in original.namelist():
                if name not in ('word/document.xml','word/_rels/document.xml.rels','[Content_Types].xml'):
                    self.assertEqual(parts[name],original.read(name),name)

    def setUp(self):
        fixture=fixtures.IntegrityTests(methodName='test_current_package');fixture.setUp()
        self.addCleanup(fixture.doCleanups);self.root=fixture.root
        shutil.copy2(PAPER/'figure_build.py',self.root/'figure_build.py')
        (self.root/'figures').mkdir();self.png=toy_png();(self.root/'figures/toy.png').write_bytes(self.png)
        source=self.root.parent/'research/toy-figure-source.json';source.write_text('{"fixture":"toy, not research findings"}')
        self.content=fixture.source()
        self.content['figures']=[dict(id='FIGURE2',path='figures/toy.png',sha256=hashlib.sha256(self.png).hexdigest(),
            source_files={'research/toy-figure-source.json':v.sha(source)},width_inches=6.0,
            caption='Figure 2. Synthetic unit-test pixels; not empirical research.',alt_text='Two toy colored pixels for package tests.')]
        self.content['sections'][0][1].append('FIGURE2')

    def built(self):
        parts=f.assemble(self.content,self.root/'official-template.docx')
        (self.root/'content.json').write_text(json.dumps(self.content),encoding='utf-8')
        self.write(parts)
        (self.root/'out/build-check.json').write_text(json.dumps(v.build_manifest(self.root,self.content)),encoding='utf-8')
        return parts

    def write(self,parts):
        with zipfile.ZipFile(self.root/'out/swarm_audit_scoping.docx','w') as z:
            for name,data in parts.items():z.writestr(name,data)

    def test_owned_parts_original_furniture_and_byte_identical_legacy(self):
        legacy_content=deepcopy(self.content);legacy_content.pop('figures');legacy_content['sections'][0][1].remove('FIGURE2')
        with zipfile.ZipFile(PAPER/'out/swarm_audit_scoping.docx') as z:
            original_output={n:z.read(n) for n in z.namelist()}
        self.assertEqual(build.assemble(legacy_content,self.root/'official-template.docx'),original_output)
        parts=self.built()
        with zipfile.ZipFile(self.root/'official-template.docx') as z:
            original={n:z.read(n) for n in z.namelist()}
        for name,data in original.items():
            if name not in ('word/document.xml','word/_rels/document.xml.rels','[Content_Types].xml'):
                self.assertEqual(parts[name],data,name)
        before=E.fromstring(original['word/document.xml']).find(build.W+'body').find(build.W+'sectPr')
        after=E.fromstring(parts['word/document.xml']).find(build.W+'body').find(build.W+'sectPr')
        self.assertEqual(E.tostring(before),E.tostring(after))
        paragraphs=v.check_docx(self.root,self.content)
        self.assertEqual(paragraphs.count(self.content['figures'][0]['caption']),1)
        manifest=v.build_manifest(self.root,self.content)
        self.assertEqual(manifest['builder_sha256'],v.builder_hash(PAPER))
        self.assertIn('figure_builder_sha256',manifest)
        self.assertEqual(len(manifest['added_package_parts']),1)

    def test_png_and_source_hash_path_size_and_registry_guards(self):
        for change in (dict(path='../toy.png'),dict(path='figures/../../secret.png'),dict(sha256='0'*64),
                       dict(width_inches=6.6),dict(width_inches=1e-20),dict(width_inches=True),dict(source_files={'research/toy-figure-source.json':'0'*64}),
                       dict(source_files={'../research/toy-figure-source.json':'0'*64})):
            content=deepcopy(self.content);content['figures'][0].update(change)
            with self.assertRaises(ValueError):f.assemble(content,self.root/'official-template.docx')
        (self.root/'figures/toy.png').unlink()
        with self.assertRaises(ValueError):f.assemble(self.content,self.root/'official-template.docx')

    def test_aspect_ratio_and_optimized_hash_guard(self):
        tall=toy_png(1,2);(self.root/'figures/toy.png').write_bytes(tall)
        self.content['figures'][0]['sha256']=hashlib.sha256(tall).hexdigest()
        with self.assertRaisesRegex(ValueError,'aspect height'):f.assemble(self.content,self.root/'official-template.docx')
        self.content['figures'][0]['sha256']='0'*64
        path=self.root/'content.json';path.write_text(json.dumps(self.content),encoding='utf-8')
        program='import sys,json;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import figure_build as f;f.assemble(json.load(open(sys.argv[2])),Path(sys.argv[3]))'
        result=subprocess.run([sys.executable,'-O','-c',program,str(PAPER),str(path),str(self.root/'official-template.docx')],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0);self.assertIn('Figure PNG hash mismatch',result.stderr)

    def test_duplicate_and_unconsumed_marker_rejected(self):
        for duplicate in (True,False):
            content=deepcopy(self.content)
            if duplicate:content['figures'].append(deepcopy(content['figures'][0]))
            else:content['sections'][0][1].remove('FIGURE2')
            with self.assertRaises(ValueError):f.assemble(content,self.root/'official-template.docx')
        corrupt=bytearray(self.png);corrupt[-5]^=1
        with self.assertRaises(ValueError):f.png_size(bytes(corrupt))

    def test_missing_tampered_media_relationship_styles_footnotes_and_section_fail(self):
        base=self.built();image=next(n for n in base if n.startswith('word/media/swarm-ledger-'))
        variants=[]
        parts=dict(base);parts.pop(image);variants.append(parts)
        parts=dict(base);parts[image]+=b'corrupt';variants.append(parts)
        parts=dict(base);rels=E.fromstring(parts['word/_rels/document.xml.rels'])
        rels[-1].set('TargetMode','External');rels[-1].set('Target','https://example.invalid/figure.png')
        parts['word/_rels/document.xml.rels']=E.tostring(rels);variants.append(parts)
        for name in ('word/styles.xml','word/footnotes.xml'):
            parts=dict(base);parts[name]+=b' ';variants.append(parts)
        parts=dict(base);parts['word/footer99.xml']=b'<footer/>';variants.append(parts)
        parts=dict(base);doc=E.fromstring(parts['word/document.xml'])
        doc.find(build.W+'body').find(build.W+'sectPr').set('tampered','1')
        parts['word/document.xml']=E.tostring(doc);variants.append(parts)
        for parts in variants:
            self.write(parts)
            with self.assertRaises(ValueError):v.check_docx(self.root,self.content)

    def test_pdf_unused_image_does_not_establish_presence(self):
        path=self.root/'out/toy.pdf'
        reader=toy_pdf(path,paint=False)
        self.assertEqual(v.painted_image_count(reader),[0])
        with self.assertRaisesRegex(ValueError,'missing painted'):v.figure_pdf_evidence(self.root,self.content,reader,path)

    def test_all_page_inspection_must_match_pdf_and_source_images(self):
        path=self.root/'out/toy.pdf';reader=toy_pdf(path,pages=2)
        self.assertEqual(v.painted_image_count(reader),[1,0])
        with self.assertRaisesRegex(ValueError,'inspection record required'):v.figure_pdf_evidence(self.root,self.content,reader,path)
        review=dict(schema_version=1,pdf_sha256=v.sha(path),figure_sha256={'FIGURE2':self.content['figures'][0]['sha256']},
                    rendered_pages=[1,2],inspected_all_pages=True,reviewer='toy unit fixture, not an actual paper review',reviewed_at='2000-01-01T00:00:00Z')
        review_path=self.root/'out/figure-review.json';review_path.write_text(json.dumps(review))
        self.assertEqual(v.figure_pdf_evidence(self.root,self.content,reader,path)['painted_images_by_page'],[1,0])
        for change in (dict(rendered_pages=[1]),dict(pdf_sha256='0'*64),dict(figure_sha256={'FIGURE2':'0'*64})):
            review_path.write_text(json.dumps(dict(review,**change)))
            with self.assertRaises(ValueError):v.figure_pdf_evidence(self.root,self.content,reader,path)


if __name__=='__main__':unittest.main()
