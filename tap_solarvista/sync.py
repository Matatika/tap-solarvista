#!/usr/bin/env python3
import requests
import singer
from singer import metadata

LOGGER = singer.get_logger()

def fetch_all_data(config, state, catalog):
    """ Sync data from tap source """
    # Loop over selected streams in catalog
    for stream in catalog.get_selected_streams(state):
        LOGGER.info("Syncing stream:" + stream.tap_stream_id)

        bookmark_column = stream.replication_key
        is_sorted = True  # TODO: indicate whether data is sorted ascending on bookmark value

        singer.write_schema(
            stream_name=stream.tap_stream_id,
            schema=stream.schema.to_dict(),
            key_properties=stream.key_properties,
        )

        # Fetch data
        tap_data = []
        if stream.tap_stream_id is not None:
            uri = "https://api.solarvista.com/datagateway/v3/%s/datasources/ref/%s/data/query" % (config.get('account'), stream.stream)
            headers = {"Authorization": "Bearer " + config.get("PAT")}
            LOGGER.info("POST " + uri)
            with requests.post(uri, headers = headers) as response:
                if response.status_code == 200:
                    response_data = response.json()
                    for row in response_data['rows']:
                        print(row)
                else:
                    LOGGER.error("["+str(response.status_code)+"] POST "+uri)
                
        # TODO: delete and replace this inline function with your own data retrieval process:
        #tap_data = lambda: [{"id": x, "name": "row${x}"} for x in range(1000)]

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
