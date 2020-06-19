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

        SINGER_MESSAGES.clear()
        tap_solarvista.sync.fetch_all_data({}, state, self.catalog)

        message_types = [type(m) for m in SINGER_MESSAGES]


        self.assertEqual(message_types,
                         [singer.SchemaMessage,
                          singer.RecordMessage])

        record_messages = list(filter(
            lambda m: isinstance(m, singer.RecordMessage), SINGER_MESSAGES))

        expected_records = [
            {'reference': "GB-83320-S7",
             'nickname': "Hamill-Lueilwitz/High Wycombe"}
        ]

        self.assertEqual(expected_records, [x.asdict()['record'] for x in record_messages])


if __name__ == '__main__':
    unittest.main()
