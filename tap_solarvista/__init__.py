"""Singer.io tap that syncs data from Solarvista."""
#!/usr/bin/env python3
import argparse
import pkg_resources
import singer
from singer import utils

import tap_solarvista.catalog as catalog
import tap_solarvista.sync as sync

REQUIRED_CONFIG_KEYS = ["start_date", "personal_access_token", "account"]
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
    our_args = parser.parse_args()
    if our_args.version:
        return

    # Parse command line arguments
    args = utils.parse_args(REQUIRED_CONFIG_KEYS)

    # If discover flag was passed, run discovery mode and dump output to stdout
    if args.discover:
        selected_datasources = args.config.get('datasources')
        data_catalog = catalog.discover(selected_datasources)
        data_catalog.dump()
    # Otherwise run in sync mode
    else:
        if args.catalog:
            data_catalog = args.catalog
        else:
            data_catalog = catalog.discover({})
        sync.fetch_all_data(args.config, args.state, data_catalog)


if __name__ == "__main__":
    main()
