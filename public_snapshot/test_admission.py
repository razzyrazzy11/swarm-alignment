"""Synthetic disclosure-gate regressions; no study inputs or release export."""
from copy import deepcopy
import importlib
from pathlib import Path
import sys
import tempfile
import types
import unittest

HERE = Path(__file__).resolve().parent
PACKAGE = '_snapshot_preparation_test_package'
if PACKAGE not in sys.modules:
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(HERE)]
    sys.modules[PACKAGE] = package
a = importlib.import_module(PACKAGE + '.admission')


def objects():
    receipt = dict(
        schema_version=1, kind='private_canonical_admission_attestation_v1',
        manifest_sha256='a' * 64, canonical_commit=a.CANONICAL_COMMIT,
        authority='author_attested_private_canonical_verification',
        original_verification=dict(normal_private='PASS', optimized_private='PASS',
                                   master_ci=42620835573, master_ci_commit=a.CANONICAL_COMMIT),
        artifact_hashes={'paper/out/swarm_audit_scoping.pdf': a.CANONICAL_PDF,
                         'paper/out/swarm_audit_scoping.docx': a.CANONICAL_DOCX},
        private_original_protocol_admission=a.PRIVATE_ADMISSION,
        privacy_checks=dict(policy_version=1, reviewed_files=9, reviewed_spans=10,
                            known_credential_values_checked=3, known_credential_matches=0,
                            structured_fields_checked=True, unknown_secret_absence_claimed=False),
    )
    coordinates = [
        ('research/DEVIATIONS.md', 68, 'initial_credit_observed'),
        ('research/PILOT_RESULTS.md', 49, 'starting_credit_observed'),
        ('research/PROTOCOL.md', 51, 'initial_credit_observed'),
        ('research/REVIEW.md', 133, 'initial_credit_observed'),
        ('research/SOURCE_AUDIT.md', 66, 'initial_credit_observed'),
        ('research/SUITE_STRATEGY.md', 49, 'initial_credit_observed'),
        ('research/OLLAMA_PROTOCOL.md', 33, 'remaining_credit_observed'),
        ('research/STATEFUL_RUNBOOK.md', 73, 'provider_available_credit_observed'),
        ('research/STATEFUL_RUNBOOK.md', 73, 'provider_available_credit_observed'),
        ('research/SWARM_MONITOR_TRAINING_FEASIBILITY.md', 64, 'stated_starting_credit_allocation'),
    ]
    files = {path: dict(sha256='b' * 64, bytes=1, role='redacted') for path in a.REDACTION_PATHS}
    files.update({path: dict(sha256='c' * 64, bytes=1, role='metadata_rebound')
                  for path in a.REBINDING_PATHS})
    files.update({path: dict(sha256=value, bytes=1, role='canonical')
                  for path, value in receipt['artifact_hashes'].items()})
    manifest = dict(schema_version=1, kind=a.SCOPE, canonical_commit=a.CANONICAL_COMMIT,
                    canonical_tree=a.CANONICAL_TREE, tooling_source_commit='d' * 40,
                    tooling_tag='public-snapshot-disclosure-v1', policy=deepcopy(a.POLICY),
                    files=files, redactions=[dict(path=p, line=n, category='provider_account_credit',
                                                semantic_role=role) for p, n, role in coordinates],
                    rebindings=[dict(path=p, sha256='c' * 64, category='private_source_commitment')
                                for p in sorted(a.REBINDING_PATHS)],
                    attestation_sha256=a.attestation_digest(receipt))
    return manifest, receipt


class AdmissionTests(unittest.TestCase):
    def test_complete_explicit_disclosure_boundary(self):
        m, r = objects()
        self.assertEqual(a.validate_objects(m, r), {p: v['sha256'] for p, v in m['files'].items()})

    def test_author_claim_change_is_bound(self):
        m, r = objects()
        r['privacy_checks']['known_credential_values_checked'] = 4
        with self.assertRaisesRegex(ValueError, 'Author claims'):
            a.validate_objects(m, r)

    def test_bool_float_aliases_rejected_even_with_new_claim_digest(self):
        for field, value in [('policy_version', True), ('policy_version', 1.0),
                             ('reviewed_files', 9.0), ('known_credential_matches', False)]:
            m, r = objects()
            r['privacy_checks'][field] = value
            m['attestation_sha256'] = a.attestation_digest(r)
            with self.assertRaises(ValueError):
                a.validate_objects(m, r)
        m, r = objects()
        m['policy']['score_or_bootstrap_changes'] = 0
        with self.assertRaises(ValueError):
            a.validate_objects(m, r)

    def test_wrong_canonical_identity_rejected(self):
        for key in ('canonical_tree', 'canonical_commit'):
            m, r = objects()
            m[key] = 'e' * 40
            with self.assertRaises(ValueError):
                a.validate_objects(m, r)

    def test_no_scientific_code_or_data_redaction(self):
        for name in ('data/toy.json', 'experiments/toy.py', 'analysis/toy.py', 'paper/toy.py'):
            m, r = objects()
            m['files'][name] = dict(sha256='f' * 64, bytes=1, role='generated')
            with self.assertRaisesRegex(ValueError, 'Scientific'):
                a.validate_objects(m, r)

    def test_exact_redaction_coordinates_and_no_private_guards_in_manifest(self):
        m, r = objects()
        m['redactions'][0]['line'] += 1
        with self.assertRaises(ValueError):
            a.validate_objects(m, r)
        m, r = objects()
        m['redactions'][0]['line_sha256'] = 'f' * 64
        with self.assertRaises(ValueError):
            a.validate_objects(m, r)

    def test_all_source_metadata_targets_must_be_disclosed(self):
        m, r = objects()
        removed = m['rebindings'].pop()
        m['files'][removed['path']]['role'] = 'canonical'
        with self.assertRaises(ValueError):
            a.validate_objects(m, r)

    def test_relative_path_and_private_names(self):
        for value in ('../outside', '/absolute', 'a//b', 'a/./b', 'a\\b', 'C:secret', 'a\nb',
                      'CON', 'dir/NUL.txt', 'dir/trailing.', 'dir/trailing '):
            with self.assertRaises(ValueError):
                a.relative_name(value)
        self.assertTrue(a.forbidden_name('nested/runs-private/state.json'))
        self.assertTrue(a.forbidden_name('.env.production'))
        self.assertFalse(a.forbidden_name('.env.example'))

    def test_strict_json_keys_and_constants(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'{"a":1e999}', b'\xff'):
            with self.assertRaises(ValueError):
                a.decode_json(raw)

    def test_case_aliased_files_are_rejected_before_reading(self):
        m, r = objects()
        name = 'paper/out/swarm_audit_scoping.pdf'
        m['files'][name.upper()] = deepcopy(m['files'][name])
        with self.assertRaisesRegex(ValueError, 'Case-aliased'):
            a.validate_objects(m, r)

    def test_inventory_never_hides_nested_git_or_caches(self):
        for relative in ('nested/.git/hidden', '__pycache__/hidden', 'nested/cache.pyc'):
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                path = root / relative
                path.parent.mkdir(parents=True)
                path.write_bytes(b'synthetic')
                with self.assertRaises(ValueError):
                    a.inventory(root)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / '.git').write_text('gitdir: outside', encoding='utf-8')
            with self.assertRaises(ValueError):
                a.inventory(root)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / '.git').mkdir()
            (root / '.git/local-state').write_bytes(b'synthetic')
            (root / 'shown').write_bytes(b'synthetic')
            self.assertEqual(a.inventory(root), {'shown'})


if __name__ == '__main__':
    unittest.main()
