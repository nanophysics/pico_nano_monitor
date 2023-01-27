import influxdb_structure

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

def upload_to_influx(measurements, credentials = 'nano_monitor'):   # 'peter_influx_com'
    # https://www.alibabacloud.com/help/en/lindorm/latest/write-data-by-using-the-influxdb-line-protocol
    # <table_name>[,<tag_key>=<tag_value>[,<tag_key>=<tag_value>]] <field_key>=<field_value>[,<field_key>=<field_value>] [<timestamp>] 
    # Required: table_name field_set  (timestamp is not required!)
    # https://docs.influxdata.com/influxdb/v2.6/write-data/developer-tools/api/
    #     https://docs.influxdata.com/influxdb/v2.6/api/#operation/PostAuthorizations

    #payload = f"airSensor,sensorId=A0100,station=Harbor humidity=35.0658,temperature=37.2"
    #payload = f"airSensor,sensorId=A0100,station=Baum humidity=35.0658,temperature=37.2\n"
    #          f"airSensor uptime_s=1234\n"
    
    influxdb_structure.assert_valid(measurements)
    payload = ""
    for measurement in measurements:
        if payload != "":
            payload += "\n"
        payload += measurement['measurement']
        tags = measurement['tags']
        for tag, tag_value in tags.items():
            payload += f",{tag}={tag_value}"
        fields = measurement['fields']
        firstfield = True
        for field_name, field_value in fields.items():
            if firstfield:
                payload += f" {field_name}={field_value}"
                firstfield = False
            else:
                payload += f",{field_name}={field_value}"
    utils.log.log_print(payload, level = utils.TRACE)
    
    url = secrets.influx_credentials[credentials]['influxdb_url']

    for tries in range(5):
        utils.wdt.feed()
        try:
            if secrets.influx_credentials[credentials].get('influxdb_pass'): # authentication old
                db_name = secrets.influx_credentials[credentials].get('influxdb_db_name')
                auth=(secrets.influx_credentials[credentials].get('influxdb_user'), secrets.influx_credentials[credentials].get('influxdb_pass'))
                #print(url + f'/write?db={db_name}')#, data = payload, auth=auth)
                #print(auth)
                result = urequests.post(url + f'/write?db={db_name}', data = payload, auth=auth)

            if secrets.influx_credentials[credentials].get('influxdb_token'): # authentication new influxdb.com
                bucketName = secrets.influx_credentials[credentials]['influxdb_bucket']
                headers = {
                "Authorization": f"Token {secrets.influx_credentials[credentials]['influxdb_token']}"
                }
                org = secrets.influx_credentials[credentials]['influxdb_org']
                url += f"/api/v2/write?precision=s&org={url_encode(org)}&bucket={url_encode(bucketName)}"
                result = urequests.post(url, headers=headers, data=payload)

            result.close()
            if result.status_code == 204:  # why 204? we'll never know...
                utils.log.log("influx success")
                #utils.log.log_print(payload)
                return
            print(f"  - upload issue ({result.status_code} {result.reason})")
        except Exception as err:
            utils.log.log(Exception, err)
            utils.log.log('Could not upload')
            utils.reset_after_delay()
