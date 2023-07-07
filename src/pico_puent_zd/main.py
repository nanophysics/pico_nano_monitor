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

Ventile_Offen_pin = machine.Pin("GPIO22", machine.Pin.IN)

class Adc_GP26:
    def __init__(self):
        self.adc = machine.ADC(machine.Pin(26))  # Number corresponds to GPx

    def voltage(self, average_n=1):
        # a single measurement takes about 2 us
        # @ average = 1000 it takes about 14ms (measured)
        uref_V = 3.0  # when using an external LT4040 3V reference
        Runten = 20000.0
        Roben = 150000.0
        Ifs = uref_V / Runten
        fs_V = (Runten + Roben) * Ifs
        korrekturfaktor = 1.00306
        value_n = 0
        for i in range(average_n):
            value_n += self.adc.read_u16()
        return float(value_n) / average_n / 2 ** 16 * fs_V * korrekturfaktor

adc_V = Adc_GP26()

board_name = utils.board.get_board_name()

voltage_V = None
house_i = None
house_i_last = None
house_i_change = True

def messen():
    global voltage_V, house_i, house_i_last, house_i_change
    time.sleep_ms(100)
    voltage_V = adc_V.voltage(average_n = 10000)
    voltage_i = int(voltage_V+0.5)
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
    assert house_i != None
    if house_i != house_i_last:
        house_i_change = True
        house_i_last = house_i

ventile_offen_last = None

while True:
    utils.board.set_led(value=1)
    messen()
    dict_tag = {
        "user": "pmaerki",
        "quality": "testDeleteLater",
    }
    utils.mmts.append(
        {
            "tags": dict_tag,
            "fields": {
                "voltage_V": "%.3f"
                % voltage_V
            },
        }
    )
    if house_i != 0 or house_i_change is True:
        utils.mmts.append(
            {
                "tags": dict_tag,
                "fields": {
                    "number_i": "%d"
                    % house_i
                },
            }
        )
    utils.mmts.append(
        {
            "tags": dict_tag,
            "fields": {
                "binary_state": "%i"     
                % Ventile_Offen_pin.value()
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



    while utils.time_manager.need_to_wait(update_period_ms=60 * minute_ms) and not house_i_change: # if house_i_change, it will upload imediatly
        messen()
        if house_i != 0:
            utils.log.log(f'{voltage_V:4.1f} V: Haus {house_i:d}')
        else:
            utils.log.log(f'{voltage_V:4.1f} V: Haus --')
        ventile_offen = Ventile_Offen_pin.value()
        if ventile_offen_last != ventile_offen:
            ventile_offen_last = ventile_offen
            break
