import json
import unittest
from pathlib import Path

from lxml import etree

from backend.transformer import Transformer


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TestConversionIntegration(unittest.TestCase):
    """Exercise the real conversion pipeline with repository samples."""

    def setUp(self):
        self.transformer = Transformer()
        self.samples = {
            'cmme': (PROJECT_ROOT / 'samples/basic/cmme/basic_example.cmme').read_text(
                encoding='utf-8'
            ),
            'mei': (PROJECT_ROOT / 'samples/basic/mei/basic_example.mei').read_text(
                encoding='utf-8'
            ),
            'json': (PROJECT_ROOT / 'samples/basic/json/basic_example.json').read_text(
                encoding='utf-8'
            ),
        }

    def convert(self, source_format, target_format):
        serialized = self.transformer.serializer.serialize(self.samples[source_format])
        result = self.transformer.transform(
            serialized,
            f'{source_format}-to-{target_format}'
        )
        return self.transformer.serializer.deserialize(result)

    def count_notes(self, result, target_format):
        if target_format == 'json':
            if isinstance(result, str):
                result = json.loads(result)
            return sum(
                len(measure.get('events', measure.get('notes', [])))
                for part in result['parts']
                for measure in part['measures']
            )

        root = etree.fromstring(result.encode('utf-8'))
        return len(root.xpath("//*[local-name()='note']"))

    def test_all_supported_paths_preserve_basic_notes(self):
        paths = [
            ('cmme', 'mei'),
            ('mei', 'cmme'),
            ('cmme', 'json'),
            ('mei', 'json'),
            ('json', 'cmme'),
            ('json', 'mei'),
        ]

        for source_format, target_format in paths:
            with self.subTest(source=source_format, target=target_format):
                result = self.convert(source_format, target_format)
                self.assertEqual(self.count_notes(result, target_format), 3)

    def test_legacy_score_staves_json_is_supported(self):
        legacy_data = {
            'metadata': {'title': 'Legacy sample', 'composer': 'Unknown'},
            'score': {
                'staves': [{
                    'name': 'Voice',
                    'measures': [{
                        'number': 1,
                        'notes': [{'pitch': 'C4', 'duration': 'quarter'}],
                    }],
                }],
            },
        }

        result = self.transformer.json_converter.json_to_cmme(legacy_data)
        root = etree.fromstring(result.encode('utf-8'))
        self.assertEqual(len(root.xpath('//note')), 1)

    def test_complex_mei_chord_inherits_parent_duration(self):
        source = (PROJECT_ROOT / 'samples/complex/mei/complex_example.mei').read_text(
            encoding='utf-8'
        )
        serialized = self.transformer.serializer.serialize(source)
        converted = self.transformer.transform(serialized, 'mei-to-cmme')
        result = self.transformer.serializer.deserialize(converted)

        root = etree.fromstring(result.encode('utf-8'))
        chord_notes = root.xpath('//chord/note')
        self.assertEqual(len(chord_notes), 2)
        self.assertTrue(all(note.get('duration') == 'quarter' for note in chord_notes))

    def test_invalid_target_is_rejected(self):
        source = {
            'metadata': {'title': 'Invalid target', 'composer': 'Unknown'},
            'parts': [{
                'name': 'Voice',
                'measures': [{
                    'number': 1,
                    'events': [{'type': 'note', 'pitch': 'C4'}],
                }],
            }],
        }
        serialized = self.transformer.serializer.serialize(source)

        with self.assertRaisesRegex(ValueError, 'failed validation'):
            self.transformer.transform(serialized, 'json-to-cmme')


if __name__ == '__main__':
    unittest.main()
