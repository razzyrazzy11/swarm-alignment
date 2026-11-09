"""Pin legacy artifact tests without weakening the actual completed-paper gate."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

TESTS=Path(__file__).resolve().parent
sys.path.insert(0,str(TESTS))
import test_integrity as fixtures


class HistoricalFixtureTests(unittest.TestCase):
    def test_pinned_source_and_all_original_bytes(self):
        root=fixtures.verified_historical_fixture()
        manifest=json.loads((root/'manifest.json').read_bytes())
        self.assertEqual(manifest['source_commit'],'166da1cd1d5b725455b03fb9a47aaf1e2b8dabe5')
        self.assertEqual(set(manifest['files_sha256']),fixtures.HISTORICAL_FILES)
        for name,expected in manifest['files_sha256'].items():
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),expected)

    def test_legacy_setup_does_not_copy_live_content_or_outputs(self):
        original_copy=shutil.copy2
        original_tree=shutil.copytree
        live=fixtures.PAPER
        def copy(source,target,*args,**kwargs):
            self.assertNotEqual(Path(source),live/'content.json')
            return original_copy(source,target,*args,**kwargs)
        def tree(source,target,*args,**kwargs):
            self.assertNotEqual(Path(source),live/'out')
            return original_tree(source,target,*args,**kwargs)
        case=fixtures.IntegrityTests('test_current_package')
        try:
            with patch.object(shutil,'copy2',side_effect=copy),patch.object(shutil,'copytree',side_effect=tree):
                case.setUp()
            content=case.source()
            self.assertEqual(content['table2_source'],'factorial_reporting')
            self.assertNotIn('ledger_registration',content)
            self.assertNotIn('figures',content)
            self.assertEqual((case.root/'content.json').read_bytes(),(fixtures.HISTORICAL_FIXTURE/'content.json').read_bytes())
        finally:
            case.doCleanups()

    def test_missing_or_modified_fixture_fails_closed(self):
        for change in ('missing','bytes','manifest'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)/'fixture'
                shutil.copytree(fixtures.HISTORICAL_FIXTURE,root)
                if change=='missing':
                    (root/'out/swarm_audit_scoping.pdf').unlink()
                elif change=='bytes':
                    with (root/'content.json').open('ab') as out:out.write(b' ')
                else:
                    manifest=json.loads((root/'manifest.json').read_bytes())
                    manifest['files_sha256']['content.json']='0'*64
                    (root/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'fixture.*hash differs'):
                    fixtures.verified_historical_fixture(root)


if __name__=='__main__':unittest.main()
