#!/usr/bin/env python3
import json
import requests
import singer
from singer import metadata

LOGGER = singer.get_logger()

def fetch_all_data(config, state, catalog):
    """ Sync data from tap source """
    # Loop over selected streams in catalog
    for stream in catalog.get_selected_streams(state):
        LOGGER.info("Syncing stream:" + stream.tap_stream_id)

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
                if 'continuationToken' in response_data and len(response_data['continuationToken']) > 0:
                    continuation = response_data['continuationToken']
                for row in response_data['rows']:
                    tap_data.append(row['rowData'])

            write_data(stream, tap_data)
                
            if continuation is None:
                break
    return

def fetch_data(config, stream, continue_from):
    continuation = None
    if stream.stream_alias is not None:
        body = None
        uri = "https://api.solarvista.com/datagateway/v3/%s/datasources/ref/%s/data/query" % (config.get('account'), stream.stream_alias)
        if continue_from is not None:
            body = json.dumps({
              "continuationToken": continue_from
            })
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer " + config.get("personal_access_token")
        }
        LOGGER.info("POST " + uri)
        with requests.post(uri, data=body, headers = headers) as response:
            if response.status_code == 200:
                response_data = response.json()
                return response_data
            else:
                LOGGER.error("["+str(response.status_code)+"] POST "+uri)

    return None

def write_data(stream, tap_data):
    bookmark_column = stream.replication_key
    is_sorted = True  # TODO: indicate whether data is sorted ascending on bookmark value
    max_bookmark = None
    for row in tap_data:
        # TODO: place type conversions or transformations here

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
    
    return