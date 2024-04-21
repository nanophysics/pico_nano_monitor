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

anforderung_pin = machine.Pin("GPIO14", machine.Pin.IN)
zwangsladung_pin = machine.Pin("GPIO13", machine.Pin.IN)
utils.log.avoid_burnIn = True

board_name = utils.board.get_board_name()

anforderung_last = None
zwangsladung_last = None

while True:
    utils.board.set_led(value=1)
    dict_tag = {
        "user": "pmaerki",
        "quality": "testDeleteLater",
    }

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
