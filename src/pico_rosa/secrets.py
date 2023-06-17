wlan_credentials = {
    "default": [
        {"SSID": "RUT240_FCE0", "PASSWORD": "p3PLa9s7"},
        {"SSID": "salamibrot", "PASSWORD": "guguseli"},
        #{"SSID": "u", "PASSWORD": "guguseli"},
        #{"SSID": "eth-iot", "PASSWORD": "dw56v8c-9z2f"},
    ],
}

influx_credentials = {
    "peter_influx_com": {
        "influxdb_org": "organisation",
        "influxdb_url": "https://eu-central-1-1.aws.cloud2.influxdata.com",
        "influxdb_token": "SXz6XEx5bl-8FF2pHYZVkgSUzLue2GF9MWgfIRrPxY7P-S9kfCrNACKOqxP01wTnG2Smsm1-IlVkZT4OgZ65DA==",
        "influxdb_bucket": "bucketPeter",
    },
    "peter_maerki_com": {
        "influxdb_org": "maerki-org",
        "influxdb_url": "http://maerki.com:8086",
        "influxdb_token": "eEPs51uRcOS6HZ2M8nTqc9zVSpyfT-P8XUoZw3-Ur-F4g23Hn8Sb9YEd22u3GZYt_teuAfEHQYGGRZIoCaOgAg==",
        "influxdb_bucket": "rutschbahnhaus",
    },
    "nano_monitor": {
        "influxdb_db_name": "nano_monitor",
        "influxdb_url": "https://influxdb.phys.ethz.ch",
        "influxdb_user": "nano_rw",
        "influxdb_pass": "frrT0DJubhOS9sCYWqSz0MFVXL11IpHL",
    },
}
