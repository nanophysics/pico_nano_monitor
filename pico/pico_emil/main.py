'''
for debuging: delete file main.py on RP2. Execute main.py with Thonny from PC
for final use: put main.py on RP2
'''
import time
import wlan_helper
import influxdb
from machine import Pin

#wlan_helper.enable_oled() # comment out if there is no oled
wlan_helper.start_wlan()
wlan_helper.update_if_local()

update_period_ms = 60 * 1000 # the time between upload of new measurements
time_restart_ms = time.ticks_add(wlan_helper.time_start_ms, 3 * 60 * 60 * 1000) # after this time the board will restart and check for new files (max of about 298 days)

from onewire import OneWire
from ds18x20 import DS18X20

ds = DS18X20(OneWire(Pin(28)))
sensors = ds.scan()
ds.convert_temp() 		# after power on reset the value is wrong. Therefore measure here once.
time.sleep_ms(900)     	# mandatory pause to collect results, datasheet max 750 ms
for s in sensors:
    ('DS18b20 scanned sensor: \'' + ''.join('%02X' % i for i in iter(s)) + '\'')

DS18B20_id_tags = {
    '2847C4660E0000BE': {'position': 'hintenLinks', 'setup':'sofia'},
    '28915A660E0000DD': {'position': 'obenRechts', 'setup':'sofia'},
    '2856D0980D000031': {'position': 'unterPumpe', 'setup':'tabea'},
    '28BA11A20E00003D': {'position': 'angeklebt', 'setup':'fritz'},
    '28D071660E000017': {'position': 'draufgelegt', 'setup':'fritz'},
    '2810C2A20E0000BE': {'position': 'inLoch', 'setup':'fritz'},
    }

while True:
    wlan_helper.led.value(1)
    measurements = []
    ds.convert_temp()
    time.sleep_ms(750+150)     # mandatory pause to collect results, datasheet max 750 ms
    for s in sensors:
        temperatureC = ds.read_temp(s)
        DS_dict = DS18B20_id_tags.get(''.join('%02X' % i for i in iter(s)))
        if DS_dict != None:
            measurements.append(
                {
                'measurement': wlan_helper.boardName,
                'tag': {
                    'unit': 'C',
                    'room': 'B15',
                    'setup': DS_dict.get('setup'),
                    'position': DS_dict.get('position'),
                    'user': 'pmaerki',
                    'quality': 'testDeleteLater',
                    },
                "field": "temperature",
                "value": "%0.2f" % temperatureC,
                })
            wlan_helper.print_oled('%0.2fC ' % temperatureC, DS_dict.get('position'))
    measurements.append(
        {
        'measurement': wlan_helper.boardName,
        'tag': {
            'unit': 's',
            'quality': 'testDeleteLater',
            },
        "field": "uptime",
        "value": "%d" % wlan_helper.time_since_start_s(),
        })
    if measurements == []:
        wlan_helper.print_oled('No Temperatures could be measured')
        continue
    success = influxdb.upload_to_influx(measurements)
    wlan_helper.print_oled(success)
    if success == 'UPLOAD_FAILED': continue
    if time.ticks_diff(time.ticks_ms(), time_restart_ms) > 0:
        wlan_helper.print_oled('It is time to restart as the time period time_restart_ms is over.')
        wlan_helper.reset_after_delay()
        
    wlan_helper.time_next_update_ms = time.ticks_add(wlan_helper.time_next_update_ms, update_period_ms)
    
    while time.ticks_diff(wlan_helper.time_next_update_ms, time.ticks_ms()) > 0: # we need to wait
        wlan_helper.feedWDT()
        wlan_helper.led.value(1)
        time.sleep_ms(50)
        wlan_helper.led.value(0)
        time.sleep_ms(1000-50)
        
    wlan_helper.print_time_since_start_s()
