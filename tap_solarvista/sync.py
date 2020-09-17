"""sync is responsible for http requests to target solarvista account"""
#!/usr/bin/env python3
import json
import requests
import singer

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
                        and len(response_data['continuationToken']) > 0):
                    continuation = response_data['continuationToken']
                for row in response_data['rows']:
                    if stream.tap_stream_id == 'workitem_stream':
                        tap_data.append(
                            flatten_json(
                                fetch_workitemdetail(config, row['rowData']['workItemId'])
                            )
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
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer " + config.get("personal_access_token")
        }
        LOGGER.info("POST %s", uri)
        with requests.post(uri, data=body, headers=headers) as response:
            if response.status_code == 200:
                response_data = response.json()
                return response_data
            LOGGER.error("[%s] POST %s", str(response.status_code), uri)
    return None

def fetch_workitemdetail(config, workitem_id):
    """ Fetch workitem detail """
    if workitem_id is not None:
        uri = "https://api.solarvista.com/workflow/v4/%s/workItems/id/%s" \
            % (config.get('account'), workitem_id)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer " + config.get("personal_access_token")
        }
        LOGGER.info("GET %s", uri)
        with requests.get(uri, headers=headers) as response:
            if response.status_code == 200:
                response_data = response.json()
                return response_data
            LOGGER.error("[%s] GET %s", str(response.status_code), uri)
    return None

def flatten_json(unformated_json):
    """ Flatten a json object, returning a single level underscore separated json structure """
    out = {}

    def flatten(json_structure, name=''):
        if isinstance(json_structure, dict):
            for element in json_structure:
                flatten(json_structure[element], name + element + '_')
        elif isinstance(json_structure, list):
            i = 0
            for element in json_structure:
                flatten(element, name + str(i) + '_')
                i += 1
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
