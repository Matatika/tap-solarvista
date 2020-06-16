import unittest
from unittest.mock import Mock, patch
import singer
import tap_solarvista.catalog as catalog

LOGGER = singer.get_logger()

SINGER_MESSAGES = []

def accumulate_singer_messages(message):
    SINGER_MESSAGES.append(message)

singer.messages.write_message = accumulate_singer_messages

class TestCatalog(unittest.TestCase):

    def setUp(self):
        self.catalog = catalog.discover(['customer','site'])

    def test_catalog_none_selected(self):
        localCatalog = catalog.discover(None)
        self.assertGreater(len(localCatalog.streams), 1, "Expect catalog to discover when no datasources supplied")

    def test_catalog_selected(self):
        localCatalog = catalog.discover(['customer','site'])
        selected_streams = localCatalog.get_selected_streams({})

        selected_stream_ids = [m.tap_stream_id for m in selected_streams]
        self.assertEqual(selected_stream_ids,
                         ['site_stream',
                          'customer_stream'])
        
        
if __name__ == '__main__':
    unittest.main()