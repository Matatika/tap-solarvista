# tap-solarvista

This is a [Singer](https://singer.io) tap that produces JSON-formatted data following the [Singer spec](https://github.com/singer-io/getting-started/blob/master/SPEC.md).

This tap:

- Pulls raw data from [Solarvista LIVE](https://api.solarvista.com)
- Queries the available resources, typically:
  	- [Customer]
  	- [Work-Item]
- Outputs the schema for each discovered resource
- Incrementally pulls data based on the input state for Work-Items


Create your own configuration with appropriate values from ```sample_config.json```.  See GDrive/Developers/Solarvista/Getting API access to Solarvista LIVE.docx

```
python3 -m venv ~/.virtualenvs/tap-solarvista
source ~/.virtualenvs/tap-solarvista/bin/activate
make install test

[do stuff e.g. discover, sync]

deactivate
```

### discover
Fetch all the streams we can sync

```
tap-solarvista -c your_config.json --discover > catalog.json
```

Update each stream in the catalog with the streams we want to sync or use the 'datasources' field in the configuration file.

      "metadata": [
        {
          "breadcrumb": [],
          "metadata": {
            "selected": "true"
          }
        }
      ]


### sync
Pull all the data

```
tap-solarvista -c your_config.json --catalog catalog.json
```

---

Copyright &copy; 2020 Matatika
