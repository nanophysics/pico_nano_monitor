'''
for debuging: delete file main.py on RP2. Execute main.py with Thonny from PC
for final use: put main.py on RP2
'''
import time
import machine
import utils
import config
import random

import micropython
micropython.alloc_emergency_exception_buf(100)

utils.wdt.enable()
utils.log.enable_oled() # comment out if there is no oled
utils.wlan.start_wlan()
utils.file_updater.update_if_local()

minute_ms = 60*1000; hour_ms = 60*minute_ms
utils.time_manager.set_period_restart_ms(time_restart_ms =  24 * hour_ms + random.randrange(10*minute_ms)) # will reset after this time 

measurement_counter = 0

from onewire import OneWire
from ds18x20 import DS18X20

msg = f'config.py has no entry for \'{utils.board.get_board_name():s}\'. Complement this file.' 
pico_tags = config.pico_tags.get(utils.board.get_board_name())
assert pico_tags != None, msg

class Vibration:
    def __init__(self):
        self._sig_counter = 0
        self._sig_integrator = 0
        self._sig_abs_difference = 0
        self._difference_last = 0
        self._sig_peak = 0
        self._sig_average = 0.0
        self._sig_sig_measure = 0
        self._sig_ref_measure = 0
        self._vib_sig = machine.ADC(26)
        self._vib_ref = machine.ADC(27)
        self._doReset = False
        self._listlength = 5 # odd number
        self._sig_liste = [None]*self._listlength
        self._temp = 0
        
    def process_isr(self, k):
        if self._doReset:
            self._sig_counter = 0
            self._sig_integrator = 0
            self._sig_abs_difference = 0
            self._sig_peak = 0
            self._sig_average = 0.0
            self._doReset = False
        self._sig_counter += 1
        for i in range(self._listlength): # measure multiple times
            self._sig_sig_measure = self._vib_sig.read_u16()//16 # the RP Pico ADC has only 12 bit
            self._sig_ref_measure = self._vib_ref.read_u16()//16
            self._sig_liste[i] = self._sig_sig_measure - self._sig_ref_measure
        self._temp = sorted(self._sig_liste)[self._listlength//2]
        self._sig_abs_difference = abs(self._temp - self._difference_last) # select the median, spikes will be removed this way
        self._difference_last = self._temp # only take the difference to the last measurement into account, this way DC offset of the Amplifier will be removed
        expected_reference = 2250
        assert self._sig_ref_measure < expected_reference+1000 and self._sig_ref_measure > expected_reference-1000  # Test Reference and therefore circuit
        self._sig_integrator += self._sig_abs_difference
        self._sig_peak = max(self._sig_peak, self._sig_abs_difference)
        self._sig_average = float(self._sig_integrator) / float(self._sig_counter)

    def getPeakAverage(self): # value between 0 and 1, peak since lasst reset, arbitrary unit
        sig_peak_float = min(float(self._sig_peak)/2**11, 1.0)
        sig_average_float = min(float(self._sig_average)/2**11, 1.0)
        self._doReset = True
        return sig_peak_float, sig_average_float

if pico_tags.get('vibration'):
    tim1 = machine.Timer(-1)
    vibration = Vibration()
    tim1.init(period=1, mode=tim1.PERIODIC, callback=vibration.process_isr)

class DS18b20Tags:
    def __init__(self, id_tags, pin='GPIO1'):
        self._id_tags = id_tags
        self._ds = ds = DS18X20(OneWire(machine.Pin(pin))) # pin corresponds to GPx
        self.sensors = ds.scan()
        if self.sensors:
            self._ds.convert_temp() # after power on reset the value is wrong. Therefore measure here once.
            time.sleep_ms(900)  # mandatory pause to collect results, datasheet max 750 ms
            for s in self.sensors:
                utils.log.log('DS18b20 scanned sensor: \'' + ''.join('%02X' % i for i in iter(s)) + '\'')
    
    def tags(self, sensor):
        return self._id_tags.get(''.join('%02X' % i for i in iter(sensor)))

    def do_measure(self):
        if self.sensors:
            self._ds.convert_temp()
            time.sleep_ms(750+150)     # mandatory pause to collect results, datasheet max 750 ms

    def measure_influx(self, sensor):
        """
        Returns temperature as string ready to send to influxdb
        """
        temperatureC = self._ds.read_temp(sensor)
        utils.log.log('%0.2f C' % temperatureC)
        return "%0.2f" % temperatureC

DS18B20_id_tags = pico_tags.get('DS18B20_id_tags')

dst = DS18b20Tags(id_tags=DS18B20_id_tags, pin='GPIO1')


while True:
    utils.board.set_led(value = 1)
    dst.do_measure()
    if pico_tags.get('vibration'):
        sig_peak_float, sig_average_float = vibration.getPeakAverage()
        #print('sig %d, ref %d, diff %d, peak %d, average %0.2f, counter %d' %  (vibration._sig_sig_measure, vibration._sig_ref_measure,vibration._sig_abs_difference,vibration._sig_peak,vibration._sig_average, vibration._sig_counter))
        utils.log.log(f'vib peak {sig_peak_float:.4f}')
        utils.log.log(f'vib aver {sig_average_float:.4f}')
    dict_tag = pico_tags.get('general')
    for sensor in dst.sensors:
        DS_dict = dst.tags(sensor)
        DS_dict.update(dict_tag)
        utils.mmts.append({
            'tags': dict_tag,
            'fields': {
                "temperature_C": dst.measure_influx(sensor)
            }})
    if measurement_counter == 0 or not pico_tags.get('vibration'): # vibration depends on measurement duration. Skip first measurement.
        pass
    else:
        utils.mmts.append({
            'tags': dict_tag,
            'fields': {
                'vibration_peak_AU': "%0.4f" % sig_peak_float,
                #'vibration_average_AU': "%0.4f" % sig_average_float was not useful
            }})
    utils.mmts.append({
        'tags': dict_tag,
        'fields': {
            "uptime_s": "%d" % utils.time_manager.uptime_s()
        }})
    measurement_counter += 1
    #print(utils.mmts.measurements)
    utils.mmts.upload_to_influx(credentials = 'peter_influx_com') # 'peter_influx_com'   'nano_monitor'
    
    while utils.time_manager.need_to_wait(update_period_ms = 10 * minute_ms):
        pass

