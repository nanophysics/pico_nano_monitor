
import time
import machine
import utils
import micropython
import simple_pid


#utils.wdt.enable()
utils.log.enable_oled() # comment out if there is no oled
utils.wlan.start_wlan()
#utils.file_updater.update_if_local()

utils.log.level( level_oled = 'info',  level_print = 'error')  # otherwise repl can not be used propperly

feuchte = 56.2

def scheduled_loop(k): # Scheduled callback
    dict_tag = {
        'room': 'C17',
        'setup': 'broker',
        'position': 'humifier',
        'user': 'pmaerki',
        'quality': 'testDeleteLater',
        }
    utils.mmts.append({
        'tags': dict_tag.copy(),
        'fields': {
            "temperature_C": 25.2,
            "humidity_pRH": "%0.2f" % 56.8,
        }})
    dict_tag.update({'position': 'stage'})
    utils.mmts.append({
        'tags': dict_tag.copy(),
        'fields': {
            "temperature_C": 21.2,
            "humidity_pRH": "%0.2f" % feuchte,
        }})
    utils.mmts.upload_to_influx(credentials = 'nano_monitor') # 'peter_influx_com'   'nano_monitor'
    

def isr_loop(k): # Hard IRQ
    micropython.schedule(scheduled_loop, 'Timer 1')
    
tim1 = machine.Timer(-1)
tim1.init(period=10000, mode=tim1.PERIODIC, callback=isr_loop)

