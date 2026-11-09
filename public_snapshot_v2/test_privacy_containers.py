"""Fabricated container probes only; no real paper, archive or private value."""
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import sys
import unittest
import warnings
import zipfile

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


SPEC = importlib.util.spec_from_file_location('privacy_policy_container_tests', Path(__file__).with_name('privacy_policy.py'))
policy = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = policy
SPEC.loader.exec_module(policy)


def archive(members):
    output = BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as package:
            for name, content in members:
                # ZipInfo's constructor normalizes Windows backslashes. Assign
                # after construction so malformed names are real input bytes.
                member = zipfile.ZipInfo('placeholder')
                member.filename = member.orig_filename = name
                member.compress_type = zipfile.ZIP_DEFLATED
                package.writestr(member, content)
    return output.getvalue()


def document(text):
    types = (b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             b'<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             b'<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
             b'</Types>')
    relationships = (b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                     b'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                     b'</Relationships>')
    body = ('<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body><w:p><w:r><w:t>' + text + '</w:t></w:r></w:p></w:body></w:document>').encode()
    return archive([('[Content_Types].xml', types), ('_rels/.rels', relationships), ('word/document.xml', body)])


def pdf(stream_text='Benign synthetic result', metadata=None, attachments=None):
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                             NameObject('/Subtype'): NameObject('/Type1'),
                             NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
    stream = DecodedStreamObject()
    escaped = stream_text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    stream.set_data(('BT /F1 12 Tf 72 720 Td (' + escaped + ') Tj ET').encode('ascii'))
    page[NameObject('/Contents')] = writer._add_object(stream.flate_encode())
    if metadata:
        writer.add_metadata(metadata)
    for name, raw in attachments or ():
        writer.add_attachment(name, raw)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


class ContainerPrivacyTests(unittest.TestCase):
    def test_docx_xml_entities_cannot_hide_known_credential(self):
        secret = 'synthetic-credential-canary'
        encoded = ''.join('&#' + str(ord(c)) + ';' for c in secret)
        raw = document(encoded)
        self.assertNotIn(secret.encode(), raw)
        with self.assertRaises(policy.PrivacyPolicyError) as caught:
            policy.audit_archive('paper/toy.docx', raw, {'credential': [secret.encode()]})
        self.assertNotIn(secret, str(caught.exception))

    def test_zip_json_unicode_escapes_cannot_hide_known_literals(self):
        for category in ('credential', 'native_response_id'):
            secret = 'synthetic-' + category + '-canary'
            encoded = ''.join('\\u' + format(ord(c), '04x') for c in secret)
            raw = archive([('nested/metadata.json', ('{"nested":{"message":"' + encoded + '"}}').encode())])
            self.assertNotIn(secret.encode(), raw)
            with self.subTest(category=category), self.assertRaises(policy.PrivacyPolicyError) as caught:
                policy.audit_archive('toy.zip', raw, {category: [secret.encode()]})
            self.assertNotIn(secret, str(caught.exception))

    def test_duplicate_zip_members_are_refused(self):
        raw = archive([('metadata.json', b'{"safe":true}'), ('metadata.json', b'{"safe":false}')])
        with self.assertRaises(policy.PrivacyPolicyError):
            policy.audit_archive('toy.zip', raw, {})

    def test_unsafe_zip_member_paths_are_refused(self):
        for name in ('../outside.json', '/absolute.json', 'C:/absolute.json', 'nested\\escape.json',
                     'nested/../escape.json', 'nested//alias.json', './alias.json', 'safe.json\0hidden.xml'):
            raw = archive([(name, b'{"safe":true}')])
            with self.subTest(name=name), self.assertRaises(policy.PrivacyPolicyError):
                policy.audit_archive('toy.zip', raw, {})

    def test_zip_member_cannot_inherit_root_file_final_output_approval(self):
        payload = json.dumps({'response': {'output_text': json.dumps({
            'provider_metadata': {'analysis': 'synthetic-private-reasoning-canary'}})}}).encode()
        raw = archive([('data/toy.json', payload)])
        with self.assertRaises(policy.PrivacyPolicyError):
            policy.audit_archive('outer.zip', raw, {},
                approved_final_output_fields={'data/toy.json': [('response', 'output_text')]})

    def test_zip_member_cannot_borrow_direct_scientific_exemptions(self):
        final_output = archive([('data/toy.jsonl', b'{"final_output":"synthetic-study-text"}\n')])
        with self.assertRaises(policy.PrivacyPolicyError):
            policy.audit_archive('outer.zip', final_output, {},
                approved_final_output_fields={'data/toy.jsonl': {('final_output',)}})
        synthetic_authorization = archive([('data/stateful_influence_cases.jsonl', b'{"packet":{"authorization":false}}\n')])
        with self.assertRaises(policy.PrivacyPolicyError):
            policy.audit_archive('outer.zip', synthetic_authorization, {})

    def test_compressed_pdf_content_cannot_hide_known_credential(self):
        secret = 'synthetic-stream-credential-canary'
        raw = pdf(secret)
        self.assertNotIn(secret.encode(), raw)
        with self.assertRaises(policy.PrivacyPolicyError) as caught:
            policy.audit_archive('paper/toy.pdf', raw, {'credential': [secret.encode()]})
        self.assertNotIn(secret, str(caught.exception))

    def test_pdf_unicode_metadata_cannot_hide_known_native_id(self):
        secret = 'synthetic-metadata-native-id-canary'
        raw = pdf(metadata={'/Subject': '\u03a9 ' + secret})
        self.assertNotIn(secret.encode(), raw)
        with self.assertRaises(policy.PrivacyPolicyError) as caught:
            policy.audit_archive('paper/toy.pdf', raw, {'native_response_id': [secret.encode()]})
        self.assertNotIn(secret, str(caught.exception))

    def test_pdf_attachment_json_escapes_cannot_hide_known_credential(self):
        secret = 'synthetic-attachment-credential-canary'
        encoded = ''.join('\\u' + format(ord(c), '04x') for c in secret)
        payload = ('{"note":"' + encoded + '"}').encode()
        raw = pdf(attachments=[('metadata.json', payload)])
        self.assertNotIn(secret.encode(), raw)
        with self.assertRaises(policy.PrivacyPolicyError) as caught:
            policy.audit_archive('paper/toy.pdf', raw, {'credential': [secret.encode()]})
        self.assertNotIn(secret, str(caught.exception))

    def test_pdf_provider_analysis_metadata_is_not_a_scientific_report(self):
        raw = pdf(metadata={'/Analysis': 'synthetic-hidden-analysis-canary'})
        with self.assertRaises(policy.PrivacyPolicyError):
            policy.audit_archive('paper/toy.pdf', raw, {})

    def test_pdf_typed_reasoning_metadata_is_not_visible_final_output(self):
        raw = pdf(metadata={'/Type': 'reasoning', '/Content': 'synthetic-hidden-envelope-canary'})
        with self.assertRaises(policy.PrivacyPolicyError):
            policy.audit_archive('paper/toy.pdf', raw, {})

    def test_xml_private_attribute_and_hidden_content_are_refused(self):
        payloads = [b'<record ResponseHeaders="synthetic-header-value"/>',
                    b'<record><reasoning_content>synthetic-hidden-notes</reasoning_content></record>']
        for payload in payloads:
            raw = archive([('metadata.xml', payload)])
            with self.subTest(payload_kind='attribute' if b'ResponseHeaders' in payload else 'element'):
                with self.assertRaises(policy.PrivacyPolicyError):
                    policy.audit_archive('toy.zip', raw, {})

    def test_xml_provider_context_cannot_hide_analysis_or_account_values(self):
        payloads = [b'<provider><analysis>synthetic-hidden-analysis</analysis></provider>',
                    b'<provider><available>12.34</available></provider>',
                    b'<provider Analysis="synthetic-hidden-analysis"/>',
                    b'<provider available="12.34"/>']
        for index, payload in enumerate(payloads):
            with self.subTest(fabricated_case=index), self.assertRaises(policy.PrivacyPolicyError):
                policy.audit_archive('toy.zip', archive([('metadata.xml', payload)]), {})

    def test_decoded_containers_reject_typed_retired_commitments_case_insensitively(self):
        retired = ('aB' * 32).encode('ascii')
        upper = retired.decode('ascii').upper()
        escaped = ''.join('\\u' + format(ord(c), '04x') for c in upper)
        json_payload = ('{"note":"' + escaped + '"}').encode()
        entities = ''.join('&#' + str(ord(c)) + ';' for c in upper)
        cases = [('toy.zip', archive([('metadata.json', json_payload)])),
                 ('paper/toy.docx', document(entities)),
                 ('paper/toy.pdf', pdf(upper)),
                 ('paper/attached.pdf', pdf(attachments=[('metadata.json', json_payload)]))]
        for index, (name, raw) in enumerate(cases):
            self.assertNotIn(upper.encode(), raw)
            with self.subTest(fabricated_container=index):
                with self.assertRaisesRegex(policy.PrivacyPolicyError, 'private_source_commitment') as caught:
                    policy.audit_archive(name, raw, {'private_source_commitment': [retired]})
                self.assertNotIn(upper, str(caught.exception))

    def test_benign_docx_and_pdf_are_accepted(self):
        policy.audit_archive('paper/toy.docx', document('Synthetic result with scientific count 17.'), {})
        policy.audit_archive('paper/toy.pdf', pdf('Synthetic result with scientific count 17.'), {})

    def test_general_auditor_dispatches_docx_and_pdf(self):
        secret = 'synthetic-container-dispatch-canary'
        values = {'credential': [secret.encode()]}
        for name, raw in [('paper/toy.docx', document(''.join('&#' + str(ord(c)) + ';' for c in secret))),
                          ('paper/toy.pdf', pdf(secret))]:
            with self.subTest(name=name), self.assertRaises(policy.PrivacyPolicyError):
                policy.audit_forbidden_values(name, raw, values)

    def test_nested_compressed_member_cannot_hide_known_secret(self):
        secret = 'synthetic-inner-container-canary'
        inner = archive([('metadata.json', json.dumps({'message': secret}).encode())])
        raw = archive([('nested/inner.zip', inner)])
        with self.assertRaises(policy.PrivacyPolicyError):
            policy.audit_archive('outer.zip', raw, {'credential': [secret.encode()]})


if __name__ == '__main__':
    unittest.main()
