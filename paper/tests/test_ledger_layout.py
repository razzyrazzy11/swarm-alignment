"""Synthetic complete-ledger layout only; no empirical inputs or artifacts."""
from copy import deepcopy
from pathlib import Path
import unittest
import zipfile
from lxml import etree as E
from paper import build, ledger_layout as layout


class LedgerLayoutTests(unittest.TestCase):
    def content(self):
        return dict(title='Synthetic ledger layout', subtitle='Test only', author='Test author',
                    affiliation='Test affiliation', abstract=' '.join(['synthetic'] * 150),
                    table2_source='swarm_ledger_complete',
                    table1=[['ONE-A', 'ONE-B', 'ONE-C'], ['ONE-D', 'ONE-E', 'ONE-F']],
                    table2=[['TWO-A', 'TWO-B', 'TWO-C'], ['TWO-D', 'TWO-E', 'TWO-LAST']],
                    table3=[['THREE-A', 'THREE-B', 'THREE-C', 'THREE-D'],
                            ['THREE-E', 'THREE-F', 'THREE-G', 'THREE-LAST']],
                    table2_caption='Table 2. Synthetic second table.',
                    table3_caption='Table 3. Synthetic third table.',
                    sections=[['1. Introduction', ['Before.', 'TABLE1', 'TABLE2', 'Between.', 'TABLE3', 'After.']]],
                    references=['Synthetic reference.'], appendix=[['Appendix', ['Synthetic limitations.']]])

    def test_all_cells_template_parts_and_input_retained(self):
        content = self.content()
        before = deepcopy(content)
        template = Path(build.__file__).parent / 'official-template.docx'
        parts = layout.assemble(content, template)
        self.assertEqual(content, before)
        doc = E.fromstring(parts['word/document.xml'])
        body = doc.find(build.W + 'body')
        tables = body.findall(build.W + 'tbl')[1:]
        self.assertEqual(len(tables), 3)
        for key, table in zip(('table1', 'table2', 'table3'), tables):
            actual = [[build.text(c) for c in row.findall(build.W + 'tc')]
                      for row in table.findall(build.W + 'tr')]
            self.assertEqual(actual, content[key])
            grid = [int(c.get(build.W + 'w')) for c in table.find(build.W + 'tblGrid')]
            self.assertEqual(sum(grid), 9360)
            self.assertEqual(len(grid), len(content[key][0]))
            if key in layout.WIDTHS:
                self.assertEqual(grid, list(layout.WIDTHS[key]))
        text = build.text(doc)
        self.assertNotIn('unused', text)
        self.assertNotIn('__SWARM_LEDGER_', text)
        self.assertLess(text.index('Between.'), text.index('Table 3.'))
        self.assertLess(text.index('THREE-LAST'), text.index('After.'))
        with zipfile.ZipFile(template) as source:
            self.assertEqual(set(parts), set(source.namelist()))
            self.assertEqual([name for name in source.namelist() if parts[name] != source.read(name)],
                             ['word/document.xml'])
            old = E.fromstring(source.read('word/document.xml'))
            self.assertEqual(E.tostring(body.find(build.W + 'sectPr')),
                             E.tostring(old.find(build.W + 'body').find(build.W + 'sectPr')))
            self.assertEqual(set(doc.xpath('//w:rFonts/@w:ascii', namespaces=build.NS)),
                             set(old.xpath('//w:rFonts/@w:ascii', namespaces=build.NS)))

    def test_bad_shapes_empty_cells_and_missing_markers_rejected(self):
        template = Path(build.__file__).parent / 'official-template.docx'
        for key, columns in (('table1', 3), ('table2', 3), ('table3', 4)):
            for rows in ([], [['x'] * (columns + 1)], [['x'] * columns, ['x']], [[''] * columns]):
                c = self.content()
                c[key] = rows
                with self.subTest(key=key, rows=rows), self.assertRaises(ValueError):
                    layout.assemble(c, template)
        for marker in ('TABLE1', 'TABLE2', 'TABLE3'):
            c = self.content()
            c['sections'][0][1].remove(marker)
            with self.subTest(marker=marker), self.assertRaises(ValueError):
                layout.assemble(c, template)

    def test_duplicate_markers_sentinel_collision_and_wrong_source_rejected(self):
        template = Path(build.__file__).parent / 'official-template.docx'
        for mutate in (lambda c: c['sections'][0][1].append('TABLE2'),
                       lambda c: c.update(title=layout.SLOTS['table2']),
                       lambda c: c.update(table2_source='factorial_reporting')):
            c = self.content()
            mutate(c)
            with self.assertRaises(ValueError):
                layout.assemble(c, template)


if __name__ == '__main__':
    unittest.main()
