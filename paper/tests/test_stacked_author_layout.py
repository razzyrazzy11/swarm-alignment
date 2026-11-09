"""Synthetic opt-in author presentation; no empirical validation or outputs."""
from copy import deepcopy
import hashlib
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib
from lxml import etree as E

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'paper/build.py').is_file())
PAPER=ROOT/'paper';sys.path.insert(0,str(PAPER))
import build
import figure_build as f


class StackedAuthorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'paper';self.root.mkdir()
        shutil.copy2(PAPER/'official-template.docx',self.root/'official-template.docx')
        def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
        png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',2,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\0\xff\0\0\0\xff\0'))+chunk(b'IEND',b'')
        (self.root/'figures').mkdir();(self.root/'figures/toy.png').write_bytes(png)
        source=self.root.parent/'research/toy.json';source.parent.mkdir();source.write_bytes(b'{"synthetic":true}\n')
        self.content=dict(title='Synthetic title',subtitle='With Apart Research',author='Synthetic Author',affiliation='Independent Researcher',
            abstract=' '.join(['synthetic']*150),table1=[['a','b','c']],table2=[['a','b','c','d']],
            sections=[['1. Introduction',['Synthetic body.','TABLE1','TABLE2','FIGURE1']]],references=['Synthetic reference.'],
            appendix=[['Limitations and Dual-Use / Ethical Considerations',['Synthetic limitations.']]],
            figures=[dict(id='FIGURE1',path='figures/toy.png',sha256=hashlib.sha256(png).hexdigest(),
                source_files={'research/toy.json':hashlib.sha256(source.read_bytes()).hexdigest()},width_inches=1,
                caption='Figure 1. Synthetic pixels.',alt_text='Synthetic pixels.')])

    def test_default_assembly_remains_byte_identical(self):
        with patch.object(f,'_author_layout',return_value=None):before=f.assemble(self.content,self.root/'official-template.docx')
        self.assertEqual(f.assemble(self.content,self.root/'official-template.docx'),before)

    def test_stacked_author_clones_template_properties_and_preserves_every_other_part(self):
        before=f.assemble(self.content,self.root/'official-template.docx')
        content=deepcopy(self.content);content['author_layout']='stacked'
        after=f.assemble(content,self.root/'official-template.docx')
        self.assertEqual(set(before),set(after))
        self.assertEqual([name for name in before if before[name]!=after[name]],['word/document.xml'])
        old=E.fromstring(before['word/document.xml']);new=E.fromstring(after['word/document.xml'])
        oldp=next(p for p in old.xpath('//w:p',namespaces=build.NS) if build.text(p)=='Synthetic Author | Independent Researcher')
        name=next(p for p in new.xpath('//w:p',namespaces=build.NS) if build.text(p)=='Synthetic Author')
        affiliation=name.getnext();self.assertEqual(build.text(affiliation),'Independent Researcher')
        for paragraph,bold in ((name,'1'),(affiliation,'0')):
            self.assertEqual(E.tostring(paragraph.find(build.W+'pPr')),E.tostring(oldp.find(build.W+'pPr')))
            self.assertEqual(paragraph.find(build.W+'pPr').find(build.W+'jc').get(build.W+'val'),'center')
            props=paragraph.find(build.W+'r').find(build.W+'rPr')
            self.assertEqual(props.find(build.W+'b').get(build.W+'val'),bold)
            self.assertEqual(props.find(build.W+'bCs').get(build.W+'val'),bold)
            kept=lambda rp:[E.tostring(ch) for ch in rp if ch.tag not in (build.W+'b',build.W+'bCs')]
            self.assertEqual(kept(props),kept(oldp.find(build.W+'r').find(build.W+'rPr')))
        self.assertIn('With Apart Research',build.text(new));self.assertNotIn('Synthetic Author | Independent Researcher',build.text(new))
        self.assertEqual(E.tostring(old.find(build.W+'body').find(build.W+'sectPr')),E.tostring(new.find(build.W+'body').find(build.W+'sectPr')))
        # Recombine exactly the one presentation edit and compare the entire XML.
        name.getparent().remove(affiliation);name.getparent().replace(name,deepcopy(oldp))
        self.assertEqual(E.tostring(new),E.tostring(old))

    def test_unknown_layout_missing_or_duplicate_author_fail_closed(self):
        content=deepcopy(self.content);content['author_layout']='sideways'
        with self.assertRaisesRegex(ValueError,'Unknown author layout'):f.assemble(content,self.root/'official-template.docx')
        content['author_layout']='stacked'
        doc=E.fromstring(f.assemble(self.content,self.root/'official-template.docx')['word/document.xml'])
        paragraph=next(p for p in doc.xpath('//w:p',namespaces=build.NS) if build.text(p)=='Synthetic Author | Independent Researcher')
        paragraph.addnext(deepcopy(paragraph))
        with self.assertRaisesRegex(ValueError,'unique and present'):f._author_layout(doc,content)
        for p in list(doc.xpath('//w:p',namespaces=build.NS)):
            if build.text(p)=='Synthetic Author | Independent Researcher':p.getparent().remove(p)
        with self.assertRaisesRegex(ValueError,'unique and present'):f._author_layout(doc,content)


if __name__=='__main__':unittest.main()
