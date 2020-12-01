"""sync is responsible for http requests to target solarvista account"""
#!/usr/bin/env python3
import json
import requests
from urllib3.util import Retry
import singer
from tap_solarvista.timeout_http_adapter import TimeoutHttpAdapter

LOGGER = singer.get_logger()

def fetch_all_data(config, state, catalog):
    """ Sync data from tap source """
    # Loop over selected streams in catalog
    for stream in catalog.get_selected_streams(state):
        LOGGER.info("Syncing stream:%s", stream.tap_stream_id)

        singer.write_schema(
            stream_name=stream.tap_stream_id,
            schema=stream.schema.to_dict(),
            key_properties=stream.key_properties,
        )

        continuation = None
        while True:
            tap_data = []
            response_data = fetch_data(config, stream, continuation)
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
                        merged.update(fetch_workitemdetail(config, item['workItemId']))
                        tap_data.append(
                            flatten_json(merged)
                        )
                    else:
                        tap_data.append(
                            flatten_json(row['rowData'])
                        )

            write_data(stream, tap_data)

            if continuation is None:
                break

def fetch_data(config, stream, continue_from):
    """ Sync data from tap source with continuation """
    if stream.stream_alias is not None:
        body = None
        uri = "https://api.solarvista.com/datagateway/v3/%s/datasources/ref/%s/data/query" \
            % (config.get('account'), stream.stream_alias)
        if continue_from is not None:
            body = json.dumps({
                "continuationToken": continue_from
            })
        return fetch(config, "POST", uri, body)
    return None

def fetch_workitemdetail(config, workitem_id):
    """ Fetch workitem detail """
    if workitem_id is not None:
        uri = "https://api.solarvista.com/workflow/v4/%s/workItems/id/%s" \
            % (config.get('account'), workitem_id)
        return fetch(config, "GET", uri, None)
    return None

def fetch(config, method, uri, body):
    """ Fetch from Solarvista API """
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer " + get_access_token(config)
    }
    response = _fetch(config, method, headers, uri, body, 1)
    if response is not None:
        if response.status_code == 200:
            response_data = response.json()
            return response_data
    return None

#pylint: disable=too-many-arguments
def _fetch(config, method, headers, uri, body, refresh_auth):
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
        config.pop('personal_access_token', None)
        headers['Authorization'] = "Bearer " + get_access_token(config)
        response = _fetch(config, method, headers, uri, body, 0)
    return response


def get_access_token(config):
    """ Fetch access token from Solarvista API """
    if config.get("personal_access_token") is not None:
        return config.get("personal_access_token")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    body = "client_id=pat&grant_type=password&username=%s&password=%s" \
        % (config.get('clientId'), config.get('code'))
    response = _fetch(config, "POST", headers, "https://auth.solarvista.com/connect/token", body, 0)
    response.raise_for_status()
    if response is not None:
        if response.status_code == 200:
            response_data = response.json()
            access_token = response_data['access_token']
            config['personal_access_token'] = access_token
            return access_token
    return None

def flatten_json(unformated_json):
    """ Flatten a json object, returning a single level underscore separated json structure """
    out = {}

    def flatten(json_structure, name=''):
        if isinstance(json_structure, dict):
            for element in json_structure:
                flatten(json_structure[element], name + element + '_')
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
            if is_sorted:
                # update bookmark to latest value
                singer.write_state({stream.tap_stream_id: row[bookmark_column]})
            else:
                # if data unsorted, save max value until end of writes
                max_bookmark = max(max_bookmark, row[bookmark_column])

    if bookmark_column and not is_sorted:
        singer.write_state({stream.tap_stream_id: max_bookmark})
