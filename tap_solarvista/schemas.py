#!/usr/bin/env python3
import os
import json
import re
from singer.schema import Schema

def get_abs_path(path):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)


def load_schemas():
    """ Load schemas from schemas folder """
    schemas = {}
    for filename in os.listdir(get_abs_path('schemas')):
        path = get_abs_path('schemas') + '/' + filename
        file_raw = filename.replace('.json', '')
        with open(path) as file:
            schemas[file_raw] = Schema.from_dict(json.load(file))
    return schemas

def extract_datasource(schema_id):
    assert schema_id, "Expected schema to extract datasource name"
    match = re.search("(.*)_stream", schema_id, re.IGNORECASE)
    if match:
        datasource = match.group(1)
        return datasource
    
    return None