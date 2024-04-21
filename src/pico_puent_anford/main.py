"""
for debuging: delete file main.py on RP2. Execute main.py with Thonny from PC
for final use: put main.py on RP2
"""

import time
import machine
import utils
import random

utils.wdt.enable()
utils.log.enable_oled()  # comment out if there is no oled
utils.wlan.start_wlan()
utils.file_updater.update_if_local()

minute_ms = 60 * 1000
hour_ms = 60 * minute_ms
utils.time_manager.set_period_restart_ms(
    time_restart_ms=6 * hour_ms + random.randrange(5 * minute_ms)
)  # will reset after this time

anforderung_pin = machine.Pin("GPIO14", machine.Pin.IN)
zwangsladung_pin = machine.Pin("GPIO13", machine.Pin.IN)


board_name = utils.board.get_board_name()

voltage_V = None
house_i = None
house_i_last = None
house_i_change = True

def messen():
    global voltage_V, house_i, house_i_last, house_i_change
    time.sleep_ms(100)
    #voltage_V = adc_V.voltage(average_n = 10000)
    #voltage_i = int(voltage_V+0.5)
    house_i = None
    if board_name == 'pico_puent':
        house_i = voltage_i-3
        if house_i > 15: 
            house_i = 0
        if house_i < 1: 
            house_i = 0
    if board_name == 'pico_bochs':
        house_i = voltage_i+12
        if house_i > 26: 
            house_i = 0
        if house_i < 16: 
            house_i = 0
    #assert house_i != None
    #if house_i != house_i_last:
    #    house_i_change = True
    #    house_i_last = house_i

anforderung_last = None
zwangsladung_last = None

while True:
    utils.board.set_led(value=1)
    messen()
    dict_tag = {
        "user": "pmaerki",
        "quality": "testDeleteLater",
    }
    #utils.mmts.append(
    #    {
    #        "tags": dict_tag,
    #        "fields": {
    #            "voltage_V": "%.3f"
    #            % voltage_V
    #        },
    #    }
    #)

    utils.mmts.append(
        {
            "tags": dict_tag,
            "fields": {
                "anforderung": "%i"     
                % anforderung_pin.value()
            },
        }
    )
    utils.mmts.append(
        {
            "tags": dict_tag,
            "fields": {
                "zwangsladung": "%i"     
                % zwangsladung_pin.value()
            },
        }
    )
    utils.mmts.append(
        {"tags": dict_tag, "fields": {"uptime_s": "%d" % utils.time_manager.uptime_s()}}
    )

    utils.mmts.upload_to_influx(
        credentials='peter_maerki_com'
    )  # 'peter_influx_com' ,  'nano_monitor'

    house_i_change = False



    while utils.time_manager.need_to_wait(update_period_ms=1 * minute_ms) and not house_i_change: # if house_i_change, it will upload imediatly
        messen()
        anforderung = anforderung_pin.value()
        if anforderung_last != anforderung:
            anforderung_last = anforderung
            break
        zwangsladung = zwangsladung_pin.value()
        if zwangsladung_last != zwangsladung:
            zwangsladung_last = zwangsladung
            break
