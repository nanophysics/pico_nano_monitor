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



class outage:
    def __init__(self, outage_ms = 0, outage_ongoing = False):
        self.outage_ms = outage_ms
        self.outage_ongoing = outage_ongoing
        self.uploaded = False

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

    def need_to_report(self):
        need_report =  self.outage_ms > 30
        return(need_report)

    def print(self):
        print('outage_ms: %d, outage_ongoing: %s' % (self.outage_ms, self.outage_ongoing))
        
        need_report =  self.outage_ms > 30
        return(need_report)

    def reset(self): # return true if worse
        self.outage_ms = 0
        self.outage_ongoing = False
        self.uploaded = False

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
    global outage_actual, outage_report, outage_upload
    meassurement_u16 = adc26.read_u16()
    if meassurement_u16 < 40000:
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

def upload():
    global last_upload_ms, outage_actual, outage_report, outage_upload, start_up_ms
    #print(f'upload to influx, time since start up {time.ticks_diff(time.ticks_ms(),start_up_ms):d}')
    outage_upload.update_if_worse(outage_report)
    utils.log.log(f"Outage {outage_upload.outage_ms:d} ms")
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
                    "powerOutage_s": "%0.3f"
                    % (float(outage_upload.outage_ms)/1000.0)
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

last_upload_ms = time.ticks_diff(time.ticks_ms(), 20000)
start_up_ms = time.ticks_ms()

MIN_MS = 60 * 1000
periodic_upload_without_outage_min = 10
# report periodic loop
def periodic_upload_loop(upload_success = True):
    global last_upload_ms, outage_actual, outage_report, outage_upload, start_up_ms
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
    
outage_actual = outage()
outage_report = outage()
outage_upload = outage()

ticks_start_ms = time.ticks_ms()

tim1 = machine.Timer(-1)
tim2 = machine.Timer(-1)
tim1.init(period=1, mode=tim1.PERIODIC, callback = isr_loop)
tim2.init(period=10, mode=tim1.PERIODIC, callback = periodic_upload_loop)#period in ms


if upload_to_influx:
    while True: # this loop ist just for fun and to be compatible with others
        time.sleep_ms(10)
        utils.time_manager.need_to_wait(update_period_ms=10 * minute_ms)
        #while utils.time_manager.need_to_wait(update_period_ms=10 * minute_ms):
        #    pass
        print(f'outage_report.outage_ms {outage_report.outage_ms:d} ms')


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

if True:
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
    time.sleep_ms(1000)