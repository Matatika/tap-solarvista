Introduction
============

``tap_solarvista`` is a `Singer <https://singer.io>`_ tap that produces JSON-formatted data following the `Singer spec <https://github.com/singer-io/getting-started/blob/master/SPEC.md>`.

This tap:

- Pulls raw data from `Solarvista LIVE <https://api.solarvista.com>`
- Queries the available resources, e.g.:
  	- [Customer]
  	- [Work-Item]
	- [Site]
	- [Equipment]
- Outputs the schema for each discovered resource
- Incrementally pulls data based on the input state for Work-Items


