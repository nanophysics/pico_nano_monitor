'''
for debuging: delete file main.py on RP2. Execute main.py with Thonny from PC
for final use: put main.py on RP2
'''
import time
import wlan_helper
import influxdb
import machine

wlan_helper.enable_oled() # comment out if there is no oled
wlan_helper.start_wlan()
wlan_helper.update_if_local()

update_period_ms = 60 * 1000 # the time between upload of new measurements
time_restart_ms = time.ticks_add(wlan_helper.time_start_ms, 3 * 60 * 60 * 1000) # after this time the board will restart and check for new files (max of about 298 days)

from onewire import OneWire
from ds18x20 import DS18X20

ds = DS18X20(OneWire(machine.Pin(1))) # pin corresponds to GPx
sensors = ds.scan()
ds.convert_temp() # after power on reset the value is wrong. Therefore measure here once.
time.sleep_ms(900)  # mandatory pause to collect results, datasheet max 750 ms
for s in sensors:
    print('DS18b20 scanned sensor: \'' + ''.join('%02X' % i for i in iter(s)) + '\'')
DS18B20_id_tags = {
    '28D789660E00000A': {'position': 'auf_tisch', 'setup':'charlie'},
    }


    
key0_was_pressed = False
key1_was_pressed = False
def key0_isr(p):
    global key0_was_pressed
    key0_was_pressed = True
def key1_isr(p):
    global key1_was_pressed
    key1_was_pressed = True
key0 = machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_UP)
key1 = machine.Pin(17, machine.Pin.IN, machine.Pin.PULL_UP)
key0.irq(trigger=machine.Pin.IRQ_FALLING, handler=key0_isr)
key1.irq(trigger=machine.Pin.IRQ_FALLING, handler=key1_isr)
key0_was_pressed = False
key1_was_pressed = False


class Adc_5V_GP0:
    def __init__(self):
        self.adc = machine.ADC(machine.Pin(26)) # Number corresponds to GPx
        
    def voltage(self, average_n = 1):
        # a single measurement takes about 2 us
        # @ average = 1000 it takes about 14ms (measured)
        uref_V = 3.0 # when using an external LT4040 3V reference
        R31 = 3900.0
        R32 = 22000.0
        R3p = 1.0 / (1.0/R31 + 1.0/R32)
        R5 = 2200.0
        fs_V = (R5 + R3p ) / R3p * uref_V
        value_n = 0
        for i in range(average_n):
            value_n += self.adc.read_u16()
        return(float(value_n) / average_n / 2**16 * fs_V)

class Pressure_15_psi_sensor_ali():
    def __init__(self):
        self.adc_5V_GP0 = Adc_5V_GP0()
        self.overload = True

    def get_pressure_pa(self, average_n = 1000):
        voltage_V = self.adc_5V_GP0.voltage(average_n = average_n)
        # Drucksensor absolut von Alie XIDIBEI Official Store 15 psi
        pa_per_psi = 6894.75729 # https://www.unitconverters.net/pressure/psi-to-pascal.htm
        p1_pa = 0.0
        p2_pa = 15.0 * pa_per_psi
        u1_V = 0.5
        u2_V = 4.5
        self.overload = voltage_V < u1_V or voltage_V > u2_V
        return((p2_pa - p1_pa)/(u2_V - u1_V) * (voltage_V - u1_V))
    
    def get_overload(self):
        return self.overload
    
pressure_15_psi_sensor_ali = Pressure_15_psi_sensor_ali()



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
            'unit': 'Pa',
            'room': 'B15',
            'setup': DS_dict.get('setup'),
            'position': DS_dict.get('position'),
            'user': 'pmaerki',
            'quality': 'testDeleteLater',
            },
        "field": "pressure",
        "value": "%0.2f" % pressure_15_psi_sensor_ali.get_pressure_pa(average_n = 1000),
        })
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
        time.sleep_ms(50)
        if key0_was_pressed:
            wlan_helper.print_oled('key0 pressed')
            key0_was_pressed = False
            wlan_helper.time_next_update_ms = time.ticks_ms()
        if key1_was_pressed:
            wlan_helper.print_oled('key1 pressed')
            machine.reset()
    wlan_helper.print_time_since_start_s()

        
