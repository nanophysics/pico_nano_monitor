"""
for debuging: delete file main.py on RP2. Execute main.py with Thonny from PC
for final use: put main.py on RP2
"""

enable_beeper = True
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
    time_restart_ms=6 * hour_ms + random.randrange(10 * minute_ms)
)  # will reset after this time

from onewire import OneWire
from ds18x20 import DS18X20

beeper_pin = machine.Pin("GPIO16", machine.Pin.OUT, value=0)
#beeper_pin.value(0)
beeper_pwm = machine.PWM(beeper_pin)
beeper_pwm.freq(8)
beeper_pwm.duty_u16(int(0)) # 0...65535, bei 0: aus

utils.log.avoid_burnIn = True

class DS18b20Tags:
    def __init__(self, id_tags, pin="GPIO1"):
        self._id_tags = id_tags
        self._ds = ds = DS18X20(OneWire(machine.Pin(pin)))  # pin corresponds to GPx
        self.sensors = ds.scan()
        self._ds.convert_temp()  # after power on reset the value is wrong. Therefore measure here once.
        time.sleep_ms(900)  # mandatory pause to collect results, datasheet max 750 ms
        for s in self.sensors:
            utils.log.log(
                "DS18b20 scanned sensor: '" + "".join("%02X" % i for i in iter(s)) + "'"
            )

    def tags(self, sensor):
        return self._id_tags.get("".join("%02X" % i for i in iter(sensor)))

    def do_measure(self):
        self._ds.convert_temp()
        time.sleep_ms(
            750 + 150
        )  # mandatory pause to collect results, datasheet max 750 ms

    def measure_influx(self, sensor):
        """
        Returns temperature as string ready to send to influxdb
        """
        temperatureC = self._ds.read_temp(sensor)
        utils.log.log("%0.2f C" % temperatureC)
        return "%0.2f" % temperatureC


DS18B20_id_tags = {
    "28FD17B50E0000EF": {"position": "vacuumpump_gas_handling", "setup": "bertram"},
    "28250BB50E0000D7": {"position": "box_temperature", "setup": "bertram"},
}
dst = DS18b20Tags(id_tags=DS18B20_id_tags, pin="GPIO1")


class Adc_5V_GP0:
    def __init__(self):
        self.adc = machine.ADC(machine.Pin(26))  # Number corresponds to GPx

    def voltage(self, average_n=1):
        # a single measurement takes about 2 us
        # @ average = 1000 it takes about 14ms (measured)
        uref_V = 3.0  # when using an external LT4040 3V reference
        R31 = 3900.0
        R32 = 22000.0
        R3p = 1.0 / (1.0 / R31 + 1.0 / R32)
        R5 = 2200.0
        fs_V = (R5 + R3p) / R3p * uref_V
        value_n = 0
        for i in range(average_n):
            value_n += self.adc.read_u16()
        return float(value_n) / average_n / 2 ** 16 * fs_V


class Pressure_15_psi_sensor_ali:
    def __init__(self):
        self.adc_5V_GP0 = Adc_5V_GP0()
        self.overload = True

    def get_pressure_pa(self, average_n=1000):
        voltage_V = self.adc_5V_GP0.voltage(average_n=average_n)
        # Drucksensor relativ von Alie XIDIBEI Official Store 15 psi, 103421 Pa
        pa_per_psi = (
            6894.75729  # https://www.unitconverters.net/pressure/psi-to-pascal.htm
        )
        #p1_pa = -14.5 * pa_per_psi
        #p2_pa = 30.0 * pa_per_psi
        p1_pa = 0.0
        p2_pa = 15.0 * pa_per_psi
        u1_V = 0.5
        u2_V = 4.5
        self.overload = voltage_V < u1_V or voltage_V > u2_V
        pressure_Pa = (p2_pa - p1_pa) / (u2_V - u1_V) * (voltage_V - u1_V)
        utils.log.log("%.3f V" % voltage_V)
        utils.log.log("%d Pa abs" % pressure_Pa)
        return pressure_Pa

    def get_overload(self):
        return self.overload


pressure_15_psi_abs_sensor_ali = Pressure_15_psi_sensor_ali()

while True:
    utils.board.set_led(value=1)
    dst.do_measure()
    dict_tag = {
        "room": "C18",
        "setup": "bertram",
        "user": "pmaerki",
        "quality": "testDeleteLater",
    }
    dict_tag_pressure = {
        "room": "C18",
        "setup": "bertram",
        "user": "pmaerki",
        "quality": "testDeleteLater",
        "position": "vacuumpump_gas_handling",
    }
    for sensor in dst.sensors:
        DS_dict = dst.tags(sensor)
        DS_dict.update(dict_tag)
        utils.mmts.append(
            #{"tags": dict_tag, "fields": {"temperature_C": dst.measure_influx(sensor)}}
            {"tags": DS_dict, "fields": {"temperature_C": dst.measure_influx(sensor)}}
        )
    utils.mmts.append(
        {
            "tags": dict_tag_pressure,
            "fields": {
                "pressure_Pa_abs": "%0.2f"
                % pressure_15_psi_abs_sensor_ali.get_pressure_pa(average_n=1000)
            },
        }
    )
    utils.mmts.append(
        {"tags": dict_tag, "fields": {"uptime_s": "%d" % utils.time_manager.uptime_s()}}
    )

    utils.mmts.upload_to_influx(
        credentials="nano_monitor"
    )  # 'peter_influx_com' ,  'nano_monitor'

    next_pressure_beep_ms = time.ticks_ms()
    while utils.time_manager.need_to_wait(update_period_ms=10 * minute_ms):
        if time.ticks_diff(next_pressure_beep_ms, time.ticks_ms()) < 0:
            next_pressure_beep_ms = time.ticks_add(next_pressure_beep_ms, 5000)
            pressure_Pa = pressure_15_psi_abs_sensor_ali.get_pressure_pa(average_n=1000)
            ambient_Pa = 100000.0
            upper_limit_Pa = ambient_Pa - 10000.0 # When pump is powered off the pressure will go to ambient pressure
            lower_limit_Pa = 30000.0 # When sample is on holder and vacuum is switched on the pressure should go below this value
            pump_switched_off = pressure_Pa > upper_limit_Pa
            pressure_ok = pressure_Pa < lower_limit_Pa
            if pump_switched_off:
                #utils.log.log("%d Pa!" % pressure_Pa)
                utils.log.log("Ambient")
                utils.log.log(" pressure?")
                utils.log.log("Pump seams to")
                utils.log.log(" be powered off")
            if pressure_ok:
                #utils.log.log("%d Pa!" % pressure_Pa)
                utils.log.log("Pressure ok")
                utils.log.log("Low enough")
            if (not pump_switched_off) and (not pressure_ok):
                #utils.log.log("%d Pa!" % pressure_Pa)
                utils.log.log("Sample ")
                utils.log.log(" on holder?")
                utils.log.log("You")
                utils.log.log(" loose Argon!")
                utils.log.log("Switch vacuum")
                utils.log.log(" off!")
                if enable_beeper:
                    beeper_pwm.duty_u16(int(65535*0.3)) # beeping
            else:
                beeper_pwm.duty_u16(int(0)) # 0: no beeping
        pass
