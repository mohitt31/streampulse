"""Offline transport tests: no requests or frozen report writes."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('sandbox', Path(__file__).resolve().parents[2] / 'scripts/sandbox_roundtrip.py')
sandbox = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sandbox)


class SandboxTransportTests(unittest.TestCase):
    def setUp(self):
        self.bundle = {'resourceType': 'Bundle', 'type': 'collection', 'entry': [
            {'fullUrl': 'urn:uuid:site', 'resource': {'resourceType': 'Location', 'id': 'site', 'name': 'Demo'}},
            {'fullUrl': 'urn:uuid:obs', 'resource': {'resourceType': 'Observation', 'id': 'obs',
             'subject': {'reference': 'urn:uuid:site'}, 'valueQuantity': {'value': 21.7, 'code': 'Cel'}}}]}

    def test_transaction_does_not_change_source_or_overwrite_ids(self):
        original = copy.deepcopy(self.bundle)
        tx = sandbox.transaction(self.bundle)
        self.assertEqual(self.bundle, original)
        self.assertEqual(tx['type'], 'transaction')
        for e in tx['entry']:
            self.assertEqual(e['request'], {'method': 'POST', 'url': e['resource']['resourceType']})
            self.assertNotIn('id', e['resource'])
            self.assertEqual(e['resource']['meta']['tag'][0]['code'], 'demo')
        self.assertEqual(tx['entry'][1]['resource']['subject'], {'reference': 'urn:uuid:site'})

    def test_missing_internal_reference_is_rejected(self):
        self.bundle['entry'].pop(0)
        with self.assertRaisesRegex(ValueError, 'Unresolved'):
            sandbox.transaction(self.bundle)

    def test_readback_allows_server_metadata_but_rejects_value_change(self):
        expected = sandbox.transaction(self.bundle)['entry'][1]['resource']
        back = copy.deepcopy(expected)
        back['id'] = 'new'
        back['meta']['versionId'] = '1'
        back['meta']['lastUpdated'] = '2026-09-30T00:00:00Z'
        back['subject']['reference'] = sandbox.BASE + '/Location/123'
        mapping = {'urn:uuid:site': 'Location/123'}
        self.assertTrue(sandbox.read_matches(expected, back, mapping))
        back['valueQuantity']['value'] += 1
        self.assertFalse(sandbox.read_matches(expected, back, mapping))

    def test_readback_rejects_wrong_reference_or_missing_demo_tag(self):
        expected = sandbox.transaction(self.bundle)['entry'][1]['resource']
        back = copy.deepcopy(expected)
        back['subject']['reference'] = 'Location/wrong'
        self.assertFalse(sandbox.read_matches(expected, back, {'urn:uuid:site': 'Location/123'}))
        back = copy.deepcopy(expected)
        back.pop('meta')
        self.assertFalse(sandbox.read_matches(expected, back, {}))
