# Fridge monitoring

Initial implementation: Benedikt

* Bluefors writes logfiles into `C:\Users\{username}\Bluefors logs`.
* Every time a file is written, the last line is read and written to grafana.


## Installation

Create a shortcut on the desktop pointing to `fridge_monitoring\start_grafana_fridge_monitoring.bat`.

Double click this file to start monitoring.

Every few seconds there will be output like
```
influxdb.phys.ethz.ch nano_rw frrT0DJubhOS9sCYWqSz0MFVXL11IpHL nano_monitor
2024-01-23 18:26:00,084:DEBUG:Starting new HTTPS connection (1): influxdb.phys.ethz.ch:443
2024-01-23 18:26:00,127:DEBUG:https://influxdb.phys.ethz.ch:443 "GET /query?q=SHOW+DATABASES&db=nano_monitor HTTP/1.1" 200 None
Databases present in idb instance:  [{'name': 'nano_monitor'}]
```
