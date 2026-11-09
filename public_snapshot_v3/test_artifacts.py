"""Synthetic strict DOCX and PDF checks, without experimental inputs."""
import importlib
from pathlib import Path
import sys
import tempfile
import types
import unittest
import zipfile

HERE = Path(__file__).resolve().parent
PACKAGE = '_snapshot_preparation_test_package'
if PACKAGE not in sys.modules:
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(HERE)]
    sys.modules[PACKAGE] = package
a = importlib.import_module(PACKAGE + '.artifacts')


def compact(value):
    return ''.join(value.split())


class ArtifactTests(unittest.TestCase):
    def test_exact_source_text_and_one_template_footnote(self):
        self.assertEqual(a.verify_text_order(
            ['SyntheticTitle1\nSynthetic body\n1Synthetic event', 'References'],
            ['SyntheticTitle', 'Synthetic body', 'References'],
            'SyntheticTitle', ['Syntheticevent'], compact), 1)

    def test_extra_and_reordered_pdf_text_rejected(self):
        for pages in (
            ['Title1 body EXTRA 1event', 'References'],
            ['body Title1 1event', 'References'],
        ):
            with self.assertRaises(ValueError):
                a.verify_text_order(pages, ['Title', 'body', 'References'],
                                    'Title', ['event'], compact)

    def test_missing_or_duplicated_title_footnote_rejected(self):
        for page in ('Title body 1event', 'Title1 Title1 body 1event',
                     'Title1 body', 'Title1 body 1event 1event'):
            with self.assertRaises(ValueError):
                a.verify_text_order([page, 'References'], ['Title', 'body', 'References'],
                                    'Title', ['event'], compact)

    def test_nine_main_pages_or_ambiguous_references_rejected(self):
        pages = ['Title1 body 1event'] + [''] * 8 + ['References']
        with self.assertRaises(ValueError):
            a.verify_text_order(pages, ['Title', 'body', 'References'], 'Title', ['event'], compact)
        with self.assertRaises(ValueError):
            a.verify_text_order(['Title1 body 1event', 'References', 'References'],
                                ['Title', 'body', 'References', 'References'], 'Title', ['event'], compact)

    def test_docx_parts_are_exact_not_only_visible_text(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'synthetic.docx'
            expected = {'word/document.xml': b'<synthetic/>', 'word/styles.xml': b'<style/>'}
            with zipfile.ZipFile(path, 'w') as archive:
                for name, raw in expected.items():
                    archive.writestr(name, raw)
            a.compare_docx_parts(path, expected)
            changed = dict(expected, **{'word/styles.xml': b'<changed/>'})
            with self.assertRaises(ValueError):
                a.compare_docx_parts(path, changed)

    def test_missing_or_extra_docx_package_part_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'synthetic.docx'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('word/document.xml', b'<synthetic/>')
            with self.assertRaises(ValueError):
                a.compare_docx_parts(path, {'word/document.xml': b'<synthetic/>', 'missing': b'x'})
            with self.assertRaises(ValueError):
                a.compare_docx_parts(path, {})


if __name__ == '__main__':
    unittest.main()
