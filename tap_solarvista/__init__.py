"""Singer.io tap that syncs data from Solarvista."""
#!/usr/bin/env python3
import argparse
import pkg_resources
import singer
from singer import utils

from tap_solarvista import catalog
from tap_solarvista import sync

REQUIRED_CONFIG_KEYS = ["start_date", "clientId", "code", "account"]
LOGGER = singer.get_logger()

@utils.handle_top_exception(LOGGER)
def main():
    """Main entrypoint into this module, typically tap-solarvista."""

    version = pkg_resources.require("tap_solarvista")[0].version

    # Parse our args, before handing off to singer
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-v', '--version',
        help='Print version',
        action='version', version=version)

    parser.add_argument(
        '-c', '--config',
        help='Config file',
        required=True)

    parser.add_argument(
        '-s', '--state',
        help='State file')

    parser.add_argument(
        '-p', '--properties',
        help='Property selections: DEPRECATED, Please use --catalog instead')

    parser.add_argument(
        '--catalog',
        help='Catalog file')

    parser.add_argument(
        '-d', '--discover',
        action='store_true',
        help='Do schema discovery')

    # handle version, but carry on to singer for the rest
    parser.parse_args()

    # Parse command line arguments
    args = utils.parse_args(REQUIRED_CONFIG_KEYS)

    selected_datasources = args.config.get('datasources')

    if args.catalog:
        data_catalog = args.catalog
    if selected_datasources:
        data_catalog = catalog.discover(selected_datasources)
    else:
        data_catalog = catalog.discover({})

    # If discover flag was passed, run discovery mode and dump output to stdout
    if args.discover:
        data_catalog.dump()
    # Otherwise run in sync mode
    else:
        sync.sync_all_data(args.config, args.state, data_catalog)

if __name__ == "__main__":
    main()
