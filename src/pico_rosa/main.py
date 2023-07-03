"""
for debuging: delete file main.py on RP2. Execute main.py with Thonny from PC
for final use: put main.py on RP2 
"""

# hat gut funktioniert mit v1.19.1-992-g38e7b842c on 2023-03-23; Raspberry Pi Pico W with RP2040
# hat gut funktoiniert mit rp2-pico-w-20230615-unstable-v1.20.0-219-g47dc7d013_gut.uf2


import time
import machine
import utils
import random
import micropython
import _thread

micropython.alloc_emergency_exception_buf(100)

utils.wdt.enable()
utils.log.enable_oled()  # comment out if there is no oled

upload_to_influx = micropython.const(True) # if False just print, fast and reliable

if upload_to_influx:
    utils.wlan.start_wlan()
    utils.file_updater.update_if_local()


# for debuging
debug_pin_gp14 = machine.Pin(14, machine.Pin.OUT) #number is GPx
debug_pin_gp16 = machine.Pin(16, machine.Pin.OUT) #number is GPx
debug_pin_gp14.value(0)
debug_pin_gp16.value(0)

class Log_file:
    def __init__(self):
        self.filename = micropython.const('log_file.txt')
        self.enabled = False
        self._log_file = None
        self.outage_test_measured_ms = 0
    def enable(self):
        assert self._log_file == None
        self._log_file = open(self.filename, 'a') # a: append, w: write
        self.enabled = True
        self.log('Logfile started')
    def close(self):
        self._log_file.close()
        self.enabled = False
    def log(self, text = ''):
        line = f'uptime_s\t{utils.time_manager.uptime_s():0.3f}\t{text:s}'
        if self.enabled:
            self._log_file.write(line + '\n')
            self._log_file.flush()
        print(line)

log_file = Log_file()

class Outage:
    def __init__(self, outage_ms = 0, outage_ongoing = False, trace_array_len = 1):
        self.outage_ms = outage_ms
        self.outage_ongoing = outage_ongoing
        self.uploaded = False
        self.trace_array_len = trace_array_len
        self.trace_array = [0] * self.trace_array_len
        self.trace_n = 0
        self.do_record_array = True
        self.counter_temp_n = 0
        self.error_counter_n = 0

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

    def reset(self):
        self.outage_ms = 0
        self.outage_ongoing = False
        self.uploaded = False


trace_array_len = micropython.const(1000)
outage_actual = Outage( trace_array_len = trace_array_len )
outage_report = Outage()
outage_upload = Outage( trace_array_len = trace_array_len)

adc26 = machine.ADC(machine.Pin("GPIO28"))

baton = _thread.allocate_lock()

def thread_sample():
    interval_us = micropython.const(1000)
    next_time_us = time.ticks_us()
    while True:
        baton.acquire()
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
        debug_pin_gp14.value(0)
        baton.release()

        next_time_us = time.ticks_add(next_time_us, interval_us)
        to_sleep_us = time.ticks_diff(next_time_us, time.ticks_us())
        if to_sleep_us < 0 or to_sleep_us > interval_us:
            next_time_us =  time.ticks_us()
            to_sleep_us = 0
            outage_actual.error_counter_n += 1
        time.sleep_us(to_sleep_us)
                





minute_ms = micropython.const(60 * 1000)
hour_ms = micropython.const(60 * minute_ms)
utils.time_manager.set_period_restart_ms(
    time_restart_ms=6 * hour_ms + random.randrange(10 * minute_ms)
)  # will reset after this time



class Ssr_relais():
    def __init__(self):
        self._relais1 = machine.Pin(3, machine.Pin.OUT) #number is GPx
        self.on()
    
    def on(self):
        self._relais1.on()

    def off(self):
        self._relais1.off()
        
relais = Ssr_relais()


def upload():
    global last_upload_ms
    time.sleep_ms(10) # to get time after the outage on the trace
    baton.acquire()
    if outage_upload.uploaded: # upload was successfull last time
        if not outage_upload.worse(outage_report) and outage_upload.outage_ongoing == False:
            outage_report.reset()
            outage_upload.reset()
            baton.release()
            print('delete outage_upload as already uploaded')
            return
    outage_upload.update_if_worse(outage_report)
    outage_actual.do_record_array = False
    for i in range(outage_actual.trace_array_len):
        outage_upload.trace_array[i] = int( outage_actual.trace_array[ (i+outage_actual.trace_n+1) % outage_actual.trace_array_len] * 350 / 2**12 )
    for i in range(outage_actual.trace_array_len):
        outage_actual.trace_array[i] = None
    outage_actual.do_record_array = True
    baton.release()

    #print ('trace =', outage_upload.trace_array)

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

        #state = machine.disable_irq() #https://docs.micropython.org/en/latest/library/machine.html

        utils.mmts.upload_to_influx(credentials='peter_maerki_com')  # 'peter_influx_com' ,  'nano_monitor' , 'peter_maerki_com' 
        #machine.enable_irq(state) #https://docs.micropython.org/en/latest/library/machine.html

        outage_upload.uploaded = True # atomic
        last_upload_ms = time.ticks_ms()
        log_file.log(f'outage_test_measured_ms\t{log_file.outage_test_measured_ms:d}\toutage uploaded ms\t{outage_upload.outage_ms:d}\tongoing\t{outage_upload.outage_ongoing:b}')
    else: # just print 
        if True: #if upload_success: # if upload success
            print('uploaded success: ', end='')
            outage_upload.print()
            outage_upload.uploaded = True # atomic
            last_upload_ms = time.ticks_ms()
        else:
            outage_upload.reset() # was not successful, do upload later again
    #debug_pin_gp16.value(0)

last_upload_ms = time.ticks_diff(time.ticks_ms(), 20000)
start_up_ms = time.ticks_ms()

MIN_MS = micropython.const(60 * 1000)

periodic_upload_without_outage_min = micropython.const(10)


def upload_check(upload_success = True):
    #global last_upload_ms, outage_actual, outage_report, outage_upload, start_up_ms
    debug_pin_gp16.value(1)
    time.sleep_us(30)
    debug_pin_gp16.value(0)
    if not outage_report.need_to_report():
        if time.ticks_diff(time.ticks_ms(), last_upload_ms) > periodic_upload_without_outage_min * MIN_MS:
            print('Periodic upload even without an outage')
            print(last_upload_ms)
            upload()
        return
    if outage_report.outage_ongoing and outage_report.outage_ms < 2000: # outage is ongoing, do not upload before 2s
        return
    if time.ticks_diff(time.ticks_ms(), last_upload_ms) < 2000: #or outage_upload.outage_ongoing == False: # do not upload more often than every 10 seconds if outage ongoing
        return
    upload()


_thread.start_new_thread(thread_sample, ())

time.sleep_ms(50)



class Sceduler:
    def __init__(self):
        self.ticks_last_time_manager_ms = time.ticks_ms()
        self.ticks_last_time_manager_interval_ms = micropython.const(1000)
        self.ticks_last_upload_check_ms = time.ticks_ms()
        self.ticks_last_upload_check_interval_ms = micropython.const(50)
        self.ticks_last_log_print_ms = time.ticks_ms()
        self.ticks_last_log_print_interval_ms = micropython.const(4000)

    def sleep_ms(self, sleep_ms=0): # Use this instead of time.sleep in order to get things done!
        ticks_sleep_end_ms = time.ticks_add(time.ticks_ms(), sleep_ms)
        while time.ticks_diff(ticks_sleep_end_ms, time.ticks_ms()) > 0: 
            if time.ticks_diff(time.ticks_ms(), self.ticks_last_time_manager_ms) > 0:
                utils.time_manager.need_to_wait(update_period_ms=10 * minute_ms, wait_time_ms=50)
                self.ticks_last_time_manager_ms = time.ticks_add(time.ticks_ms(), self.ticks_last_time_manager_interval_ms)
                continue
            if time.ticks_diff(time.ticks_ms(), self.ticks_last_upload_check_ms) > 0:
                upload_check()
                self.ticks_last_upload_check_ms = time.ticks_add(time.ticks_ms(), self.ticks_last_upload_check_interval_ms)
                continue  
            if time.ticks_diff(time.ticks_ms(), self.ticks_last_log_print_ms) > 0:
                print(f'report {outage_report.outage_ms} ms, error: {outage_actual.error_counter_n}, uptime: {utils.time_manager.uptime_s_str(utils.time_manager.uptime_s())}')
                utils.log.log_oled(f"Outage {outage_report.outage_ms:d} ms")
                self.ticks_last_log_print_ms = time.ticks_add(time.ticks_ms(), self.ticks_last_log_print_interval_ms)
                continue
            time.sleep_us(500)

sceduler = Sceduler()

def generiere_outage(outage_ms=50):
    log_file.log(f'Es folgt ein outage von ca. ms\t{outage_ms:d}')
    log_file.outage_soll_ms = outage_ms
    log_file.outage_test_measured_ms = 0

    baton.acquire()
    start_ms = time.ticks_ms() # remainder: die ticks laufen auch nicht ganz zuverlaessig. Das habe ich bei fruehren projekten gemerkt. Muesste bei genauen Messungen vorgaengig gecheckt werden.
    relais.off()
    baton.release()

    sceduler.sleep_ms(sleep_ms = outage_ms) # Vorsicht: in dieser Zeit laeuft bei einem langen outage der Upload und der outage ist dann effektiv laenger.
    
    baton.acquire()
    relais.on()
    log_file.outage_test_measured_ms = time.ticks_diff(time.ticks_ms(), start_ms)
    baton.release()
    
def generiere_pause(pause_ms=1000):
    log_file.log(f'Es folgt eine Pause von\t{pause_ms:d}')
    sceduler.sleep_ms(sleep_ms = pause_ms)
    
while False:
    time.sleep_ms(1000)
    print(f'report {outage_report.outage_ms:d} on:{outage_report.outage_ongoing:d} upload  {outage_upload.outage_ms:d} on:{outage_upload.outage_ongoing:d}')



if False:  # random tester
    log_file.enable()
    sceduler.sleep_ms(sleep_ms = 5000)
    for i in range(1000):
        #outage_ms = random.randint(10, 3000)
        outage_ms = random.choice([10,12,15,20,25,30,50,80,100,200,300,500,800,1000,1500,2000,2200,2500,3000,5000,8000,10000])
        generiere_outage(outage_ms=outage_ms)
        sceduler.sleep_ms(sleep_ms = 25000)
    log_file.close()

if False:
    log_file.enable()
    sceduler.sleep_ms(sleep_ms = 5000)
    generiere_outage(outage_ms=3000)
    sceduler.sleep_ms(sleep_ms = 25000)
    log_file.close()


while True:
    sceduler.sleep_ms(sleep_ms = 100)
    #peter_scheduler_wait_ms(1000)
    #utils.time_manager.need_to_wait(update_period_ms=10 * minute_ms, wait_time_ms=50)
    #print(f'report {outage_report.outage_ms} ms, error: {outage_actual.error_counter_n}')
    #debug_pin_gp16.value(0)
    #upload_check()
    #debug_pin_gp16.value(1)
    #print(f'actual {outage_actual.outage_ms} ms, report {outage_report.outage_ms} ms, count {outage_actual.counter_temp_n} ')
    #print(f'report {outage_report.outage_ms} ms')
    #outage_actual.take_array_snapshot()
    #print(outage_actual.trace_array_snapshot)




''' Read:
https://docs.micropython.org/en/latest/library/micropython.html?highlight=schedule
https://docs.micropython.org/en/latest/reference/isr_rules.html#isr-rules

Ich messe mit KO: 
_thread.start_new_thread(thread_sample, ())
der thread wird durch einen micropython.schedule() beeinflusst. Darf daher keine micropython.schedule brauchen? ISR gehen auch nicht zusammen. Also beides nicht brauchen.

'''