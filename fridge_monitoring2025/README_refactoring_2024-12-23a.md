# Folder: fridge_monitoring

See:
* fridge_monitoring/README.md
* fridge_monitoring/secrets_file.py
* Folder to be observe: BlueforsFridge, log_folder=rf"C:\Users\{username}\Bluefors logs"

## Strategy

Install venv
Refactor:
  * Mock grafana
  * Loop to read all files may be read
    * Test parsing
    * Test grafana formatting


## Installation

uv venv --python 3.13.1 --prompt=fridge_monitoring2025 ./venv

source ./venv/bin/activate
uv pip install -r requirements.txt

## Design

How to follow a file: https://github.com/kasun/python-tail/blob/master/tail.py

## Time

Currently, measurements use current time. Similar to https://github.com/petermaerki/puenterswis_heizung_2023_git/blob/main/software/software-zentral/zentral/util_influx.py#L79.

However, it would be beneficial to use the time stored in the file:
```
CH5 R 24-12-03.log
  03-12-24,00:22:10,6.526690e+02

CH5 T 24-12-03.log
  03-12-24,00:12:10,7.252130e-01

Flowmeter 24-12-03.log
  03-12-24,00:18:10,0.242708

Channels 24-12-03.log
  03-12-24,00:20:10,0,v1,1,v2,0,v3,0,v4,1,v5,0,v6,0,v7,1,v8,0,v9,1,v10,1,v11,0,v12,0,v13,0,v14,0,v15,0,v16,0,v17,0,v18,0,v19,0,v20,0,v21,0,v22,0,v23,0,turbo1,1,turbo2,0,scroll1,1,scroll2,0,compressor,0,pulsetube,1,hs-still,0,hs-mc,0,ext,1

maxigauge 24-12-03.log
  03-12-24,00:12:10,CH1,        ,1,1.83e-06,0,1,CH2,        ,1,9.62e-03,0,1,CH3,        ,1,3.51e+02,0,1,CH4,        ,1,3.71e+02,0,1,CH5,        ,1,3.70e+00,0,1,CH6,        ,1,9.50e+00,0,1,

Status_24-12-03.log
  03-12-24,00:16:10,ctrl_pres_ok,1.000000e+00,ctrl_pres,1.000000e+00,cpastate,3.000000e+00,cparun,1.000000e+00,cpawarn,-0.000000e+00,cpaerr,-0.000000e+00,cpatempwi,1.859667e+01,cpatempwo,2.651833e+01,cpatempo,3.448889e+01,cpatemph,6.117723e+01,cpalp,1.007056e+02,cpalpa,1.023911e+02,cpahp,3.231992e+02,cpahpa,3.273502e+02,cpadp,2.249408e+02,cpacurrent,1.725316e+01,cpahours,6.906636e+07,cpascale,0.000000e+00,cpasn,5.171300e+04,ctr_pressure_ok,1.000000e+00,pcu_pv,0.000000e+00,pcu_gv,1.000000e+00,pcu_pos,1.199000e+01,pcu_dst,0.000000e+00,pcu_probe_out,0.000000e+00,pcu_probe_in,0.000000e+00,pcu_torque_limit,0.000000e+00,pcu_destination_set,0.000000e+00,pcu_motor_off,1.000000e+00,pcu_pos_compl,0.000000e+00,pcu_going_home,0.000000e+00,pcu_no_ctrl_pressure,1.000000e+00,pcu_integrity_ok,0.000000e+00,pcu_maintenance_mode,0.000000e+00,pcu_probe_mounted,1.000000e+00,pcu_vacuum,1.000000e+00,pcu_remote,1.000000e+00,tc400actualspd_3,8.190000e+02,tc400drvpower_3,9.500000e+01,tc400ovtempelec_3,0.000000e+00,tc400ovtemppum_3,0.000000e+00,tc400heating_3,0.000000e+00,tc400pumpaccel_3,0.000000e+00,tc400pumpstatn_3,1.000000e+00,tc400remoteprio_3,1.000000e+00,tc400spdswptatt_3,1.000000e+00,tc400setspdatt_3,1.000000e+00,tc400standby_3,0.000000e+00
```

## Observing files

### Every minute: Verify if new top folder exists, eg. '24-12-02'.

### Every minute: Verify if new file exists. Start observing this file.

### When the program restarts: The current day will be send to influxdb (duplicate date)


## Error handling

* Exception Influxdb: Restarts the connection to influxdb
* Exception Parsing: Will just be logged

## Logfile

* INFO: Wheneved data is collected/sent
* WARNING: expected errors
* ERROR: unhandled exception
