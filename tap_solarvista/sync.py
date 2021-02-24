"""sync is responsible for http requests to target solarvista account"""
#!/usr/bin/env python3
import json
import requests
from urllib3.util import Retry
from datetime import datetime
from dateutil.relativedelta import relativedelta
import singer
from tap_solarvista.timeout_http_adapter import TimeoutHttpAdapter

LOGGER = singer.get_logger()
CONFIG = {}
STATE = {}

def get_start(entity):
    """ Get the start point for incremental sync """
    if entity not in STATE:
        STATE[entity] = CONFIG['start_date']

    return STATE[entity]


#pylint: disable=too-many-branches
def sync_all_data(config, state, catalog):
    """ Sync data from tap source """
    CONFIG.update(config)
    LOGGER.info("CONFIG [%s]", CONFIG)
    STATE.update(state)
    LOGGER.info("STATE [%s]", STATE)

    # Write all schema messages for selected streams in catalog
    for stream in catalog.get_selected_streams(state):
        singer.write_schema(
            stream_name=stream.tap_stream_id,
            schema=stream.schema.to_dict(),
            key_properties=stream.key_properties,
        )

    # Sync all selected streams in catalog
    selected_streams = catalog.get_selected_streams(state)
    user_stream = None
    users = []
    for stream in selected_streams:
        # workitemhistory will sync on each work item
        if stream.tap_stream_id == 'workitemhistory_stream':
            continue
        # appointments sync after all streams, once we have a list of users
        if stream.tap_stream_id == 'appointment_stream':
            continue
        LOGGER.info("Syncing stream:%s", stream.tap_stream_id)
        continuation = None
        with singer.metrics.record_counter(stream.tap_stream_id) as counter:
            while True:
                if (stream.tap_stream_id == 'workitem_stream'
                        and CONFIG.get('workitem_detail_enabled') is None):
                    response_data = sync_workitems_by_filter(stream,
                                            stream.replication_key, continuation)
                else:
                    response_data = sync_datasource(stream, continuation)
                tap_data = []
                continuation = None
                if response_data is not None:
                    if ('continuationToken' in response_data
                            and response_data['continuationToken'] is not None
                            and len(response_data['continuationToken']) > 0):
                        continuation = response_data['continuationToken']
                    for row in response_data['rows']:
                        if stream.tap_stream_id == 'workitem_stream':
                            item = row['rowData']
                            merged = {}
                            merged.update(item)
                            if CONFIG.get('workitem_detail_enabled') is not None:
                                merged.update(fetch_workitemdetail(item['workItemId']))
                            sync_workitemhistory(catalog, item['workItemId'])
                            tap_data.append(
                                flatten_json(merged)
                            )
                        else:
                            item = row['rowData']
                            if stream.tap_stream_id == 'users_stream':
                                user_stream = stream
                                users.append(item['userId'])
                            merged = {}
                            merged.update(item)
                            if 'lastModified' in row:
                                merged.update({ 'lastModified': row['lastModified'] })
                            tap_data.append(
                                flatten_json(merged)
                            )
                        counter.increment()

                write_data(stream, tap_data)
                if continuation is None:
                    break
            while True:
                tap_data = []
                continuation = None
                if user_stream and users:
                    LOGGER.info("Syncing stream:%s", "")
                    response_data = sync_appointment(user_stream, continuation, users)
                    if response_data is not None:
                        process_response_data(catalog, user_stream, counter, response_data)
                if continuation is None:
                    break


def process_response_data(catalog, stream, counter, response_data):
    tap_data = []
    continuation = None
    if response_data is not None:
        if ('continuationToken' in response_data
                and response_data['continuationToken'] is not None
                and len(response_data['continuationToken']) > 0):
            continuation = response_data['continuationToken']
        for row in response_data['rows']:
            if stream.tap_stream_id == 'workitem_stream':
                item = row['rowData']
                merged = {}
                merged.update(item)
                if CONFIG.get('workitem_detail_enabled') is not None:
                    merged.update(fetch_workitemdetail(item['workItemId']))
                sync_workitemhistory(catalog, item['workItemId'])
                tap_data.append(
                    flatten_json(merged)
                )
            else:
                item = row['rowData']
                merged = {}
                merged.update(item)
                if 'lastModified' in row:
                    merged.update({ 'lastModified': row['lastModified'] })
                tap_data.append(
                    flatten_json(merged)
                )
            counter.increment()

    write_data(stream, tap_data)
    return continuation


def sync_workitems_by_filter(stream, bookmark_property, continue_from, predefined_filter=None):
    """ Sync work-item data from tap source with continuation """
    state_entity = stream.tap_stream_id
    if predefined_filter:
        state_entity = state_entity + "_" + predefined_filter
    start = get_start(state_entity)
    query = {
      'lastModifiedAfter': start,
      'orderBy': bookmark_property,
      'orderByDirection': "ascending"
    }
    if continue_from is not None:
        query['continuationToken'] = continue_from
    ## add tests and full support for predefined_filter, e.g. isCompleted
    #{
    #    'comparison': "equals",
    #    'fieldName': "isCompleted",
    #    'value': True
    #}
    if predefined_filter:
        LOGGER.info("Syncing work-items with filter %s", predefined_filter)
        query['filterGroups'] = [{ 'filters': predefined_filter }]
    LOGGER.info("Syncing work-items since %s", start)
    uri = "https://api.solarvista.com/workflow/v4/%s/workItems/search" \
        % (CONFIG.get('account'))
    body = json.dumps(query)
    response_data = fetch("POST", uri, body)
    return transform_search_to_look_like_rowdata(response_data)


def transform_search_to_look_like_rowdata(response_data):
    """ transform the search results, so we can reuse the sync loop """
    if response_data is None:
        return None
    new_data = {}
    if response_data.get('continuationToken'):
        new_data['continuationToken'] = response_data['continuationToken']
    rows = []
    if response_data['items']:
        for item in response_data['items']:
            if item.get("fieldValues"):
                item["properties"] = item.pop("fieldValues")
            rows.append({ "rowData": item})
    new_data['rows'] = rows
    return new_data

def transform_appointments_to_look_like_rowdata(response_data):
    """ transform the appointments results, so we can reuse the sync loop """
    if response_data is None:
        return None
    new_data = {}
    if response_data.get('continuationToken'):
        new_data['continuationToken'] = response_data['continuationToken']
    rows = []
    if response_data['appointments']:
        for item in response_data['appointments']:
            rows.append({ "rowData": item})
    new_data['rows'] = rows
    return new_data

def sync_datasource(stream, continue_from):
    """ Sync data from tap source with continuation """
    if stream.stream_alias is not None:
        body = None
        uri = "https://api.solarvista.com/datagateway/v3/%s/datasources/ref/%s/data/query" \
            % (CONFIG.get('account'), stream.stream_alias)
        if continue_from is not None:
            body = json.dumps({
                "continuationToken": continue_from
            })
        return fetch("POST", uri, body)
    return None

def sync_appointment(stream, continue_from, userIds):
    """ Sync data from tap source with continuation """
    if stream.stream_alias is not None:
        body = None
        uri = "https://api.solarvista.com/calendar/v2/%s/appointments/search/%s" \
            % (CONFIG.get('account'), 'users')
        oneYearPast = datetime.now() - relativedelta(years=1)
        oneYearFuture = datetime.now() - relativedelta(years=1)
        query = {
            "from": oneYearPast.isoformat(),
            "includeUnassigned": True,
            "to": oneYearFuture.isoformat(),
            "userIds": userIds
        }
        if continue_from is not None:
            query['continuationToken'] = continue_from
        body = json.dumps(query)
        response_data = fetch("POST", uri, body)
        return transform_appointments_to_look_like_rowdata(response_data)
    return None

def sync_workitemhistory(catalog, workitem_id):
    """ Sync data from work item history """
    if workitem_id is not None:
        workitem_history_stream = catalog.get_stream('workitemhistory_stream')
        if workitem_history_stream and workitem_history_stream.is_selected():
            with singer.metrics.record_counter(workitem_history_stream.tap_stream_id) as counter:
                uri = "https://api.solarvista.com/workflow/v4/%s/workItems/id/%s/history" \
                    % (CONFIG.get('account'), workitem_id)
                history_rows = transform_workitemhistory_to_rowdata(fetch("GET", uri, None))
                if history_rows.get('rows'):
                    tap_data = []
                    for history_row in history_rows['rows']:
                        tap_data.append(history_row['rowData'])
                        counter.increment()
                    write_data(workitem_history_stream, tap_data)

def fetch_workitemdetail(workitem_id):
    """ Fetch workitem detail """
    if workitem_id is not None:
        uri = "https://api.solarvista.com/workflow/v4/%s/workItems/id/%s" \
            % (CONFIG.get('account'), workitem_id)
        response_data = fetch("GET", uri, None)
        return response_data
    return None

def transform_workitemhistory_to_rowdata(response_data):
    """ transform the work item history response to row data """
    if response_data is None:
        return None
    workitem_data = {}
    for k, value in response_data.items():
        if k != 'stages':
            workitem_data[k] = value

    new_data = {}
    for k, value in response_data.items():
        if k == 'stages':
            rows = []
            for i, stage in enumerate(value):
                row_data = {}
                row_data['workItemHistoryId'] = workitem_data['workItemId'] + "_" + str(i)
                row_data.update(workitem_data)
                stage_data= {}
                stage_data['stage'] = stage
                row_data.update(flatten_json(stage_data))
                rows.append({ "rowData": row_data})
            new_data['rows'] = rows
    return new_data

def fetch(method, uri, body):
    """ Fetch from Solarvista API """
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer " + get_access_token()
    }
    response = _fetch(method, headers, uri, body, 1)
    if response is not None:
        if response.status_code == 200:
            response_data = response.json()
            return response_data
    return None

def _fetch(method, headers, uri, body, refresh_auth):
    """ Internal fetch to allow access token to be refreshed """
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    http = requests.Session()
    http.mount("https://", TimeoutHttpAdapter(max_retries=retries))
    response = None
    if method == "GET":
        LOGGER.info("GET %s", uri)
        with requests.get(uri, headers=headers) as res:
            LOGGER.info("[%s] GET %s", str(res.status_code), uri)
            response = res
    elif method == "POST":
        LOGGER.info("POST %s", uri)
        with requests.post(uri,
                           data=body,
                           headers=headers) as res:
            LOGGER.info("[%s] POST %s", str(res.status_code), uri)
            response = res
    if response is not None and refresh_auth and response.status_code == 401:
        LOGGER.error("[%s] token expired %s", str(response.status_code), uri)
        CONFIG.pop('personal_access_token', None)
        headers['Authorization'] = "Bearer " + get_access_token()
        response = _fetch(method, headers, uri, body, 0)
    return response


def get_access_token():
    """ Fetch access token from Solarvista API """
    if CONFIG.get("personal_access_token") is not None:
        return CONFIG.get("personal_access_token")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    body = "client_id=pat&grant_type=password&username=%s&password=%s" \
        % (CONFIG.get('clientId'), CONFIG.get('code'))
    response = _fetch("POST", headers, "https://auth.solarvista.com/connect/token", body, 0)
    response.raise_for_status()
    if response is not None:
        if response.status_code == 200:
            response_data = response.json()
            access_token = response_data['access_token']
            CONFIG['personal_access_token'] = access_token
            return access_token
    return None

lowerFirstCharacter = lambda s: s[:1].lower() + s[1:] if s else ''

def flatten_json(unformated_json):
    """ Flatten a json object, returning a single level underscore separated json structure """
    out = {}

    def flatten(json_structure, name=''):
        if isinstance(json_structure, dict):
            for element in json_structure:
                flatten(json_structure[element], name + lowerFirstCharacter(element) + '_')
        else:
            out[name[:-1]] = json_structure

    flatten(unformated_json)
    return out

def write_data(stream, tap_data):
    """ Write the fetched data to singer records and update state """
    bookmark_column = stream.replication_key
    is_sorted = True  # indicate whether data is sorted ascending on bookmark value
    max_bookmark = None
    for row in tap_data:
        # write one or more rows to the stream:
        singer.write_records(stream.tap_stream_id, [row])
        if bookmark_column:
            if row.get(bookmark_column):
                if is_sorted:
                    # update bookmark to latest value
                    singer.write_state({stream.tap_stream_id: row[bookmark_column]})
                else:
                    # if data unsorted, save max value until end of writes
                    max_bookmark = max(max_bookmark, row[bookmark_column])
            else:
                LOGGER.error("[%s] bookmark value not found in column [%s]",
                             stream.tap_stream_id, bookmark_column)

    if bookmark_column and not is_sorted:
        singer.write_state({stream.tap_stream_id: max_bookmark})
