""" Utilities used in this module """
import tap_solarvista
from tap_solarvista import schemas

def discover_catalog(datasource):
    """ Return a catalog with the supplied datasources updated with singer 'selected' metadata """
    catalog = tap_solarvista.catalog.discover({})
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
