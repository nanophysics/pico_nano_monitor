"""
for debuging: delete file main.py on RP2. Execute main.py with Thonny from PC
for final use: put main.py on RP2
"""
import time
import machine
import utils
import micropython

micropython.alloc_emergency_exception_buf(100)

time.sleep_ms(3000) # allows to interrupt with Thonny

utils.wdt.enable()
utils.log.enable_oled()  # comment out if there is no oled
utils.wlan.start_wlan()
utils.file_updater.update_if_local()

minute_ms = micropython.const(60 * 1000)
hour_ms = micropython.const(60 * minute_ms)
utils.time_manager.set_period_restart_ms(
    time_restart_ms=24 * hour_ms
)  # will reset after this time

S0 = machine.Pin("GPIO2", machine.Pin.OUT)
S1 = machine.Pin("GPIO3", machine.Pin.OUT)
S2 = machine.Pin("GPIO4", machine.Pin.OUT)


from onewire import OneWire
from ds18x20 import DS18X20

ds = DS18X20(OneWire(machine.Pin("GPIO1")))
sensors = ds.scan()
ds.convert_temp() 		# after power on reset the value is wrong. Therefore measure here once.
time.sleep_ms(900)     	# mandatory pause to collect results, datasheet max 750 ms
for s in sensors:
    print('DS18b20 scanned sensor: \'' + ''.join('%02X' % i for i in iter(s)) + '\'')



class Adc_GP27:
    def __init__(self):
        self.adc = machine.ADC(machine.Pin(27))  # Number corresponds to GPx

    def voltage_V(self, average_n=1):
        # a single measurement takes about 2 us
        # @ average = 1000 it takes about 14ms (measured)
        uref_V = 3.0  # when using an external LT4040 3V reference
        value_n = 0
        for i in range(average_n):
            value_n += self.adc.read_u16()
        voltage_V = float(value_n) / average_n / 2 ** 16 * uref_V
        print (voltage_V)
        return voltage_V

adc_V = Adc_GP27()

def messen_A():
    #global S0
    S0.value(0)
    time.sleep_ms(100)
    referenz_V = adc_V.voltage_V(average_n = 10000)
    #assert abs(referenz_V - 1.65) < 0.3
    S0.value(1)
    time.sleep_ms(100)
    signal_V = adc_V.voltage_V(average_n = 10000)
    messsignal_V = signal_V - referenz_V
    strom_A = messsignal_V / 0.625 * 25.0
    return strom_A

while True:
    utils.board.set_led(value=1)
    measurements = []
    ds.convert_temp()
    time.sleep_ms(750+150)     # mandatory pause to collect results, datasheet max 750 ms
    dict_tag = {'user': 'hannav','quality': 'testDeleteLater','setup':'HPT_nitrogen_tank'}
    for sensor in sensors: # only one sensor is used!!!
        Dict_tag = dict_tag.update({'position': 'wallbox_powersupplies'})
        utils.mmts.append(
            {"tags": dict_tag, "fields": {"temperature_C": "%0.2f" % ds.read_temp(sensor)}}
        )
    S1.value(0)
    S2.value(0)
    offset_1_A = -0.503
    Dict_tag = dict_tag.copy()
    Dict_tag.update({'position': 'tank_a'})
    utils.mmts.append(
        {"tags": Dict_tag, "fields": {"current_A": "%0.3f" % (messen_A()-offset_1_A)}}
    )
    S1.value(1)
    S2.value(0)
    offset_2_A = -0.481
    Dict_tag = dict_tag.copy()
    Dict_tag.update({'position': 'tank_b'})
    utils.mmts.append(
        {"tags": Dict_tag, "fields": {"current_A": "%0.3f" % (messen_A()-offset_2_A)}}
    )
    S1.value(0)
    S2.value(1)
    offset_3_A = -0.488
    Dict_tag = dict_tag.copy()
    Dict_tag.update({'position': 'ventil_2'})
    utils.mmts.append(
        {"tags": Dict_tag, "fields": {"current_A": "%0.3f" % (messen_A()-offset_3_A)}}
    )
    S1.value(1)
    S2.value(1)
    offset_3_A = -0.717
    Dict_tag = dict_tag.copy()
    Dict_tag.update({'position': 'ventil_11'})
    utils.mmts.append(
        {"tags": Dict_tag, "fields": {"current_A": "%0.3f" % (messen_A()-offset_3_A)}}
    )

    utils.mmts.append(
        {"tags": dict_tag, "fields": {"uptime_s": "%d" % utils.time_manager.uptime_s()}}
    )
    utils.mmts.upload_to_influx(
        credentials='nano_monitor'
    )  # 'peter_influx_com'   'nano_monitor'

    while utils.time_manager.need_to_wait(update_period_ms=10 * minute_ms):
        pass












