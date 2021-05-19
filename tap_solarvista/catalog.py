"""catalog is responsible for inspecting which streams the target solarvista account supports."""
#!/usr/bin/env python3
from singer.catalog import Catalog, CatalogEntry
import tap_solarvista.schemas as schemas

def discover(selected_datasources):
    """Discover the streams this module can sync."""
    raw_schemas = schemas.load_schemas()
    streams = []
    for stream_id, schema in raw_schemas.items():
        stream_metadata = []
        # populate any metadata and stream's key properties here..
        datasource = schemas.extract_datasource(stream_id)
        # stream id becomes the table name, strip invalid characters for downstream targets
        stream_id = stream_id.replace('-', '')
        stream_name = datasource.replace('-', '')
        stream_replication_key = None
        stream_replication_method = 'FULL_TABLE'
        if stream_id == 'workitem_stream':
            stream_replication_key = "lastModified"
            stream_replication_method = "INCREMENTAL"

        if selected_datasources and datasource in selected_datasources:
            stream_metadata = [
                {'breadcrumb': (), 'metadata': {'selected': True}}
            ]

        key_properties = ['reference']
        if stream_id == 'appointment_stream':
            key_properties = ['appointmentId']
        if stream_id == 'users_stream':
            key_properties = ['userId']
        if stream_id == 'workitemhistory_stream':
            key_properties = ['workItemHistoryId']
        if stream_id == 'activity_stream':
            key_properties = ['activityId']

        streams.append(
            CatalogEntry(
                tap_stream_id=stream_id,
                stream=stream_name,
                schema=schema,
                key_properties=key_properties,
                metadata=stream_metadata,
                replication_key=stream_replication_key,
                is_view=None,
                database=None,
                table=None,
                row_count=None,
                stream_alias=datasource,
                replication_method=stream_replication_method,
            )
        )

    return Catalog(streams)
