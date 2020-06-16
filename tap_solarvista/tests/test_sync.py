import unittest
from unittest.mock import Mock, patch
import singer
import tap_solarvista

try:
    import tap_solarvista.tests.utils as test_utils
except ImportError:
    import utils as test_utils
    
LOGGER = singer.get_logger()

SINGER_MESSAGES = []

def accumulate_singer_messages(message):
    SINGER_MESSAGES.append(message)

singer.messages.write_message = accumulate_singer_messages

class TestSync(unittest.TestCase):

    def setUp(self):
        self.catalog = test_utils.discover_catalog('site')

    @patch('tap_solarvista.sync.fetch_data')
    def test_sync_basic(self, mock_fetch):
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

        global SINGER_MESSAGES
        SINGER_MESSAGES.clear()
        tap_solarvista.sync.fetch_all_data({}, state, self.catalog)

        message_types = [type(m) for m in SINGER_MESSAGES]

        
        self.assertEqual(message_types,
                         [singer.SchemaMessage,
                          singer.RecordMessage])

        record_messages = list(filter(lambda m: isinstance(m, singer.RecordMessage), SINGER_MESSAGES))

        expected_records = [
            {'reference': "GB-83320-S7",
             'nickname': "Hamill-Lueilwitz/High Wycombe"}
        ]

        self.assertEqual(expected_records, [x.asdict()['record'] for x in record_messages])
        
        
if __name__ == '__main__':
    unittest.main()