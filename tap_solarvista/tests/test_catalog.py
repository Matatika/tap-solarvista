""" Test catalog package """
import unittest
import singer
from tap_solarvista import catalog

LOGGER = singer.get_logger()

class TestCatalog(unittest.TestCase):
    """ Test class for catalog package """

    def setUp(self):
        """ Setup the test objects and helpers """
        self.catalog = catalog.discover(['customer', 'site'])

    def test_catalog_none_selected(self):
        """ Test discover returns all when no datasources provided """
        local_catalog = catalog.discover(None)
        self.assertGreater(len(local_catalog.streams), 1,
                           "Expect catalog to discover when no datasources supplied")

    def test_catalog_selected(self):
        """ Test discover returns only the provided datasources """
        local_catalog = catalog.discover(['customer', 'site'])
        selected_streams = local_catalog.get_selected_streams({})

        selected_stream_ids = [s.tap_stream_id for s in selected_streams]
        self.assertEqual(sorted(selected_stream_ids),
                         ['customer_stream',
                          'site_stream'])

    def test_catalog_streamname_reserved_chars(self):
        """ Test catalog strips reserved characters that are used as downstream table names """
        local_catalog = catalog.discover(['work-item'])

        selected_streams = local_catalog.get_selected_streams({})
        stream_names = [s.stream for s in selected_streams]
        self.assertEqual(stream_names, ['workitem'],
                         "Expect stream name to be stripped of invalid chars")

        selected_streams = local_catalog.get_selected_streams({})
        stream_aliases = [s.stream_alias for s in selected_streams]
        self.assertEqual(stream_aliases, ['work-item'],
                         "Expect stream alias to be datasource name")

    def test_catalog_users_primary_key(self):
        """ Test discover users with a primary key for 'userId' """
        local_catalog = catalog.discover(['users'])
        selected_streams = local_catalog.get_selected_streams({})

        key_props = [s.key_properties[0] for s in selected_streams]
        self.assertEqual(sorted(key_props), ['userId'])

if __name__ == '__main__':
    unittest.main()
