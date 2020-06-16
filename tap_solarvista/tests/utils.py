import tap_solarvista
import tap_solarvista.schemas as schemas


def discover_catalog(datasource):
    catalog = tap_solarvista.catalog.discover()
    streams = []

    for stream in catalog.streams:
        datasource_name = schemas.extract_datasource(stream.tap_stream_id)
        if datasource_name == datasource:
            stream.key_properties = []
            stream.metadata = [
                {'breadcrumb': (), 'metadata': {'selected': True}}
            ]
            streams.append(stream)

    catalog.streams = streams

    return catalog