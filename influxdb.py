#https://docs.influxdata.com/influxdb/cloud/reference/key-concepts/data-elements/

influxFieldKeyDict= { # Zahlenwerte
    "temperature_C": None,
    "temperature_K": None,
    "pressure_Pa_rel": None,
    "powerOutage_s": None,
    "uptime_s": None,
    "humidity_pRH": None,}

influxTagKeyDict= {
    "room": ["B15","B16","B17", "C17"],
    "setup": ['sofia', 'tabea', 'fritz', 'charlie', 'broker'],
    "position": None, # z.B. "N2 exhaust tube" 
    "user": ["pmaerki", "benekrat", "baehler", "lostertag"],
    "quality": ["testDeleteLater", "use"],}

measurementExample = [{
    'measurement': 'pico_emil', # a measurement has one 'measurement'. It is the name of the pcb.
    'fields': {
        'temperature_C': '23.5',
        'humidity_pRH': '88.2',},
    'tags': {
        'room': 'B15',
        "position": "hintenLinks",
        'user': 'pmaerki',},
    },]
        
def assert_valid(measurements):
    for measurement in measurements:
        for field_name in measurement['fields']:
            assert field_name in influxFieldKeyDict, f"field '{field_name}' is not in {influxFieldKeyDict}"
        for tag_name, tag_value in measurement['tags'].items():
            valid_values = influxTagKeyDict[tag_name]
            if valid_values is None:
                continue
            assert tag_value in valid_values, f"{tag_name}={tag_value} is not in {valid_values}"


assert_valid(measurementExample)

import socket
import time
import struct
import machine
import urequests
import secrets
import utils

def url_encode(t):
  result = ""
  for c in t:
    # no encoding needed for character
    if c.isalpha() or c.isdigit() or c in ["-", "_", "."]:
      result += c
    elif c == " ":
      result += "+"
    else:
      result += f"%{ord(c):02X}"
  return result

def upload_to_influx(measurements, credentials = 'peter_influx_com'):  
    bucketName = secrets.influx_credentials[credentials]['influxdb_bucket']
    assert_valid(measurements)
    # https://www.alibabacloud.com/help/en/lindorm/latest/write-data-by-using-the-influxdb-line-protocol
    # <table_name>[,<tag_key>=<tag_value>[,<tag_key>=<tag_value>]] <field_key>=<field_value>[,<field_key>=<field_value>] [<timestamp>] 
    # Required: table_name field_set  (timestamp is not required!)
    # https://docs.influxdata.com/influxdb/v2.6/write-data/developer-tools/api/
    #     https://docs.influxdata.com/influxdb/v2.6/api/#operation/PostAuthorizations

    #payload = f"airSensor,sensorId=A0100,station=Harbor humidity=35.0658 temperature=37.2"
    #payload = f"airSensor,sensorId=A0100,station=Baum humidity=35.0658 temperature=37.2\n"
    #          f"airSensor uptime_s=1234\n"
    payload = ""
    for measurement in measurements:
        if payload != "":
            payload += "\n"
        payload += measurement['measurement']
        tags = measurement['tags']
        for tag, tag_value in tags.items():
            payload += f",{tag}={tag_value}"
        fields = measurement['fields']
        for field_name, field_value in fields.items():
            payload += f" {field_name}={field_value}"
    
    headers = {
    "Authorization": f"Token {secrets.influx_credentials[credentials]['influxdb_token']}"
    }

    url = secrets.influx_credentials[credentials]['influxdb_url']
    org = secrets.influx_credentials[credentials]['influxdb_org']
    url += f"/api/v2/write?precision=s&org={url_encode(org)}&bucket={url_encode(bucketName)}"

    if False:
        result = urequests.get(url='http://ergoinfo.ch/')
        #result.close()
        print(result.text)
 
    for tries in range(5):
        utils.wdt.feed()
        try:
            # post reading data to http endpoint
            result = urequests.post(url, headers=headers, data=payload)
            result.close()
            if result.status_code == 204:  # why 204? we'll never know...
                utils.log.log("influx success")
                utils.log.log_print(payload)
                return
            print(f"  - upload issue ({result.status_code} {result.reason})")
        except Exception as err:
            print(Exception, err)
            utils.reset_after_delay()


#upload_to_influx(measurementExample)