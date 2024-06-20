"""
for debuging: delete file main.py on RP2. Execute main.py with Thonny from PC
for final use: put main.py on RP2
"""

import time
import machine
import utils
import random
import micropython
from machine import I2C, Pin

utils.wdt.enable()
utils.log.enable_oled()  # comment out if there is no oled
utils.wlan.start_wlan()
utils.file_updater.update_if_local()

minute_ms = 60 * 1000
hour_ms = 60 * minute_ms
utils.time_manager.set_period_restart_ms(
    time_restart_ms=24 * hour_ms + random.randrange(10 * minute_ms)
)  # will reset after this time

debug_fix_flow = False

utils.log.avoid_burnIn = True

fram_initialize_to_zero = False # in case you want to start from scratch

class FRAM:
    # Writes a number multiple times into the fram. 
    # Reading: if two identical numbers are found one assumes the value is ok. 
    def __init__(self):
        # Distrelec 301-39-068
        # VCC auf 3.3V  PCB Pin 36
        # GND auf GND
        # WP to gnd
        # SCL  PCB Pin 25  GP19 I2C1 SCL
        # SDA  PCB Pin 24  GP18 I2C1 SDA
        # A0, A1, A2 to gnd, Adress 0x50
        # 32 kB
        # MB85RC256V
        self.i2c = I2C(id=1, scl=Pin(19), sda=Pin(18),freq=100000)
        assert self.i2c.scan()[0] == 80 # Adress has to match
        self._redundant_numbers = 10
        self.bytes_per_integer = 50
        self._buf = bytearray(self.bytes_per_integer)
        self._max_adress_i = 32768
        self._MB85RC256V_adress = 0x50
        assert self._redundant_numbers * self.bytes_per_integer < self._max_adress_i

    def write(self, number: int):
        for i in range(self._redundant_numbers):
            adress_i = i * self.bytes_per_integer
            self.i2c.writeto_mem(self._MB85RC256V_adress, adress_i, number.to_bytes(self.bytes_per_integer,'big'), addrsize=16)
            time.sleep_ms(30) # wait a bit, in case of a brown out

    def read(self):
        last_i = None
        for i in range(self._redundant_numbers):
            adress_i = i * self.bytes_per_integer
            self.i2c.readfrom_mem_into(self._MB85RC256V_adress, adress_i, self._buf ,addrsize=16)
            time.sleep_ms(30) # wait a bit, in case of a brown out
            number_i = int.from_bytes(self._buf,'big')
            if number_i == last_i:
                return number_i
            if last_i != None:
                print (f'at adress_i {adress_i} the last_i {last_i} is not equal to number_i {number_i}, fram error?')
            last_i = number_i
        print('Corrupted FRAM, no two identical numbers found')
        self.write(number = 0) # reset
        assert False

    def test_force_defect(self):
        buf = bytearray(2)
        buf[0] = 3
        print('an defect is insertet into the fram')
        self.i2c.writeto_mem(self._MB85RC256V_adress,0, buf, addrsize=16)
        self.i2c.readfrom_mem_into(self._MB85RC256V_adress, 0, self._buf ,addrsize=16)
        print(self._buf)

fram = FRAM()

if fram_initialize_to_zero:
    fram.write(0)
    while True:
        print('fram set to zero')
        time.sleep_ms(5000)

class Flowmeter:
    def __init__(self):
        #self.adc = machine.ADC(machine.Pin(26))  # Number corresponds to GPx
        self.flow_ln_per_min = None
        self.flowsignal_V = None
        self.temperature_C = None
        self.total_ln_int = None # max int = 2**32, we assume we will stay below 2**32 liter
        self._total_ln_float = 0.0
        self.mittelwert_ln = None
        self.a_amount = 0

        self.last_tick_ms = time.ticks_ms()
        self._flow26 = machine.ADC(machine.Pin(26)) #number is GPx
        self._temp27 = machine.ADC(machine.Pin(27))
        self._AUFLOESUNG = micropython.const(2**16)
        self.error = None
        self.OK = micropython.const(0)
        self.OVERFLOW = micropython.const(1)
        self.WRONG_FLOW_DIRECTION = micropython.const(2)

    def measure(self):
        self._temp_csv()
        self._flow()
        if debug_fix_flow == True:
             self.flow_ln_per_min =1.0
        self._integrate()

    
    def _temp_csv(self):
        tempvalue = self._temp27.read_u16()
        temp_V = 3.0/self._AUFLOESUNG*tempvalue #converts the bits into voltage
        csvdata_temp = []
        delim = ','
        
        with open('csv_SMF3100_Temperaturliste.csv','r') as file: #opens the csv file
            for line in file:
                csvdata_temp.append(line.rstrip('\n').rstrip('\r').split(delim)) #puts value in array
        csvdata_temp.pop(0) #removes first (position 0) values, here C and Voltage

        for i in range(len(csvdata_temp)):
            csv_temp_V=float(csvdata_temp[i][1]) #converts string into float
            if csv_temp_V < temp_V: #if value of csv is lower than temp than use that number and the one before, then break out of loop
                temp_C_f = float(csvdata_temp[i][0]) #first temperature value, lower than meassured
                temp_V_f = float(csvdata_temp[i][1]) #first voltage value, lower than meassured
                temp_C_s = float(csvdata_temp[i-1][0]) #second temperature value, higher than meassured
                temp_V_s = float(csvdata_temp[i-1][0]) #second voltage value, higher than meassured           
                break

        self.temperature_C = (((temp_C_s-temp_C_f)/(temp_V_s-temp_V_f))*(temp_V)*(temp_V-temp_V_f)+temp_C_f) #interpolation der Temperatur
        #(y=((yo*(x1-x)+(y1*(x-xo))/(x1-xo)
        print("temp_C",self.temperature_C)
        if self.temperature_C == None:
            utils.reset_after_delay()    

    def _flow(self):
        global flow_lnmin
        #global te_ln
        flowvalue = self._flow26.read_u16()
        self.flowsignal_V = 3.0/self._AUFLOESUNG*flowvalue #converts the bits into voltage
        if self.flowsignal_V == None:
            utils.reset_after_delay()             

        xnullmin_V = 0.6 #under 0.6 the Flow is backwards
        xnull_V = 0.691 #start of 0 Flow
        xmax_V = 1.54 #from 1.5V on up the values, aren't calibrated anymore
        
        self.flow_ln_per_min = 0.0
        self.error = self.OK

        if xnull_V <= self.flowsignal_V <= xmax_V :
            flow_lnmin = -934.26351 * self.flowsignal_V + 1282.96211 * self.flowsignal_V**2 + -697.52901 * self.flowsignal_V**3 + 139.81601 * self.flowsignal_V**4 + 231.25960 #polynom from measurements
            self.flow_ln_per_min = round(flow_lnmin)
            flow_lnmin = f'{self.flow_ln_per_min} ln/min'
            #te_ln = f'Temp: {self.temperature_C:0.2} C'
            return
        if xnullmin_V > self.flowsignal_V:       
            #flow_lnmin = 'Error'
            #te_ln = 'flowdirection'
            self.error = self.WRONG_FLOW_DIRECTION
            if self.error == None:
                utils.reset_after_delay() 
            return
        if xmax_V < self.flowsignal_V :
            #flow_lnmin = 'Error'
            #te_ln = 'not calibrated'
            self.error = self.OVERFLOW
            if self.error == None:
                utils.reset_after_delay()
            self.flow_ln_per_min = 74.0
            return
        # self.mittelwert_ln += self.flow_ln_per_min #todo
        # self.a_amount += 1

        #print(te_ln)
        #print("Flow Signal:",'\t',flowvalue)
        #print("flow_V:",'\t',flow_V)
        #print("Durchfluss ",'\t',flow_lnmin)
    
    def _integrate(self):
        if self.total_ln_int == None: # just startet
            self.total_ln_int = fram.read()
        # if self.total_ln_int == None:
        #     utils.reset_after_delay()   
        ticks_now_ms = time.ticks_ms()
        volume_ln = self.flow_ln_per_min * time.ticks_diff(ticks_now_ms, self.last_tick_ms)/(1000.0*60.0)
        self.last_tick_ms = ticks_now_ms
        self._total_ln_float += volume_ln
        _total_ln_int = int(self._total_ln_float)
        if _total_ln_int >= 1:
            self.total_ln_int += _total_ln_int
            fram.write(self.total_ln_int)
            self._total_ln_float -= float(_total_ln_int)
        print (self._total_ln_float , self.total_ln_int)



flowmeter = Flowmeter()

while True:
    flowmeter.measure()
    utils.board.set_led(value=1)
    dict_tag = {
        "room": "C15",
        "setup": "emma",
        "user": "hannav",
        "position": 'He-Flowmeter',
        "quality": "testDeleteLater",
    }

    utils.mmts.append(
        {"tags": dict_tag, "fields": {"temperature_C": flowmeter.temperature_C}}
    )
    utils.mmts.append(
        {"tags": dict_tag, "fields": {"flow_ln_per_min": flowmeter.flow_ln_per_min}}
    )
    utils.mmts.append(
        {"tags": dict_tag, "fields": {"total_ln": flowmeter.total_ln_int}}
    )
    utils.mmts.append(
        {"tags": dict_tag, "fields": {"uptime_s": "%d" % utils.time_manager.uptime_s()}}
    )

    utils.mmts.upload_to_influx(
        credentials="nano_monitor"
    )  # 'peter_influx_com' ,  'nano_monitor'

    while utils.time_manager.need_to_wait(update_period_ms=5 * minute_ms):
        flowmeter.measure()
        utils.log.log_oled(f"flow: {flowmeter.flow_ln_per_min:2.0f} ln/min")
        #utils.log.log("uptime ", utils.time_manager.uptime_s_str(utils.time_manager.uptime_s())
        error_msg_ovewrflow1 = f"Overflow!"
        error_msg_ovewrflow2 = f"flowsig: {flowmeter.flowsignal_V:1.2f} V"
        error_msg_WRONG_FLOW_DIRECTION1 = f"Flow direction!"
        error_msg_WRONG_FLOW_DIRECTION2 = f"flowsig: {flowmeter.flowsignal_V:1.2f} V"

        if flowmeter.error != flowmeter.OK:
            if flowmeter.error == flowmeter.OVERFLOW:
                utils.log.log_oled(error_msg_ovewrflow1)
                utils.log.log_oled(error_msg_ovewrflow2)
            if flowmeter.error == flowmeter.WRONG_FLOW_DIRECTION:
                utils.log.log_oled(error_msg_WRONG_FLOW_DIRECTION1)
                utils.log.log_oled(error_msg_WRONG_FLOW_DIRECTION2)
                

        
        



