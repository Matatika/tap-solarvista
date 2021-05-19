""" Test sync package """
import unittest
try:
    from unittest.mock import patch
except ImportError:
    #from mock import patch
    pass
import json
from datetime import datetime
import dateutil.relativedelta
import dateutil.parser
import responses
import singer
import tap_solarvista
import tap_solarvista.tests.utils as test_utils
from tap_solarvista import catalog

LOGGER = singer.get_logger()

SINGER_MESSAGES = []
def accumulate_singer_messages(message):
    """ function to collect singer library write_message in tests """
    SINGER_MESSAGES.append(message)
singer.messages.write_message = accumulate_singer_messages

SINGER_METRICS = []
def accumulate_singer_metrics(_logger, point):
    """ function to collect singer library metrics in tests """
    SINGER_METRICS.append(point)
singer.metrics.log = accumulate_singer_metrics


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
    "isCompleted": False,
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
        del SINGER_METRICS[:]
        tap_solarvista.sync.CONFIG = {}
        tap_solarvista.sync.STATE = {}
        responses.reset()

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
        self.assertEqual(len(SINGER_MESSAGES), 3)
        self.assertIsInstance(SINGER_MESSAGES[0], singer.SchemaMessage)
        self.assertIsInstance(SINGER_MESSAGES[1], singer.RecordMessage)
        self.assertIsInstance(SINGER_MESSAGES[2], singer.StateMessage)


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
        self.assertEqual(len(SINGER_MESSAGES), 3)
        self.assertIsInstance(SINGER_MESSAGES[0], singer.SchemaMessage)
        self.assertIsInstance(SINGER_MESSAGES[1], singer.RecordMessage)
        self.assertIsInstance(SINGER_MESSAGES[2], singer.StateMessage)


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
        self.assertEqual(len(SINGER_MESSAGES), 3)

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
        self.assertEqual(len(SINGER_MESSAGES), 6)
        self.assertIsInstance(SINGER_MESSAGES[0], singer.SchemaMessage)
        self.assertIsInstance(SINGER_MESSAGES[1], singer.RecordMessage)
        self.assertIsInstance(SINGER_MESSAGES[2], singer.StateMessage)
        self.assertIsInstance(SINGER_MESSAGES[3], singer.SchemaMessage)
        self.assertIsInstance(SINGER_MESSAGES[4], singer.RecordMessage)
        self.assertIsInstance(SINGER_MESSAGES[5], singer.StateMessage)


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

        self.assertEqual(len(SINGER_MESSAGES), 3)
        self.assertIsInstance(SINGER_MESSAGES[0], singer.SchemaMessage)
        self.assertIsInstance(SINGER_MESSAGES[1], singer.RecordMessage)
        self.assertIsInstance(SINGER_MESSAGES[2], singer.StateMessage)

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
        mock_config = {
            'workitem_detail_enabled': True
        }
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

        tap_solarvista.sync.sync_all_data(mock_config, state, self.catalog)

        self.assertEqual(len(SINGER_MESSAGES), 3)
        self.assertIsInstance(SINGER_MESSAGES[0], singer.SchemaMessage)
        self.assertIsInstance(SINGER_MESSAGES[1], singer.RecordMessage)
        self.assertIsInstance(SINGER_MESSAGES[2], singer.StateMessage)

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
             'isCompleted': False,
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
            'isCompleted': False,
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
            'account': 'mock-account-id',
            'personal_access_token': "mock-token", # disables get_access_token call
            'workitem_detail_enabled': None,
            'start_date': "2020-05-14T14:14:14.455852+00:00"
        }
        mock_state = {}

        mock_workitem_data = {
            'items': [{
                "workItemId": "55a98839-c04f-4b95-b99c-b7e2537f8809",
                "assignedUserId": "4f104c50-745b-4f47-86ef-826b300f5074",
                "assignedUserName": "Bill",
                "reference": "AP0002",
                "createdOn": "2020-05-14T14:14:14.455852+00:00",
                "lastModified": "mock-last-modified-state",
                "currentStage": {
                    "stageType": "Working",
                },
                "description": "Aaron test repair",
                "isCompleted": False,
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

        self.assertEqual(len(responses.calls), 1, "Expecting 1 call to search")
        self.assertEqual(responses.calls[0].request.url,
                         "https://api.solarvista.com/workflow/v4/mock-account-id/workItems/search")
        request_body = json.loads(responses.calls[0].request.body)
        self.assertEqual(request_body["lastModifiedAfter"], "2020-05-14T14:14:14.455852+00:00")
        self.assertEqual(request_body["orderBy"], "lastModified")
        self.assertEqual(request_body["orderByDirection"], "ascending")

        self.assertEqual(len(SINGER_MESSAGES), 3)
        self.assertIsInstance(SINGER_MESSAGES[0], singer.SchemaMessage)
        self.assertIsInstance(SINGER_MESSAGES[1], singer.RecordMessage)
        self.assertIsInstance(SINGER_MESSAGES[2], singer.StateMessage)

        record_messages = list(filter(
            lambda m: isinstance(m, singer.RecordMessage), SINGER_MESSAGES))

        expected_records = [
            {'workItemId': "55a98839-c04f-4b95-b99c-b7e2537f8809",
             'assignedUserId': "4f104c50-745b-4f47-86ef-826b300f5074",
             'assignedUserName': "Bill",
             'reference': "AP0002",
             'createdOn': "2020-05-14T14:14:14.455852+00:00",
             'lastModified': 'mock-last-modified-state',
             'currentStage_stageType': 'Working',
             'description': "Aaron test repair",
             'isCompleted': False,
             'properties_customer_id': "GB-4998-E5",
             'properties_site_id': "GB-54778-S7",
             'properties_equipment_id': "GB1261",
             'properties_charge': 233,
             'properties_currency_id': 'GBP',
             'properties_price-inc-tax': False,
             'properties_duration-hours': 3}
        ]
        self.assertEqual(expected_records, [x.asdict()['record'] for x in record_messages])

        state_messages = list(filter(
            lambda m: isinstance(m, singer.StateMessage), SINGER_MESSAGES))
        expected_states = [
            {'workitem_stream': 'mock-last-modified-state'}
        ]
        self.assertEqual(expected_states, [x.asdict()['value'] for x in state_messages])


    @responses.activate  # intercept HTTP calls within this method
    def test_sync_workitem_properties_camel_case(self):
        """ Test workitem sync returns all properties where they include camel case """
        self.catalog = test_utils.discover_catalog('workitem')
        mock_config = {
            'account': 'mock-account-id',
            'personal_access_token': "mock-token", # disables get_access_token call
            'workitem_detail_enabled': None,
            'start_date': "2020-05-14T14:14:14.455852+00:00"
        }
        mock_state = {}

        mock_workitem_data = {
            'items': [
                {
                    "workItemId": "bc3071a2-0ddf-4e4c-819b-9bec8f968570",
                    "reference": "AP0001",
                    "lastModified": "mock-last-modified-state",
                    "fieldValues": {
                        "site": {
                            "id": "GB-54778-S7",
                        },
                        "customer": {
                            "id": "GB-4998-E5",
                        },
                        "territories": {
                            "id": "TER001",
                            "title": "Hertfordshire"
                        },
                    },
                },
                {
                    "workItemId": "55a98839-c04f-4b95-b99c-b7e2537f8809",
                    "reference": "AP0002",
                    "lastModified": "mock-last-modified-state",
                    "fieldValues": {
                        "site": {
                            "id": "GB-54778-S7",
                        },
                        "customer": {
                            "id": "GB-4998-E5",
                        },
                        "territories": {
                            "Id": "TER023",
                            "Title": "Newcastle & Teeside"
                        },
                    },
                },
            ]
        }
        responses.add(
            responses.POST,
            "https://api.solarvista.com/workflow/v4/mock-account-id"
                + "/workItems/search",
            json=mock_workitem_data,
        )

        tap_solarvista.sync.sync_all_data(mock_config, mock_state, self.catalog)

        self.assertEqual(len(responses.calls), 1, "Expecting 1 call to search")
        self.assertEqual(responses.calls[0].request.url,
                         "https://api.solarvista.com/workflow/v4/mock-account-id/workItems/search")
        request_body = json.loads(responses.calls[0].request.body)
        self.assertEqual(request_body["lastModifiedAfter"], "2020-05-14T14:14:14.455852+00:00")
        self.assertEqual(request_body["orderBy"], "lastModified")
        self.assertEqual(request_body["orderByDirection"], "ascending")

        self.assertEqual(len(SINGER_MESSAGES), 4)
        self.assertIsInstance(SINGER_MESSAGES[0], singer.SchemaMessage)
        self.assertIsInstance(SINGER_MESSAGES[1], singer.RecordMessage)
        self.assertIsInstance(SINGER_MESSAGES[2], singer.RecordMessage)
        self.assertIsInstance(SINGER_MESSAGES[3], singer.StateMessage)

        record_messages = list(filter(
            lambda m: isinstance(m, singer.RecordMessage), SINGER_MESSAGES))

        expected_records = [
            {'workItemId': "bc3071a2-0ddf-4e4c-819b-9bec8f968570",
             'reference': "AP0001",
             'lastModified': 'mock-last-modified-state',
             'properties_site_id': "GB-54778-S7",
             'properties_customer_id': "GB-4998-E5",
             'properties_territories_id': "TER001",
             'properties_territories_title': "Hertfordshire",
            },
            {'workItemId': "55a98839-c04f-4b95-b99c-b7e2537f8809",
             'reference': "AP0002",
             'lastModified': 'mock-last-modified-state',
             'properties_site_id': "GB-54778-S7",
             'properties_customer_id': "GB-4998-E5",
             'properties_territories_id': "TER023",
             'properties_territories_title': "Newcastle & Teeside",
            },
        ]
        self.assertEqual(expected_records, [x.asdict()['record'] for x in record_messages])


    @responses.activate  # intercept HTTP calls within this method
    def test_sync_workitem_history(self):
        """ Test sync history of work-item """
        self.catalog = catalog.discover(['work-item', 'work-item-history'])
        mock_config = {
            'account': 'mock-account-id',
            'personal_access_token': "mock-token", # disables get_access_token call
            'workitem_detail_enabled': None,
            'start_date': "2020-05-14T14:14:14.455852+00:00"
        }
        mock_state = {}

        mock_workitem_data = {
            'items': [{
                "workItemId": "mock-workitem-id",
                "lastModified": "2020-12-01T12:26:21.1250844+00:00"
            }]
        }
        responses.add(
            responses.POST,
            "https://api.solarvista.com/workflow/v4/mock-account-id"
                + "/workItems/search",
            json=mock_workitem_data,
        )
        mock_workitem_history_data = {
            "workItemId": "mock-workitem-id",
            "workflowId": "74f6d038-a676-48dd-ac3a-a052907d9570",
            "stages": [
                {
                    "stageDisplayName": "Unassigned",
                    "stageType": "Unassigned"
                },
                {
                    "assignedUser": {
                        "displayName": "Mock User",
                        "email": "user@mock.com",
                        "userId": "6521aa9b-b9a2-4254-b85a-4b523d0f312c"
                    },
                    "stageDisplayName": "Assigned",
                    "stageType": "Assigned",
                    "transition": {
                        "fromStageType": "Unassigned",
                        "processOrder": 1,
                        "receivedAt": "2020-12-01T15:28:21.6370267+00:00",
                        "status": "submitted",
                        "toStageType": "Assigned",
                        "transitionedAt": "2020-12-01T15:28:21.5350844+00:00",
                        "transitionedBy": {
                            "displayName": "A Nother",
                            "email": "another@mock.com",
                            "userId": "9119e52d-95d9-4757-9657-99ed383f6bc5"
                        },
                        "transitionId": "6adc63f9-f860-4d9d-bbd5-628bf456fc8f",
                        "violatesStageExclusivity": False
                    }
                }
            ]
        }
        responses.add(
            responses.GET,
            "https://api.solarvista.com/workflow/v4/mock-account-id"
                + "/workItems/id/mock-workitem-id/history",
            json=mock_workitem_history_data,
        )

        tap_solarvista.sync.sync_all_data(mock_config, mock_state, self.catalog)
        self.assertEqual(len(responses.calls), 2,
                         "Expecting 2 calls one to search another to history")

        self.assertEqual(len(SINGER_MESSAGES), 7)
        self.assertIsInstance(SINGER_MESSAGES[0], singer.SchemaMessage)
        self.assertIsInstance(SINGER_MESSAGES[1], singer.SchemaMessage)
        self.assertIsInstance(SINGER_MESSAGES[2], singer.RecordMessage)
        self.assertIsInstance(SINGER_MESSAGES[3], singer.RecordMessage)
        self.assertIsInstance(SINGER_MESSAGES[4], singer.StateMessage)
        self.assertIsInstance(SINGER_MESSAGES[5], singer.RecordMessage)
        self.assertIsInstance(SINGER_MESSAGES[6], singer.StateMessage)

        schema_messages = list(filter(
            lambda m: isinstance(m, singer.SchemaMessage), SINGER_MESSAGES))
        self.assertEqual(sorted(['workitem_stream', 'workitemhistory_stream']),
                            sorted([x.asdict()['stream'] for x in schema_messages]))

        record_messages = list(filter(
            lambda m: isinstance(m, singer.RecordMessage), SINGER_MESSAGES))

        expected_records = [
            {'workItemHistoryId': "mock-workitem-id_0",
                'workItemId': "mock-workitem-id",
                'workflowId': "74f6d038-a676-48dd-ac3a-a052907d9570",
                'stage_stageDisplayName': "Unassigned",
                'stage_stageType': "Unassigned",
                'lastModified': "2020-12-01T12:26:21.1250844+00:00",
            },
            {'workItemHistoryId': "mock-workitem-id_1",
                'workItemId': "mock-workitem-id",
                'workflowId': "74f6d038-a676-48dd-ac3a-a052907d9570",
                'stage_assignedUser_displayName': "Mock User",
                'stage_assignedUser_email': "user@mock.com",
                'stage_assignedUser_userId': "6521aa9b-b9a2-4254-b85a-4b523d0f312c",
                'stage_stageDisplayName': "Assigned",
                'stage_stageType': "Assigned",
                'stage_transition_fromStageType': "Unassigned",
                'stage_transition_processOrder': 1,
                'stage_transition_receivedAt': "2020-12-01T15:28:21.6370267+00:00",
                'stage_transition_status': "submitted",
                'stage_transition_toStageType': "Assigned",
                'stage_transition_transitionedAt': "2020-12-01T15:28:21.5350844+00:00",
                'stage_transition_transitionedBy_displayName': "A Nother",
                'stage_transition_transitionedBy_email': "another@mock.com",
                'stage_transition_transitionedBy_userId': "9119e52d-95d9-4757-9657-99ed383f6bc5",
                'stage_transition_transitionId': "6adc63f9-f860-4d9d-bbd5-628bf456fc8f",
                'stage_transition_violatesStageExclusivity': False,
                'lastModified': "2020-12-01T15:28:21.5350844+00:00",
            },
            {
                'workItemId': "mock-workitem-id",
                'lastModified': "2020-12-01T12:26:21.1250844+00:00"
            }
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
                        "id": "GB-38884-E10",
                    },
                }
            }]
        }

        mock_fetch_data.side_effect = [site_data, None]

        tap_solarvista.sync.sync_all_data({}, state, self.catalog)

        self.assertEqual(len(SINGER_MESSAGES), 3)
        self.assertIsInstance(SINGER_MESSAGES[0], singer.SchemaMessage)
        self.assertIsInstance(SINGER_MESSAGES[1], singer.RecordMessage)
        self.assertIsInstance(SINGER_MESSAGES[2], singer.StateMessage)

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
            'customer_id': "GB-38884-E10"}
        ]
        self.assertEqual(expected_records, [x.asdict()['record'] for x in record_messages])

    @patch('tap_solarvista.sync.sync_datasource')
    def test_sync_project(self, mock_fetch_data):
        """ Test projects sync returns all record elements """
        self.catalog = test_utils.discover_catalog('project')
        state = {}

        project_data = {
            'continuationToken': 'moredata',
            'rows': [{
                "lastModified": "2021-02-24T08:30:26+00:00",
                "rowData": {
                    "reference": "75521249",
                    "project-type": "Repair",
                    "workcenter": None,
                    "createdon": "2021-02-09T11:35:00Z",
                    "responseduedate": None,
                    "fixduedate": "2021-02-10T19:37:00Z",
                    "appliedresponsesla": None,
                    "appliedfixsla": 24.0,
                    "closedon": None,
                    "customer": {
                        "Id": "2386264880",
                    },
                    "phonenumber": "01142 682933",
                    "revenue-expected": None,
                    "costs-expected": None,
                    "working-time-expected": None,
                    "travel-time-expected": None,
                    "progress-percent": None
                }
            }]
        }

        mock_fetch_data.side_effect = [project_data, None]

        tap_solarvista.sync.sync_all_data({}, state, self.catalog)

        self.assertEqual(len(SINGER_MESSAGES), 3)
        self.assertIsInstance(SINGER_MESSAGES[0], singer.SchemaMessage)
        self.assertIsInstance(SINGER_MESSAGES[1], singer.RecordMessage)
        self.assertIsInstance(SINGER_MESSAGES[2], singer.StateMessage)

        record_messages = list(filter(
            lambda m: isinstance(m, singer.RecordMessage), SINGER_MESSAGES))

        expected_records = [
            {'reference': "75521249",
            'project-type': "Repair",
            'workcenter': None,
            'createdon': "2021-02-09T11:35:00Z",
            'responseduedate': None,
            'fixduedate': "2021-02-10T19:37:00Z",
            'appliedresponsesla': None,
            'appliedfixsla': 24.0,
            'closedon': None,
            'customer_id': "2386264880",
            'phonenumber': "01142 682933",
            'revenue-expected': None,
            'costs-expected': None,
            'working-time-expected': None,
            'travel-time-expected': None,
            'progress-percent': None,
            'lastModified': "2021-02-24T08:30:26+00:00",
            }
        ]
        self.assertEqual(expected_records, [x.asdict()['record'] for x in record_messages])

    @patch('tap_solarvista.sync.sync_datasource')
    def test_sync_metrics(self, mock_fetch_data):
        """ Test sync outputs the correct metrics for number of records """
        self.catalog = test_utils.discover_catalog('site')
        state = {}

        mock_data = {
            'rows': [
                {
                    "rowData": {
                        "reference": "mock-record-1"
                    }
                },
                {
                    "rowData": {
                        "reference": "mock-record-2"
                    }
                }
            ]
        }

        mock_fetch_data.side_effect = [mock_data, None]

        tap_solarvista.sync.sync_all_data({}, state, self.catalog)
        self.assertEqual(len(SINGER_MESSAGES), 4)
        self.assertIsInstance(SINGER_MESSAGES[0], singer.SchemaMessage)
        self.assertIsInstance(SINGER_MESSAGES[1], singer.RecordMessage)
        self.assertIsInstance(SINGER_MESSAGES[2], singer.RecordMessage)
        self.assertIsInstance(SINGER_MESSAGES[3], singer.StateMessage)
        self.assertEqual(len(SINGER_METRICS), 1)
        metric_message = SINGER_METRICS[0]
        self.assertIsInstance(metric_message, singer.metrics.Point)
        self.assertEqual(2, metric_message.value)

    @responses.activate  # intercept HTTP calls within this method
    def test_sync_user_appointment(self):
        """ Test sync user appointments """
        self.catalog = catalog.discover(['users', 'appointment'])
        mock_config = {
            'account': 'mock-account-id',
            'personal_access_token': "mock-token", # disables get_access_token call
            'start_date': "2020-05-14T14:14:14.455852+00:00"
        }
        mock_state = {}
        mock_user_data = {
            'rows': [
                {
                    "rowData": {
                        "userId": "mock-user-id"
                    }
                },
                {
                    "rowData": {
                        "userId": "mock-user-id2"
                    }
                }
            ]
        }
        responses.add(
            responses.POST,
            "https://api.solarvista.com/datagateway/v3/mock-account-id"
                + "/datasources/ref/users/data/query",
            json=mock_user_data,
        )
        responses.add(
            responses.POST,
            "https://api.solarvista.com/datagateway/v3/mock-account-id"
                + "/datasources/ref/users/data/query",
            json=mock_user_data,
        )
        mock_user_appointment_data = {
            "appointments": [
                {
                    "appointmentId": "b0ef95ef-7347-4e57-af3c-12ae8373e1c0",
                    "displayColour": 4288988160,
                    "end": "2021-02-26T17:30:00+00:00",
                    "icon": "bell",
                    "label": "Leave/Holiday PM only",
                    "showAsHint": "foreground",
                    "start": "2021-02-26T12:45:00+00:00",
                    "userId": "mock-user-id3",
                    "workExclusivity": "cannotOverlap",
                    "properties": {}
                }
            ]
        }

        responses.add(
            responses.POST,
            "https://api.solarvista.com/calendar/v2/mock-account-id"
                + "/appointments/search/users",
            json=mock_user_appointment_data,
        )

        tap_solarvista.sync.sync_all_data(mock_config, mock_state, self.catalog)
        self.assertEqual(len(responses.calls), 3,
                         "Expecting 3 calls 2 to users and 1 to appointments")
        appointments_response = next((call for call in responses.calls
                    if call.request.url == "https://api.solarvista.com/calendar/v2/mock-account-id"
                         + "/appointments/search/users"), None)
        self.assertEqual(appointments_response.request.url,
                         "https://api.solarvista.com/calendar/v2/mock-account-id"
                         + "/appointments/search/users")
        request_body = json.loads(appointments_response.request.body)

        one_year_past = datetime.now() - dateutil.relativedelta.relativedelta(years=1)
        one_year_future = datetime.now() + dateutil.relativedelta.relativedelta(years=1)
        from_query = dateutil.parser.isoparse(request_body["from"])
        to_query = dateutil.parser.isoparse(request_body["to"])

        self.assertEqual(from_query.replace(second=0, microsecond=0),
            one_year_past.replace(second=0, microsecond=0))
        self.assertEqual(to_query.replace(second=0, microsecond=0),
            one_year_future.replace(second=0, microsecond=0))
        self.assertEqual(request_body["includeUnassigned"], True)
        self.assertEqual(request_body["userIds"], ["mock-user-id", "mock-user-id2"])

        self.assertEqual(len(SINGER_MESSAGES), 7)
        schema_messages = list(filter(
            lambda m: isinstance(m, singer.SchemaMessage), SINGER_MESSAGES))
        self.assertEqual(sorted(['users_stream', 'appointment_stream']),
                            sorted([x.asdict()['stream'] for x in schema_messages]))

        record_messages = list(filter(
            lambda m: isinstance(m, singer.RecordMessage), SINGER_MESSAGES))
        record_messages = sorted(record_messages, key=lambda k: k.asdict()['record']['userId'])
        expected_records = [
            {'userId': "mock-user-id"},
            {'userId': "mock-user-id2"},
            {
                'appointmentId': "b0ef95ef-7347-4e57-af3c-12ae8373e1c0",
                'start': "2021-02-26T12:45:00+00:00",
                'end': "2021-02-26T17:30:00+00:00",
                'label': "Leave/Holiday PM only",
                'userId': "mock-user-id3",
                'displayColour': 4288988160,
                'icon': 'bell',
                'showAsHint': 'foreground',
                'workExclusivity': 'cannotOverlap',
            },
        ]
        self.assertEqual(expected_records, [x.asdict()['record'] for x in record_messages])

    @patch('tap_solarvista.sync.sync_datasource')
    def test_sync_skill(self, mock_fetch):
        """ Test sync skill """

        state = {}

        skill_data = {
            'rows': [{
                "rowData": {
                    "reference": 1,
                    "name": "Reactive",
                    "description": None,
                    "users": [
                        {
                        "id": "f0a5a5f0",
                        "title": "Firstname Lastname",
                        "subtitle": "Firstname.Lastname@city-holdings.co.uk"
                        }
                    ]
                }
            }]
        }

        mock_fetch.side_effect = [skill_data, None]

        tap_solarvista.sync.sync_all_data({}, state, self.catalog)

        self.assertEqual(len(SINGER_MESSAGES), 3)
        self.assertIsInstance(SINGER_MESSAGES[0], singer.SchemaMessage)
        self.assertIsInstance(SINGER_MESSAGES[1], singer.RecordMessage)
        self.assertIsInstance(SINGER_MESSAGES[2], singer.StateMessage)

        record_messages = list(filter(
            lambda m: isinstance(m, singer.RecordMessage), SINGER_MESSAGES))

        expected_records = [{
            "reference": 1,
            "name": "Reactive",
            "description": None,
            "users": [
                {
                "id": "f0a5a5f0",
                "title": "Firstname Lastname",
                "subtitle": "Firstname.Lastname@city-holdings.co.uk"
                }
            ]
        }]

        self.assertEqual(expected_records, [x.asdict()['record'] for x in record_messages])


    def test_transform_activity(self):
        """ Test transform of activity """

        activity_data = [
            {
                "actvivityId": "1",
                "contextProperties": {
                    "stageType": "TravellingFrom",
                    "ref": "56967",
                    "visitId": "cf3b5e1d-a582-4a52-ac26-f72233c44c40"
                },
                "createdBy": "f12a4565-4dd4-45bb-9189-dfb603e9b938",
                "createdOn": "2021-05-10T16:24:03.949878Z",
                "data": {
                "linkedWorkOrder": "77369110",
                "internalComments": "a comment"
                }
            }
        ]

        result = tap_solarvista.sync.transform_activity_to_look_like_rowdata(activity_data)

        expected_records = {'rows': [{ "rowData": {
                "actvivityId": "1",
                "contextProperties": {
                    "stageType": "TravellingFrom",
                    "ref": "56967",
                    "visitId": "cf3b5e1d-a582-4a52-ac26-f72233c44c40"
                },
                "createdBy": "f12a4565-4dd4-45bb-9189-dfb603e9b938",
                "createdOn": "2021-05-10T16:24:03.949878Z",
                "data": {
                    "linkedWorkOrder": "77369110",
                    "internalComments": "a comment"
                }
        }}]}

        self.assertEqual(expected_records, result)

    @responses.activate
    def test_sync_activity(self):
        """ Test sync activity """

        self.catalog = catalog.discover(['work-item', 'activity'])

        mock_state = {}

        mock_config = {
            'account': 'mock-account-id',
            'personal_access_token': "mock-token", # disables get_access_token call
            'workitem_detail_enabled': None,
            'start_date': "2020-05-14T14:14:14.455852+00:00"
        }

        mock_workitem_data = {
            'items': [{
                "workItemId": "cf3b5e1d-a582-4a52-ac26-f72233c44c40",
                "lastModified": "2020-12-01T12:26:21.1250844+00:00"
            }]
        }
        responses.add(
            responses.POST,
            "https://api.solarvista.com/workflow/v4/mock-account-id"
                + "/workItems/search",
            json=mock_workitem_data,
        )

        mock_activity_data = [
            {
                "actvivityId": "1",
                "contextProperties": {
                    "stageType": "TravellingFrom",
                    "ref": "56967",
                    "visitId": "cf3b5e1d-a582-4a52-ac26-f72233c44c40"
                },
                "createdBy": "f12a4565-4dd4-45bb-9189-dfb603e9b938",
                "createdOn": "2021-05-10T16:24:03.949878Z",
                "data": {
                "linkedWorkOrder": "77369110",
                "internalComments": "a comment"
                }
            }
        ]

        responses.add(
            responses.GET,
            "https://api.solarvista.com/activity/v2/mock-account-id"
                + "/activities/context/cf3b5e1d-a582-4a52-ac26-f72233c44c40",
            json=mock_activity_data,
        )

        tap_solarvista.sync.sync_all_data(mock_config, mock_state, self.catalog)
        self.assertEqual(len(responses.calls), 2,
                         "Expecting 2 calls one to search another to history")

        self.assertEqual(len(SINGER_MESSAGES), 6)
        self.assertIsInstance(SINGER_MESSAGES[0], singer.SchemaMessage)
        self.assertIsInstance(SINGER_MESSAGES[1], singer.SchemaMessage)
        self.assertIsInstance(SINGER_MESSAGES[2], singer.RecordMessage)
        self.assertIsInstance(SINGER_MESSAGES[3], singer.StateMessage)
        self.assertIsInstance(SINGER_MESSAGES[4], singer.RecordMessage)
        self.assertIsInstance(SINGER_MESSAGES[5], singer.StateMessage)

        schema_messages = list(filter(
            lambda m: isinstance(m, singer.SchemaMessage), SINGER_MESSAGES))
        self.assertEqual(sorted(['workitem_stream', 'activity_stream']),
                            sorted([x.asdict()['stream'] for x in schema_messages]))

        record_messages = list(filter(
            lambda m: isinstance(m, singer.RecordMessage), SINGER_MESSAGES))

        expected_records = [
            {
                "actvivityId": "1",
                "contextProperties_stageType": "TravellingFrom",
                "contextProperties_ref": "56967",
                "contextProperties_visitId": "cf3b5e1d-a582-4a52-ac26-f72233c44c40",
                "createdBy": "f12a4565-4dd4-45bb-9189-dfb603e9b938",
                "createdOn": "2021-05-10T16:24:03.949878Z",
                "data_linkedWorkOrder": "77369110",
                "data_internalComments": "a comment"
            },
            {
                "workItemId": "cf3b5e1d-a582-4a52-ac26-f72233c44c40",
                "lastModified": "2020-12-01T12:26:21.1250844+00:00"
            }
        ]

        self.assertEqual(expected_records, [x.asdict()['record'] for x in record_messages])


if __name__ == '__main__':
    unittest.main()
