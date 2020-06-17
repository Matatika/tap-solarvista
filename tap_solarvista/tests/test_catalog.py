import unittest
from unittest.mock import Mock, patch
import singer
from tap_solarvista import catalog

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

        selected_stream_ids = [s.tap_stream_id for s in selected_streams]
        self.assertEqual(selected_stream_ids,
                         ['site_stream',
                          'customer_stream'])
        
    def test_catalog_streamname_reserved_chars(self):
        localCatalog = catalog.discover(['work-item'])
        
        selected_streams = localCatalog.get_selected_streams({})
        stream_names = [s.stream for s in selected_streams]
        self.assertEqual(stream_names, ['workitem'], "Expect stream name to be stripped of invalid chars")

        selected_streams = localCatalog.get_selected_streams({})
        stream_aliases = [s.stream_alias for s in selected_streams]
        self.assertEqual(stream_aliases, ['work-item'], "Expect stream alias to be datasource name")
        
if __name__ == '__main__':
    unittest.main()