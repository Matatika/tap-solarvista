""" Test sync package """
import unittest
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch
import responses
import singer
import tap_solarvista
import tap_solarvista.tests.utils as test_utils

LOGGER = singer.get_logger()

SINGER_MESSAGES = []

def accumulate_singer_messages(message):
    """ function to collect singer library write_message in tests """
    SINGER_MESSAGES.append(message)

singer.messages.write_message = accumulate_singer_messages

MOCK_TOKEN = {
    "access_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6Ij",
    "expires_in": 3600,
    "token_type": "Bearer",
    "scope": "api email openid profile"
}

MOCK_WORKITEM_DETAIL = {
    "workItemId": "55a98839-c04f-4b95-b99c-b7e2537f8809",
    "reference": "AP0002",
    "createdOn": "2020-05-14T14:14:14.455852+00:00",
    "lastModified": "2020-05-14T14:24:35.8273218+00:00",
    "currentStage": {
        "stageType": "Working",
    },
    "isComplete": False,
    "description": "Aaron test repair",
    "properties": {
        "site": {
            "id": "GB-54778-S7",
        },
        "customer": {
            "id": "GB-4998-E5",
        },
        "equipment": {
            "id": "GB1261",
        },
        "charge": 233,
        "currency": {
            "id": "GBP",
        },
        "price-inc-tax": False,
        "duration-hours": 3,
    },
}

class TestSync(unittest.TestCase):
    """ Test class for sync package """

    def setUp(self):
        """ Setup the test objects and helpers """
        self.catalog = test_utils.discover_catalog('site')
        del SINGER_MESSAGES[:]  # prefer SINGER_MESSAGES.clear(), only available on python3

    @responses.activate  # intercept HTTP calls within this method
    def test_sync_token(self):
        """ Test basic sync requests token before requesting records """
        mock_config = {
            'account': 'mock-account-id'
        }
        mock_state = {}
        responses.add(
            responses.POST,
            "https://auth.solarvista.com/connect/token",
            json=MOCK_TOKEN,
        )
        mock_site_data = {
            'continuationToken': None,
            'rows': [{
                "rowData": {
                    "reference": "GB-83320-S7",
                    "nickname": "Hamill-Lueilwitz/High Wycombe"
                }
            }]
        }
        responses.add(
            responses.POST,
            "https://api.solarvista.com/datagateway/v3/mock-account-id"
                + "/datasources/ref/site/data/query",
            json=mock_site_data,
        )
        tap_solarvista.sync.sync_all_data(mock_config, mock_state, self.catalog)
        self.assertEqual(len(SINGER_MESSAGES), 2)
        self.assertIsInstance(SINGER_MESSAGES[0], singer.SchemaMessage)
        self.assertIsInstance(SINGER_MESSAGES[1], singer.RecordMessage)


    @responses.activate  # intercept HTTP calls within this method
    def test_sync_refresh_token(self):
        """ Test sync requests refresh token """
        mock_config = {
            'account': 'mock-account-id'
        }
        mock_state = {}
        responses.add(
            responses.POST,
            "https://auth.solarvista.com/connect/token",
            json=MOCK_TOKEN,
        )
        responses.add(
            responses.POST,
            "https://api.solarvista.com/datagateway/v3/mock-account-id"
                + "/datasources/ref/site/data/query",
            status=401
        )
        responses.add(
            responses.POST,
            "https://auth.solarvista.com/connect/token",
            json=MOCK_TOKEN,
        )
        mock_site_data = {
            'continuationToken': None,
            'rows': [{
                "rowData": {
                    "reference": "GB-83320-S7",
                    "nickname": "Hamill-Lueilwitz/High Wycombe"
                }
            }]
        }
        responses.add(
            responses.POST,
            "https://api.solarvista.com/datagateway/v3/mock-account-id"
                + "/datasources/ref/site/data/query",
            json=mock_site_data,
        )
        responses.add(
            responses.POST,
            "https://api.solarvista.com/datagateway/v3/mock-account-id"
                + "/datasources/ref/site/data/query",
            json=mock_site_data,
        )
        tap_solarvista.sync.sync_all_data(mock_config, mock_state, self.catalog)
        self.assertEqual(len(SINGER_MESSAGES), 2)
        self.assertIsInstance(SINGER_MESSAGES[0], singer.SchemaMessage)
        self.assertIsInstance(SINGER_MESSAGES[1], singer.RecordMessage)


    @responses.activate  # intercept HTTP calls within this method
    def test_sync_reuse_token(self):
        """ Test sync requests refresh token """
        mock_config = {
            'account': 'mock-account-id'
        }
        mock_state = {}
        responses.add(
            responses.POST,
            "https://auth.solarvista.com/connect/token",
            json=MOCK_TOKEN,
        )
        mock_site_data = {
            'continuationToken': None,
            'rows': [{
                "rowData": {
                    "reference": "GB-83320-S7",
                    "nickname": "Hamill-Lueilwitz/High Wycombe"
                }
            }]
        }
        responses.add(
            responses.POST,
            "https://api.solarvista.com/datagateway/v3/mock-account-id"
                + "/datasources/ref/site/data/query",
            json=mock_site_data,
        )
        tap_solarvista.sync.CONFIG.clear()
        tap_solarvista.sync.sync_all_data(mock_config, mock_state, self.catalog)
        self.assertEqual(len(responses.calls), 2)
        self.assertTrue(responses.assert_call_count("https://auth.solarvista.com/connect/token", 1))
        self.assertTrue(responses.assert_call_count("https://api.solarvista.com/datagateway/v3"
                + "/mock-account-id/datasources/ref/site/data/query", 1))
        self.assertEqual(len(SINGER_MESSAGES), 2)

        # a second call should reuse the access_token
        responses.add(
            responses.POST,
            "https://api.solarvista.com/datagateway/v3/mock-account-id"
                + "/datasources/ref/site/data/query",
            json=mock_site_data,
        )
        tap_solarvista.sync.sync_all_data(mock_config, mock_state, self.catalog)
        self.assertEqual(len(responses.calls), 3)
        self.assertTrue(responses.assert_call_count("https://auth.solarvista.com/connect/token", 1))
        self.assertTrue(responses.assert_call_count("https://api.solarvista.com/datagateway/v3"
                + "/mock-account-id/datasources/ref/site/data/query", 2))
        self.assertEqual(len(SINGER_MESSAGES), 4)
        self.assertIsInstance(SINGER_MESSAGES[0], singer.SchemaMessage)
        self.assertIsInstance(SINGER_MESSAGES[1], singer.RecordMessage)
        self.assertIsInstance(SINGER_MESSAGES[2], singer.SchemaMessage)
        self.assertIsInstance(SINGER_MESSAGES[3], singer.RecordMessage)


    @patch('tap_solarvista.sync.sync_datasource')
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

        tap_solarvista.sync.sync_all_data({}, state, self.catalog)

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


    @patch('tap_solarvista.sync.fetch_workitemdetail')
    @patch('tap_solarvista.sync.sync_datasource')
    def test_sync_workitem(self, mock_fetch_data, mock_fetch_workitemdetail):
        """ Test workitem sync returns schema and full work-item detail records """
        self.catalog = test_utils.discover_catalog('workitem')
        state = {}

        workitem_data = {
            'continuationToken': 'moredata',
            'rows': [{
                "rowData": {
                    "workItemId": "55a98839-c04f-4b95-b99c-b7e2537f8809",
                    "assignedUserId": "4f104c50-745b-4f47-86ef-826b300f5074",
                    "assignedUserName": "Bill",
                    "tags": [
                        "Revisit",
                        "Awaiting Parts"
                    ],
                }
            }]
        }

        mock_fetch_data.side_effect = [workitem_data, None]
        mock_fetch_workitemdetail.side_effect = [MOCK_WORKITEM_DETAIL, None]

        tap_solarvista.sync.sync_all_data({}, state, self.catalog)

        self.assertEqual(len(SINGER_MESSAGES), 2)
        self.assertIsInstance(SINGER_MESSAGES[0], singer.SchemaMessage)
        self.assertIsInstance(SINGER_MESSAGES[1], singer.RecordMessage)

        record_messages = list(filter(
            lambda m: isinstance(m, singer.RecordMessage), SINGER_MESSAGES))

        expected_records = [
            {'workItemId': "55a98839-c04f-4b95-b99c-b7e2537f8809",
             'assignedUserId': "4f104c50-745b-4f47-86ef-826b300f5074",
             'assignedUserName': "Bill",
             'tags': ['Revisit', 'Awaiting Parts'],
             'reference': "AP0002",
             'createdOn': "2020-05-14T14:14:14.455852+00:00",
             'lastModified': '2020-05-14T14:24:35.8273218+00:00',
             'currentStage_stageType': 'Working',
             'description': "Aaron test repair",
             'isComplete': False,
             'properties_customer_id': "GB-4998-E5",
             'properties_site_id': "GB-54778-S7",
             'properties_equipment_id': "GB1261",
             'properties_charge': 233,
             'properties_currency_id': 'GBP',
             'properties_price-inc-tax': False,
             'properties_duration-hours': 3}
        ]
        self.assertEqual(expected_records, [x.asdict()['record'] for x in record_messages])


    def test_transform_workitemdetail(self):
        """ Test workitem sync returns schema and full work-item detail records """
        result = tap_solarvista.sync.flatten_json(MOCK_WORKITEM_DETAIL)
        expected = {
            'workItemId': "55a98839-c04f-4b95-b99c-b7e2537f8809",
            'reference': "AP0002",
            'createdOn': "2020-05-14T14:14:14.455852+00:00",
            'lastModified': '2020-05-14T14:24:35.8273218+00:00',
            'currentStage_stageType': 'Working',
            'description': "Aaron test repair",
            'isComplete': False,
            'properties_customer_id': "GB-4998-E5",
            'properties_site_id': "GB-54778-S7",
            'properties_equipment_id': "GB1261",
            'properties_charge': 233,
            'properties_currency_id': 'GBP',
            'properties_price-inc-tax': False,
            'properties_duration-hours': 3,
        }
        self.assertEqual(expected, result)


    @responses.activate  # intercept HTTP calls within this method
    def test_sync_workitem_incremental(self):
        """ Test incremental workitem sync returns schema and full work-item detail records """
        self.catalog = test_utils.discover_catalog('workitem')
        mock_config = {
            'workitem_search_enabled': True,
            'start_date': "2020-05-14T14:14:14.455852+00:00"
        }
        mock_state = {}

        mock_workitem_data = {
            'continuationToken': None,
            'items': [{
                "workItemId": "55a98839-c04f-4b95-b99c-b7e2537f8809",
                "assignedUserId": "4f104c50-745b-4f47-86ef-826b300f5074",
                "assignedUserName": "Bill",
                "reference": "AP0002",
                "createdOn": "2020-05-14T14:14:14.455852+00:00",
                "lastModified": "2020-05-14T14:24:35.8273218+00:00",
                "currentStage": {
                    "stageType": "Working",
                },
                "description": "Aaron test repair",
                "isComplete": False,
                "fieldValues": {
                    "site": {
                        "id": "GB-54778-S7",
                    },
                    "customer": {
                        "id": "GB-4998-E5",
                    },
                    "equipment": {
                        "id": "GB1261",
                    },
                    "charge": 233,
                    "currency": {
                        "id": "GBP",
                    },
                    "price-inc-tax": False,
                    "duration-hours": 3,
                },
            }]
        }
        responses.add(
            responses.POST,
            "https://api.solarvista.com/workflow/v4/mock-account-id"
                + "/workItems/search",
            json=mock_workitem_data,
        )

        tap_solarvista.sync.sync_all_data(mock_config, mock_state, self.catalog)

        self.assertEqual(len(SINGER_MESSAGES), 2)
        self.assertIsInstance(SINGER_MESSAGES[0], singer.SchemaMessage)
        self.assertIsInstance(SINGER_MESSAGES[1], singer.RecordMessage)

        record_messages = list(filter(
            lambda m: isinstance(m, singer.RecordMessage), SINGER_MESSAGES))

        expected_records = [
            {'workItemId': "55a98839-c04f-4b95-b99c-b7e2537f8809",
             'assignedUserId': "4f104c50-745b-4f47-86ef-826b300f5074",
             'assignedUserName': "Bill",
             'reference': "AP0002",
             'createdOn': "2020-05-14T14:14:14.455852+00:00",
             'lastModified': '2020-05-14T14:24:35.8273218+00:00',
             'currentStage_stageType': 'Working',
             'description': "Aaron test repair",
             'isComplete': False,
             'properties_customer_id': "GB-4998-E5",
             'properties_site_id': "GB-54778-S7",
             'properties_equipment_id': "GB1261",
             'properties_charge': 233,
             'properties_currency_id': 'GBP',
             'properties_price-inc-tax': False,
             'properties_duration-hours': 3}
        ]
        self.assertEqual(expected_records, [x.asdict()['record'] for x in record_messages])


    @patch('tap_solarvista.sync.sync_datasource')
    def test_sync_site(self, mock_fetch_data):
        """ Test site sync returns all record elements """
        self.catalog = test_utils.discover_catalog('site')
        state = {}

        site_data = {
            'continuationToken': 'moredata',
            'rows': [{
                "rowData": {
                    "reference": "GB-44271-W3",
                    "nickname": "Lucky Gold Coin/Cheltenham",
                    "name": "Lucky Gold Coin Casinos plc",
                    "floor-room": "Unit 14",
                    "building": "Swift Tower",
                    "address": {
                        "addressLine1": "06 Esch Alley",
                        "addressLine2": None,
                        "city": "Cheltenham",
                        "administrativeRegion2": "Gloucestershire",
                        "administrativeRegion1": "England",
                        "country": "United Kingdom",
                        "postalCode": "GL51 0TF"
                    },
                    "customer": {
                        "Id": "GB-38884-E10",
                    },
                }
            }]
        }

        mock_fetch_data.side_effect = [site_data, None]

        tap_solarvista.sync.sync_all_data({}, state, self.catalog)

        self.assertEqual(len(SINGER_MESSAGES), 2)
        self.assertIsInstance(SINGER_MESSAGES[0], singer.SchemaMessage)
        self.assertIsInstance(SINGER_MESSAGES[1], singer.RecordMessage)

        record_messages = list(filter(
            lambda m: isinstance(m, singer.RecordMessage), SINGER_MESSAGES))

        expected_records = [
            {'reference': "GB-44271-W3",
            'nickname': "Lucky Gold Coin/Cheltenham",
            'name': "Lucky Gold Coin Casinos plc",
            'floor-room': 'Unit 14',
            'building': 'Swift Tower',
            'address_addressLine1': "06 Esch Alley",
            'address_addressLine2': None,
            'address_city': "Cheltenham",
            'address_administrativeRegion2': "Gloucestershire",
            'address_administrativeRegion1': "England",
            'address_country': "United Kingdom",
            'address_postalCode': "GL51 0TF",
            'customer_Id': "GB-38884-E10"}
        ]
        self.assertEqual(expected_records, [x.asdict()['record'] for x in record_messages])

if __name__ == '__main__':
    unittest.main()
