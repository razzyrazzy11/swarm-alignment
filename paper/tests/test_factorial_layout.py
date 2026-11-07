"""Exercise table layout with synthetic content and the retained official template."""
from pathlib import Path
import unittest
import zipfile

from lxml import etree as E

from paper import build


class FactorialLayoutTests(unittest.TestCase):
    def content(self, columns, source=None):
        result = {
            'title': 'Synthetic layout check', 'subtitle': 'Illustrative only',
            'author': 'Test Author', 'affiliation': 'Test affiliation',
            'abstract': ' '.join(['synthetic'] * 150),
            'table1': [['Column ' + str(i) for i in range(columns)],
                       ['cell ' + str(i) for i in range(columns - 1)] + ['LAST-COLUMN-SENTINEL']],
            'table2': [['A', 'B', 'C', 'D']],
            'sections': [['1. Introduction', ['TABLE1']]],
            'references': ['Synthetic reference.'],
            'appendix': [['Appendix', ['Synthetic limitations.']]],
        }
        if source is not None:
            result['table2_source'] = source
        return result

    def check_layout(self, columns, source, widths):
        template = Path(build.__file__).parent / 'official-template.docx'
        parts = build.assemble(self.content(columns, source), template)
        doc = E.fromstring(parts['word/document.xml'])
        tables = doc.find(build.W + 'body').findall(build.W + 'tbl')
        table = tables[1]  # First table is the retained title/abstract container.
        grid = table.find(build.W + 'tblGrid').findall(build.W + 'gridCol')
        self.assertEqual([int(c.get(build.W + 'w')) for c in grid], widths)
        self.assertEqual(sum(widths), 9360)
        for row in table.findall(build.W + 'tr'):
            self.assertEqual(len(row.findall(build.W + 'tc')), columns)
        self.assertEqual(build.text(table.findall(build.W + 'tr')[1].findall(build.W + 'tc')[-1]),
                         'LAST-COLUMN-SENTINEL')
        # The layout branch must preserve all package parts and page geometry.
        with zipfile.ZipFile(template) as original:
            self.assertEqual(set(parts), set(original.namelist()))
            self.assertEqual([name for name in original.namelist()
                              if parts[name] != original.read(name)], ['word/document.xml'])
            old = E.fromstring(original.read('word/document.xml'))
            self.assertEqual(E.tostring(doc.find(build.W + 'body').find(build.W + 'sectPr')),
                             E.tostring(old.find(build.W + 'body').find(build.W + 'sectPr')))

    def test_factorial_four_columns_preserve_fourth_cell(self):
        self.check_layout(4, 'factorial_reporting', [2200, 1700, 1700, 3760])

    def test_legacy_three_columns_unchanged(self):
        for source in (None, 'factorial_study', 'legacy'):
            with self.subTest(source=source):
                self.check_layout(3, source, [2200, 3400, 3760])

    def test_column_count_mismatch_is_rejected(self):
        template = Path(build.__file__).parent / 'official-template.docx'
        for source, columns in [('factorial_reporting', 3), ('factorial_reporting', 5),
                                (None, 4), ('factorial_study', 4)]:
            with self.subTest(source=source, columns=columns):
                with self.assertRaisesRegex(ValueError, 'table1 must have'):
                    build.assemble(self.content(columns, source), template)


if __name__ == '__main__':
    unittest.main()
