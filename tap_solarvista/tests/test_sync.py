""" Test sync package """
import unittest
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch
import singer
import tap_solarvista
import tap_solarvista.tests.utils as test_utils

LOGGER = singer.get_logger()

SINGER_MESSAGES = []

def accumulate_singer_messages(message):
    """ function to collect singer library write_message in tests """
    SINGER_MESSAGES.append(message)

singer.messages.write_message = accumulate_singer_messages

class TestSync(unittest.TestCase):
    """ Test class for sync package """

    def setUp(self):
        """ Setup the test objects and helpers """
        self.catalog = test_utils.discover_catalog('site')
        del SINGER_MESSAGES[:]  # prefer SINGER_MESSAGES.clear(), only available on python3

    @patch('tap_solarvista.sync.fetch_data')
    def test_sync_basic(self, mock_fetch):
        """ Test basic sync returns schema and records """
        state = {}

        site_data = {
            'continuationToken': 'moredata',
            'rows': [{
                "rowData": {
                    "reference": "GB-83320-S7",
                    "nickname": "Hamill-Lueilwitz/High Wycombe"
                }
            }]
        }

        mock_fetch.side_effect = [site_data, None]

        tap_solarvista.sync.fetch_all_data({}, state, self.catalog)

        self.assertEqual(len(SINGER_MESSAGES), 2)
        self.assertIsInstance(SINGER_MESSAGES[0], singer.SchemaMessage)
        self.assertIsInstance(SINGER_MESSAGES[1], singer.RecordMessage)

        record_messages = list(filter(
            lambda m: isinstance(m, singer.RecordMessage), SINGER_MESSAGES))

        expected_records = [
            {'reference': "GB-83320-S7",
             'nickname': "Hamill-Lueilwitz/High Wycombe"}
        ]

        self.assertEqual(expected_records, [x.asdict()['record'] for x in record_messages])


if __name__ == '__main__':
    unittest.main()
