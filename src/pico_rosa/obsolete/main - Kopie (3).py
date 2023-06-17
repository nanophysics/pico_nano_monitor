"""
for debuging: delete file main.py on RP2. Execute main.py with Thonny from PC
for final use: put main.py on RP2 
"""

import time
import machine
import utils
import random
import micropython

micropython.alloc_emergency_exception_buf(100)

#utils.wdt.enable()
utils.log.enable_oled()  # comment out if there is no oled

upload_to_influx = True # if False just print, fast and reliable

if upload_to_influx:
    utils.wlan.start_wlan()
    utils.file_updater.update_if_local()

minute_ms = 60 * 1000
hour_ms = 60 * minute_ms
utils.time_manager.set_period_restart_ms(
    time_restart_ms=6 * hour_ms + random.randrange(10 * minute_ms)
)  # will reset after this time


adc26 = machine.ADC(machine.Pin(26))
debug_pin_gp14 = machine.Pin(14, machine.Pin.OUT) #number is GPx
debug_pin_gp15 = machine.Pin(15, machine.Pin.OUT) #number is GPx
debug_pin_gp14.value(0)
debug_pin_gp15.value(0)
class outage:
    def __init__(self, outage_ms = 0, outage_ongoing = False):
        self.outage_ms = outage_ms
        self.outage_ongoing = outage_ongoing
        self.uploaded = False
        self.trace_array_len = 500
        self.trace_array = [0] * self.trace_array_len
        self.trace_n = 0
        #self.trace_array_snapshot = [0] * self.trace_array_len
        self.do_record_array = True
        self.counter_temp_n = 0

    def worse(self, outage): # return true if worse
        worse = False
        if outage.outage_ms > self.outage_ms:
            worse = True
            return(worse)
        if outage.outage_ms == self.outage_ms:
            if outage.outage_ongoing == False and self.outage_ongoing == True: # outage ended
                worse = True
        return(worse)

    def update_if_worse(self, outage):
        if self.worse(outage):
            self.outage_ms = outage.outage_ms
            self.outage_ongoing = outage.outage_ongoing
            #self.trace_array = [x for x in outage.trace_array]
            #self.trace_n = outage.trace_n

    def need_to_report(self):
        need_report =  self.outage_ms > 30
        return(need_report)

    def print(self):
        print('outage_ms: %d, outage_ongoing: %s' % (self.outage_ms, self.outage_ongoing))
        
        need_report =  self.outage_ms > 30
        return(need_report)

    def reset(self):
        self.outage_ms = 0
        self.outage_ongoing = False
        self.uploaded = False
'''
    def take_array_snapshot(self):
        self.trace_array_snapshot = [x for x in self.trace_array]
'''

class Ssr_relais():
    def __init__(self):
        self._relais1 = machine.Pin(3, machine.Pin.OUT) #number is GPx
        self.on()
    
    def on(self):
        self._relais1.on()

    def off(self):
        self._relais1.off()
        
relais = Ssr_relais()

def isr_loop(k):
    #global outage_actual, outage_report, outage_upload
    debug_pin_gp14.value(1)
    meassurement_u16 = adc26.read_u16()  >> 4 # RP2040 has only 12 bit ad converter. 
    outage_actual.counter_temp_n += 1

    if outage_actual.do_record_array:
        outage_actual.trace_n = (outage_actual.trace_n + 1) % outage_actual.trace_array_len
        outage_actual.trace_array[outage_actual.trace_n] = meassurement_u16

    if meassurement_u16 < 2500:
        outage_actual.outage_ongoing = True
        outage_actual.outage_ms += 1
        outage_report.update_if_worse(outage_actual)
    else:
        outage_actual.outage_ongoing = False
        outage_report.update_if_worse(outage_actual)
        outage_actual.reset()
    if outage_upload.uploaded: # upload was successfull
        if outage_upload.worse(outage_report): # in between the report got worse, do upload again
            return
        if outage_upload.outage_ongoing == True: # still ongoing
            return
        outage_report.reset()
        outage_upload.reset()
    debug_pin_gp14.value(0)

def upload():
    debug_pin_gp15.value(1)
    #global last_upload_ms, outage_actual, outage_report, outage_upload, start_up_ms
    #print(f'upload to influx, time since start up {time.ticks_diff(time.ticks_ms(),start_up_ms):d}')
    outage_upload.update_if_worse(outage_report)
    #utils.log.log(f"Outage {outage_upload.outage_ms:d} ms")

    for k in range(50):
        time.sleep_ms(1) # for the trace, collect more to see recovered mains

    outage_actual.do_record_array = False
    for i in range(outage_actual.trace_array_len):
        outage_upload.trace_array[i] = int( outage_actual.trace_array[ (i+outage_actual.trace_n+1) % outage_actual.trace_array_len] * 350 / 2**12 )
    for i in range(outage_actual.trace_array_len):
        outage_actual.trace_array[i] = None
    outage_actual.do_record_array = True

    print ('trace =', outage_upload.trace_array)

    if upload_to_influx:
        dict_tag = {
            "room": "E9",
            "user": "pmaerki",
            "quality": "testDeleteLater",
        }
        utils.mmts.append(
            {
                "tags": dict_tag,
                "fields": {
                    "powerOutage_s": "%0.3f" % (float(outage_upload.outage_ms)/1000.0),
                },
            }
        )
        if outage_upload.need_to_report():
            utils.mmts.append(
                {
                    "tags": dict_tag,
                    "fields": {
                        "outage_trace_V": "\"%s\"" % ', '.join([str(a) for a in outage_upload.trace_array]),
                    },
                }
            )
        utils.mmts.append(
            {"tags": dict_tag, "fields": {"uptime_s": "%d" % utils.time_manager.uptime_s()}}
        )

        utils.mmts.upload_to_influx(
            credentials='nano_monitor'
        )  # 'peter_influx_com' ,  'nano_monitor'
        outage_upload.uploaded = True # atomic
        last_upload_ms = time.ticks_ms()
    else: # just print
        if True: #if upload_success: # if upload success
            print('uploaded success: ', end='')
            outage_upload.print()
            outage_upload.uploaded = True # atomic
            last_upload_ms = time.ticks_ms()
        else:
            outage_upload.reset() # was not successful, do upload later again
    debug_pin_gp15.value(0)

last_upload_ms = time.ticks_diff(time.ticks_ms(), 20000)
start_up_ms = time.ticks_ms()

MIN_MS = 60 * 1000

periodic_upload_without_outage_min = 10

# report periodic loop
def scheduled_periodic_upload_loop(upload_success = True):
    #global last_upload_ms, outage_actual, outage_report, outage_upload, start_up_ms
    #print('periodic_upload_loop')
    if not outage_report.need_to_report():
        if time.ticks_diff(time.ticks_ms(), last_upload_ms) > periodic_upload_without_outage_min * MIN_MS:
            print('Periodic upload even without an outage')
            upload()
        return
    if outage_report.outage_ongoing and outage_report.outage_ms < 2000: # outage is ongoing, do not upload before 2s
        return
    if time.ticks_diff(time.ticks_ms(), last_upload_ms) < 2000: #or outage_upload.outage_ongoing == False: # do not upload more often than every 10 seconds if outage ongoing
        return
    upload()

flag_do_upload = False

def isr_periodic_upload_loop(salami):
    global flag_do_upload
    #micropython.schedule(scheduled_periodic_upload_loop, 'hugo')
    flag_do_upload = True
    
outage_actual = outage()
outage_report = outage()
outage_upload = outage()

ticks_start_ms = time.ticks_ms()

tim1 = machine.Timer(-1)
tim2 = machine.Timer(-1)
tim1.init(period=1, mode=tim1.PERIODIC, callback = isr_loop)
tim2.init(period=30, mode=tim1.PERIODIC, callback = isr_periodic_upload_loop)#period in ms

def peter_scheduler_wait_ms(wait_time_ms=0):
    # this is my own scheduler as I had problems: ISR task did not get executed bevore a scheduled task was finished. Therefore I made my own scheduler and schedule from the main program.
    global flag_do_upload
    start_ms = time.ticks_ms()
    while True:
        if flag_do_upload:
            flag_do_upload = False
            scheduled_periodic_upload_loop()

        utils.time_manager.need_to_wait(update_period_ms=10 * minute_ms, do_blink_wait = False)

        if time.ticks_diff(time.ticks_ms(),start_ms) >= wait_time_ms:
            return

'''
if upload_to_influx:
    while True: # this loop ist just for fun and to be compatible with others
        time.sleep_ms(10)
        utils.time_manager.need_to_wait(update_period_ms=10 * minute_ms, do_blink_wait = False)
        #while utils.time_manager.need_to_wait(update_period_ms=10 * minute_ms):
        #    pass
        print(f'outage_report.outage_ms {outage_report.outage_ms:d} ms')
'''

def generiere_outage(outage_ms=50):
    global relais
    print(f'Es folgt ein outage von ca. {outage_ms:d}ms')
    relais.off()
    time.sleep_ms(outage_ms)
    relais.on()
    
def generiere_pause(pause_ms=1000):
    global relais
    print(f'Es folgt eine Pause von {pause_ms:d}ms')
    time.sleep_ms(pause_ms)
    
while False:
    time.sleep_ms(1000)
    print(f'report {outage_report.outage_ms:d} on:{outage_report.outage_ongoing:d} upload  {outage_upload.outage_ms:d} on:{outage_upload.outage_ongoing:d}')

if False:
    time.sleep_ms(1000)
    generiere_outage(outage_ms=100)
    generiere_pause(pause_ms=1000)
    generiere_outage(outage_ms=1000)
    generiere_pause(pause_ms=5000)
    generiere_outage(outage_ms=2500)
    generiere_pause(pause_ms=5000)
    generiere_outage(outage_ms=35)
    generiere_pause(pause_ms=5000)
    
while True:
    peter_scheduler_wait_ms(1000)

    #time.sleep_ms(1000)
    print(f'actual {outage_actual.outage_ms} ms, report {outage_report.outage_ms} ms, count {outage_actual.counter_temp_n} ')
    #outage_actual.take_array_snapshot()
    #print(outage_actual.trace_array_snapshot)

