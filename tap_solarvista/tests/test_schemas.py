import unittest
from tap_solarvista import schemas

class TestSchemas(unittest.TestCase):

    def test_datasource_from_stream(self):
        self.assertEqual('customers', schemas.extract_datasource('customers_stream'))
        self.assertEqual('work-items', schemas.extract_datasource('work-items_stream'))
        self.assertEqual('value_with_underscore', schemas.extract_datasource('value_with_underscore_stream'))


if __name__ == '__main__':
    unittest.main()