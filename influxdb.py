#https://docs.influxdata.com/influxdb/cloud/reference/key-concepts/data-elements/

#influxMeasurementKeyDict= { # the names of the pico w boards, according to uniq_id_names.py, is automatically added
#    "pico_hugo": "",
#    "pico_emil": "",
#}

influxFieldKeyDict= { # Zahlenwerte
    "temperature": "",
    "pressure": "",
    "powerOutage": "",
    "uptime": "",
}

influxTagKeyDict= {
    "unit": ["C", "K", "Pa", "s"],
    "room": ["B15","B16","B17", "B17"],
    "setup": ['sofia', 'tabea', 'fritz', 'charlie'],
    "position": "", # z.B. "N2 exhaust tube" 
    "user": ["pmaerki", "benekrat", "baehler"],
    "quality": ["testDeleteLater", "use"],
}

measurementExample = [{
    'measurement': 'pico_emil', # a measurement has one 'measurement'. It is the name of the pcb.
    'field': 'temperature', # a measurement has one 'field'.
    'value': '23.5', # a measurement has one 'value'.
    'tag': {
        'unit': 'C',
        'room': 'B15',
        "position": "hintenLinks",
        'user': 'pmaerki',
        },
    },]
        
def measurementTest(measurements):
    for measurement in measurements:
        #if influxMeasurementKeyDict.get(measurement['measurement']) !=  "":
        #    print(measurement['measurement'], 'is not contained as key in ', influxMeasurementKeyDict)
        #    return False
        if influxFieldKeyDict.get(measurement['field']) !=  "":
            print(measurement['field'], 'is not contained as key in ', influxFieldKeyDict)
            return False
        if measurement['value'] ==  None:
            print(measurement['value'], 'is not contained')
            return False
        for key in list(measurement['tag']):
            predefined = influxTagKeyDict[key]
            if predefined == "": # free to be defined by user
                if " " in measurement['tag'][key]:
                    print('Spaces are not allowed in ', measurement['tag'][key])
                    return False
                continue
            #print('key', key)
            #print('measurement[\'tag\']', measurement['tag'][key])
            #print('predefined', predefined)
            if measurement['tag'][key] in predefined:
                continue
            print(measurement['tag'][key], 'is not contained as value in ', "influxTagKeyDict", predefined)
            return False
    return True

assert(measurementTest(measurementExample))

import socket
import time
import struct
import machine
import urequests
import secrets
import wlan_helper

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

def upload_to_influx(measurements):  
    bucketName = secrets.influxdb_bucket
    assert(measurementTest(measurements))
    # https://www.alibabacloud.com/help/en/lindorm/latest/write-data-by-using-the-influxdb-line-protocol
    # <table_name>[,<tag_key>=<tag_value>[,<tag_key>=<tag_value>]] <field_key>=<field_value>[,<field_key>=<field_value>] [<timestamp>] 
    # Required: table_name field_set  (timestamp is not required!)
    # https://docs.influxdata.com/influxdb/v2.6/write-data/developer-tools/api/
    #     https://docs.influxdata.com/influxdb/v2.6/api/#operation/PostAuthorizations

    #payload = f"airSensor,sensorId=A0100,station=Harbor humidity=35.0658,{value}"
    payload = ""
    for measurement in measurements:
        if payload != "":
            payload += "\n"
        payload += f"{measurement['measurement']}"
        tags = measurement['tag']
        for tag in tags:
            payload += f",{tag}={measurement['tag'][tag]}"
            
        #payload += f",board={wlan_helper.boardName}"
        payload += f" {measurement['field']}={measurement['value']}"
    
    headers = {
    "Authorization": f"Token {secrets.influxdb_token}"
    }

    url = secrets.influxdb_url
    org = secrets.influxdb_org
    url += f"/api/v2/write?precision=s&org={url_encode(org)}&bucket={url_encode(bucketName)}"
 
    try:
        # post reading data to http endpoint
        result = urequests.post(url, headers=headers, data=payload)
        result.close()
        if result.status_code == 204:  # why 204? we'll never know...
            print("upload to influxdb success: ", payload)
            return "UPLOAD_SUCCESS"
        print(f"  - upload issue ({result.status_code} {result.reason})")
    except Exception as err:
        print(Exception, err)
        #except:
        #  print(f"  - an exception occurred when uploading")
    return "UPLOAD_FAILED"

#upload_to_influx(measurementExample)