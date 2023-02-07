# 2023 Peter Maerki
# Common functions for RP2 Pico w baords.

import rp2
import network
import secrets
import time
import machine
import urequests
import uhashlib
import gc
import oled_1_3
import influxdb_structure
import neopixel

gc.enable()


class Wlan:
    def __init__(self):
        pass

    def start_wlan(self, credentials="default"):
        wdt.feed()
        board.set_led(value=True, colour=BLUE)
        log.log("ETHZ 2023")
        log.log("pico_nano_monitor")
        log.log(" -> ", board.get_board_name())
        rp2.country("CH")
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.wlan.config(pm=0xA11140)  # Diable powersave mode
        self.status_dict = {
            "0": "CYW43_LINK_DOWN (0): Es besteht keine WLAN-Verbindung.",
            "1": "CYW43_LINK_JOIN (1): Verbindungsaufbau-Versuch, noch nicht abgeschlossen.",
            "2": "CYW43_LINK_NOIP (2): Verbindungsaufbau war erfolgreich, IP-Konfiguration fehlt noch.",
            "3": "CYW43_LINK_UP (3): Der Verbindungsaufbau war erfolgreich.",
            "-1": "CYW43_LINK_FAIL (-1): Verbindungsaufbau abgebrochen.",
            "-2": "CYW43_LINK_NONET (-2): Verbindungsaufbau abgebrochen, WLAN (SSID) nicht gefunden.",
            "-3": "CYW43_LINK_BADAUTH (-3): Verbindungsaufbau abgebrochen, Authentifizierung fehlgeschlagen. Vemutlich WLAN-Passwort falsch.",
        }
        connected = False
        for secret in secrets.wlan_credentials[credentials]:
            status_old = None
            self.wlan.connect(secret["SSID"], secret["PASSWORD"])
            for max_wait in range(20):
                wdt.feed()
                time.sleep_ms(500)
                status = self.wlan.status()
                if status != status_old:
                    # print("WLAN: SSID:", secret["SSID"], self.status_dict.get("%s" % status))
                    log.log("SSID:", secret["SSID"], ":s%s" % status)
                status_old = status
                if status < 0 or status >= 3:
                    break
            if status == 3:
                ifconfig = self.wlan.ifconfig()
                # print("WLAN: SSID:", secret["SSID"],' connected to ip = ' + ifconfig[0])
                log.log(ifconfig[0])
                connected = True
                break
        board.set_led(value=False)
        if False:
            result = urequests.get("https://ethz.ch/de.html")  #'https://www.google.com'
            print("Good result ist 200 and I got: %s" % result.status_code)
        if False:
            result = urequests.get(
                "https://gitlab.phys.ethz.ch/pmaerki/pico_nano_monitor/-/raw/main/test.py"
            )  #'https://www.google.com'
            print(result.text)
        if not connected:
            log.log("Could not establish a wlan connection")
            reset_after_delay(error=True)


wlan = Wlan()

TRACE = 0
DEBUG = 1
INFO = 2
WARN = 3
ERROR = 4
FATAL = 5


class Log:
    def __init__(self):
        self._print = False
        self.level_oled = INFO
        self.level_print = TRACE
        self._oled = None

    def log(self, *string, level=INFO):
        self.log_print(*string, level=level)
        self.log_oled(*string, level=level)

    def log_print(self, *string, level=INFO):
        if level >= self.level_print:
            print(*string)

    def log_oled(self, *string, level=INFO):
        if self._oled:
            if level >= self.level_oled:
                self._oled.printe("".join(map(str, string)))

    def oled_progress_bar(self, progress=0.5):  # progress bar 0.0 ... 1.0
        if self._oled:
            self._oled.progress(progress)

    def enable_oled(self, level_oled=INFO, level_print=TRACE):
        self._oled = oled_1_3.OLED()
        key0.enable()
        key1.enable()


class Key:
    def __init__(self, GPx):
        self._key = False
        self._gpx = GPx

    def enable(self):
        def _key_isr(k):
            self._key = True

        key = machine.Pin(self._gpx, machine.Pin.IN, machine.Pin.PULL_UP)
        key.irq(trigger=machine.Pin.IRQ_FALLING, handler=_key_isr)

    def get_key(self):
        value = self._key
        self._key = False
        return value


key0 = Key(GPx=15)
key1 = Key(GPx=17)
log = Log()

GITHUB_URL = "https://raw.githubusercontent.com/nanophysics/pico_nano_monitor/main/"  # use a / at the end


class Ota_git:
    def __init__(self):
        self._headers = {}

    def _get_remote_file(self, url="", remote_folder="", file=""):
        wdt.feed()
        _url = url + remote_folder + file
        payload = urequests.get(_url, headers=self._headers)
        if payload.status_code != 200:
            log.log(
                f"_get_remote_file got status_code of {payload.status_code}, _url: {_url}",
                level=FATAL,
            )
            reset_after_delay()
        if len(payload.text) == 0:  # seams to be wrong
            log.log(
                f"_get_remote_file len of payload.text was 0, _url: {_url}", level=FATAL
            )
            reset_after_delay(error=True)
        return payload.text

    def _get_local_file(self, file=""):
        wdt.feed()
        try:
            f = open(file, "r")
            text = f.read()
            f.close()
        except:
            log.log(
                f"could not open local file: {file}", level=TRACE
            )  # could be the file does not exist
            return ""
        if len(text) == 0:  # seams to be wrong
            return ""
        return text

    def update_file_if_changed(self, url="", file="", remote_folder=""):
        str_git = self._get_remote_file(url=url, remote_folder=remote_folder, file=file)
        gc.collect()
        str_local = self._get_local_file(file=file)
        if str_local != str_git:
            wdt.feed()
            f = open(file, "w")
            f.write(str_git)
            f.close
            log.log(f"new:{file}", level=INFO)
            return 1
        else:
            log.log(f"ok :{file}", level=INFO)
            return 0

    def _compare_strings(
        self, str_local, str_git
    ):  # in case we search for strange effects
        str_local = "".join(c for c in str_local if c != "\r")
        str_local_length = len(str_local)
        str_git_length = len(str_git)
        max_length = max(str_local_length, str_git_length)
        local = None
        remote = None
        counter = 0
        counter_line = 0
        counter_char = 0
        for element in range(0, max_length - 1):
            if element < str_local_length:
                counter_char += 1
                local = str_local[element]
                if local == "\n":
                    counter_line += 1
                    counter_char = 0
                local = repr(local)
            if element < str_git_length:
                remote = repr(str_git[element])
            if local != remote:
                print(
                    f"Line: {counter_line}, character nr. {counter_char} local: {local} remote: {remote}"
                )
                counter += 1
                if counter > 40:
                    break
        print(str_local[0:400])
        print(str_git[0:400])


ota_git = Ota_git()


class FileUpdater:
    def __init__(self):
        pass

    def update_if_local(self):
        gc.collect()
        if board.main_is_local():
            log.log("new files?", level=INFO)
            files = ["utils.py", "uniq_id_names.py", "oled_1_3.py"]
            updates = 0
            for file in files:
                updates += ota_git.update_file_if_changed(url=GITHUB_URL, file=file)
            dict = board.get_board_dict()
            add_files = dict.get(
                "src_files"
            )  # additional files, typically in a subfolder on git
            remote_folder = dict.get("src_folder")
            for file in add_files:
                updates += ota_git.update_file_if_changed(
                    url=GITHUB_URL, file=file, remote_folder=remote_folder
                )
            if updates:
                reset_after_delay()


file_updater = FileUpdater()


def reset_after_delay(
    error=False,
):  # In case of an error the LED will be red. A regular reset will not be red.
    delay = 5
    if error:
        board.set_led(value=True, colour=RED)
        delay = 30
    for counter in range(delay, 0, -1):
        log.log("reboot in %d s" % counter)
        wdt.feed()
        time.sleep_ms(1000)
        board.set_led(value=False)
    machine.reset()


WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
DARK = (0, 0, 0)


class Board:
    def __init__(self):
        import uniq_id_names
        import ubinascii

        unique_id_hex = ubinascii.hexlify(machine.unique_id())
        self._boardDict = uniq_id_names.names_id_dict.get(unique_id_hex)
        if self.get_board_dict() == None:
            print(f"did not find boardName: No value for key b'{unique_id_hex:s}'")
            msg = f"-> add unique_id b'{unique_id_hex:s}' to uniq_id_names.py"
            print(msg)
            assert False, msg
        print(
            "machine.unique_id(): %s found b'%s'"
            % (unique_id_hex, self.get_board_name())
        )
        self._led = machine.Pin("LED", machine.Pin.OUT)
        self._np = neopixel.NeoPixel(machine.Pin("GPIO0"), 1)
        try:  # test if main.py is on local file system. If so: real system (no development)
            self._main_is_local = True
            f = open("main.py", "r")
            f.close()
            print("main.py local")
        except:
            print("main.py not local")
            self._main_is_local = False

    def get_board_name(self):
        return self._boardDict.get("name")

    def get_board_dict(self):
        return self._boardDict

    def set_led(self, value=True, colour=GREEN):
        self._led.value(value)
        if value:
            self._np[0] = colour
            self._np.write()
        else:
            value: self._np[0] = DARK
            self._np.write()

    def led_blink_once(self, time_ms=50, colour=GREEN):
        self.set_led(value=1)
        self._np[0] = colour
        self._np.write()
        time.sleep_ms(time_ms)
        self.set_led(value=0)
        self._np[0] = DARK
        self._np.write()

    def main_is_local(self):
        return self._main_is_local


board = Board()


class Wdt:
    def __init__(self):
        self._wdt = None
        self._monitor_last_wdt_ms = time.ticks_ms()
        self._timeout = 8388
        self._installed = False

    def enable(self):
        if board.main_is_local:
            self._wdt = machine.WDT(
                timeout=self._timeout
            )  # The maximum value for timeout is 8388 ms.
            self._installed = True
            log.log(f"Wdt is enabled; timeout = {self._timeout:d} ms", level=TRACE)
            self._monitor_last_wdt_ms = time.ticks_ms()

    def halt_temporary(self, value = False): # https://github.com/micropython/micropython/issues/8600
        if self._installed:
            if value:
                machine.mem32[0x40058000] = machine.mem32[0x40058000] & ~(1<<30)
                log.log(f"Wdt is halted temporary", level=TRACE)
            else:
                self.enable()
        

    def feed(self):
        if self._wdt:
            self._wdt.feed()
        time_since_last_feed = time.ticks_diff(
            time.ticks_ms(), self._monitor_last_wdt_ms
        )
        self._monitor_last_wdt_ms = time.ticks_ms()
        msg = f"Wdt feed, {time_since_last_feed:d} ms elapsed, timeout {self._timeout:d} ms, enabled = {self._wdt != None}"
        if time_since_last_feed > 4000:
            log.log(msg, level=INFO)
        return time_since_last_feed


wdt = Wdt()


class TimeManager:
    def __init__(self):
        self._time_start_ms = time.ticks_ms()
        self._time_restart_ms = None
        self._time_next_update_ms = None

    def need_to_wait(
        self, update_period_ms=5000
    ):  # Waits for 1000ms if we need to wait. Returns True if we need to wait.
        if not self._time_next_update_ms:
            self._time_next_update_ms = time.ticks_add(
                self._time_start_ms, update_period_ms
            )
        if key0.get_key():  # extra measurement
            log.log("key0 pressed")
            log.log("extra measure")
            return False
        time_to_wait_ms = time.ticks_diff(self._time_next_update_ms, time.ticks_ms())
        if time_to_wait_ms > 0:
            if key1.get_key():
                log.log("key1 pressed")
                reset_after_delay()
            if self._time_restart_ms:
                if time.ticks_diff(time.ticks_ms(), self._time_restart_ms) > 0:
                    log.log(
                        "It is time to restart as the time period time_restart_ms is over."
                    )
                    reset_after_delay()
            log.oled_progress_bar(1.0 - time_to_wait_ms / update_period_ms)
            wdt.feed()
            board.led_blink_once(time_ms=50)
            time.sleep_ms(1000 - 50)
            wdt.feed()
            return True
        log.log("uptime ", time_manager.uptime_s_str(self.uptime_s()))
        self._time_next_update_ms = time.ticks_add(
            self._time_next_update_ms, update_period_ms
        )
        log.oled_progress_bar(0.0)
        gc.collect()
        log.log(
            f"gc.mem_alloc {gc.mem_alloc():d}, gc.mem_free  {gc.mem_free():d}",
            level=TRACE,
        )
        return False

    def set_period_restart_ms(
        self, time_restart_ms=3 * 60 * 60 * 1000
    ):  # optional, for periodic restart
        self._time_restart_ms = time.ticks_add(time_restart_ms, self._time_start_ms)
        log.log(
            f"will restart automatically after {self.uptime_s_str(time_restart_ms/1000)}",
            level=TRACE,
        )

    def uptime_s(self):
        return time.ticks_diff(time.ticks_ms(), self._time_start_ms) / 1000

    def uptime_s_str(self, time_s):
        string = ""
        s = int(time_s)
        seconds = s % 60
        if seconds:
            string = "%2ds" % seconds + string
        s = s // 60
        minutes = s % 60
        if minutes:
            string = "%dm" % minutes + string
        s = s // 60
        hours = s % 24
        if hours:
            string = "%dh" % hours + string
        s = s // 24
        days = s % 365
        if days:
            string = "%dd" % days + string
        s = s // 365
        years = s
        if years:
            string = "%dy" % years + string
        return string


time_manager = TimeManager()


def url_encode(t):
    result = ""
    for c in t:
        # no encoding needed for character
        if c.isalpha() or c.isdigit() or c in ["-", "_", "."]:
            result += c
        elif c == " ":
            result += "+"
        else:
            result += f"%{ord(c):02X}"
    return result


class Measurements:
    def __init__(self):
        self.measurements = []

    def append(self, dict_data):
        dict_data["measurement"] = board.get_board_name()
        self.measurements.append(dict_data)

    def upload_to_influx(self, credentials="nano_monitor"):
        gc.collect()
        # upload_to_influx(self.measurements, credentials)
        # https://www.alibabacloud.com/help/en/lindorm/latest/write-data-by-using-the-influxdb-line-protocol
        # <table_name>[,<tag_key>=<tag_value>[,<tag_key>=<tag_value>]] <field_key>=<field_value>[,<field_key>=<field_value>] [<timestamp>]
        # Required: table_name field_set  (timestamp is not required!)
        # https://docs.influxdata.com/influxdb/v2.6/write-data/developer-tools/api/
        #     https://docs.influxdata.com/influxdb/v2.6/api/#operation/PostAuthorizations

        # payload = f"airSensor,sensorId=A0100,station=Harbor humidity=35.0658,temperature=37.2"
        # payload = f"airSensor,sensorId=A0100,station=Baum humidity=35.0658,temperature=37.2\n"
        #          f"airSensor uptime_s=1234\n"

        influxdb_structure.assert_valid(self.measurements)
        payload = ""
        for measurement in self.measurements:
            if payload != "":
                payload += "\n"
            payload += measurement["measurement"]
            tags = measurement["tags"]
            for tag, tag_value in tags.items():
                payload += f",{tag}={tag_value}"
            fields = measurement["fields"]
            firstfield = True
            for field_name, field_value in fields.items():
                if firstfield:
                    payload += f" {field_name}={field_value}"
                    firstfield = False
                else:
                    payload += f",{field_name}={field_value}"
        log.log_print(payload, level=TRACE)
        url = secrets.influx_credentials[credentials]["influxdb_url"]
        for tries in range(2):
            wdt.feed()
            try:
                if secrets.influx_credentials[credentials].get(
                    "influxdb_pass"
                ):  # authentication old
                    db_name = secrets.influx_credentials[credentials].get(
                        "influxdb_db_name"
                    )
                    auth = (
                        secrets.influx_credentials[credentials].get("influxdb_user"),
                        secrets.influx_credentials[credentials].get("influxdb_pass"),
                    )
                    # print(url + f'/write?db={db_name}')#, data = payload, auth=auth)
                    # print(auth)
                    wdt.halt_temporary(value=True) # very ugly, but the urequests takes very long
                    result = urequests.post(
                        url + f"/write?db={db_name}", data=payload, auth=auth
                    )
                    wdt.halt_temporary(value=False)
                if secrets.influx_credentials[credentials].get(
                    "influxdb_token"
                ):  # authentication new influxdb.com
                    bucketName = secrets.influx_credentials[credentials][
                        "influxdb_bucket"
                    ]
                    headers = {
                        "Authorization": f"Token {secrets.influx_credentials[credentials]['influxdb_token']}"
                    }
                    org = secrets.influx_credentials[credentials]["influxdb_org"]
                    url += f"/api/v2/write?precision=s&org={url_encode(org)}&bucket={url_encode(bucketName)}"
                    result = urequests.post(url, headers=headers, data=payload)
                result.close()
                if result.status_code == 204:  # why 204? we'll never know...
                    log.log("influx success")
                    break
                else:
                    print(f"  - upload issue ({result.status_code} {result.reason})")
            except Exception as err:
                log.log(Exception, err)
                log.log("Could not upload")
                reset_after_delay(error=True)
        self.measurements = []


mmts = Measurements()
