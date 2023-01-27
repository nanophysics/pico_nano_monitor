import rp2
import network
import secrets
import time
import machine
import influxdb
import urequests
import uhashlib
import gc

gc.enable()
class Wlan():
    def __init__(self):
        pass
    def start_wlan(self, credentials = 'default'):
        log.log(' -> ', board.get_board_name())
        rp2.country('CH')
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.wlan.config(pm = 0xa11140) # Diable powersave mode
        self.status_dict = {
        "0": "CYW43_LINK_DOWN (0): Es besteht keine WLAN-Verbindung.",
        "1": "CYW43_LINK_JOIN (1): Verbindungsaufbau-Versuch, noch nicht abgeschlossen.",
        "2": "CYW43_LINK_NOIP (2): Verbindungsaufbau war erfolgreich, IP-Konfiguration fehlt noch.",
        "3": "CYW43_LINK_UP (3): Der Verbindungsaufbau war erfolgreich.",
        "-1": "CYW43_LINK_FAIL (-1): Verbindungsaufbau abgebrochen.",
        "-2": "CYW43_LINK_NONET (-2): Verbindungsaufbau abgebrochen, WLAN (SSID) nicht gefunden.",
        "-3": "CYW43_LINK_BADAUTH (-3): Verbindungsaufbau abgebrochen, Authentifizierung fehlgeschlagen. Vemutlich WLAN-Passwort falsch."
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
                    #print("WLAN: SSID:", secret["SSID"], self.status_dict.get("%s" % status))
                    log.log('SSID:', secret["SSID"], ':s%s' % status)
                status_old = status
                if status < 0 or status >= 3:
                    break
            if status == 3:
                ifconfig = self.wlan.ifconfig()
                #print("WLAN: SSID:", secret["SSID"],' connected to ip = ' + ifconfig[0])
                log.log(ifconfig[0])
                connected = True
                break
        if False:
            result = urequests.get('https://ethz.ch/de.html') #'https://www.google.com'
            print('Good result ist 200 and I got: %s' % result.status_code)
        if False:
            result = urequests.get('https://gitlab.phys.ethz.ch/pmaerki/pico_nano_monitor/-/raw/main/test.py') #'https://www.google.com'
            print(result.text)
        if not connected:   
            log.log("Could not establish a wlan connection")
            reset_after_delay()

wlan=Wlan()

TRACE = 0
DEBUG = 1
INFO = 2
WARN = 3
ERROR = 4
FATAL = 5

class Log():
    def __init__(self):
        self._oled_1_3 = False
        self._print = False
        self.level_oled = INFO
        self.level_print = TRACE
        self._oled = None

    def log(self, *string, level = INFO):
        self.log_print(*string)
        self.log_oled(*string)
    
    def log_print(self, *string, level = INFO):
        if level >= self.level_print:
            print(*string)

    def log_oled(self, *string, level = INFO):
        if self._oled:
            if level >= self.level_oled:
                self._oled.printe(''.join(map(str, string)))

    def oled_progress_bar(self, progress=0.5): #progress bar 0.0 ... 1.0
        if self._oled:
            self._oled.progress(progress)

    def enable_oled(self, level_oled = INFO,  level_print = TRACE):
        import oled_1_3
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

'''
class Senko: # from https://raw.githubusercontent.com/RangerDigital//master/senko/senko.py
    raw = "https://raw.githubusercontent.com"
    github = "https://github.com"

    def __init__(self, user=None, repo=None, url=None, branch="master", working_dir="app", files=["boot.py", "main.py"], headers={}):
        """Senko OTA agent class.
        Args:
            user (str): GitHub user.
            repo (str): GitHub repo to fetch.
            branch (str): GitHub repo branch. (master)
            working_dir (str): Directory inside GitHub repo where the micropython app is.
            url (str): URL to root directory.
            files (list): Files included in OTA update.
            headers (list, optional): Headers for urequests.
        """
        self.base_url = "{}/{}/{}".format(self.raw, user, repo) if user else url.replace(self.github, self.raw)
        self.url = url if url is not None else "{}/{}/{}".format(self.base_url, branch, working_dir)
        self.headers = headers
        self.files = files
    def _check_hash(self, x, y):
        x_hash = uhashlib.sha1(x.encode())
        y_hash = uhashlib.sha1(y.encode())
        x = x_hash.digest()
        y = y_hash.digest()

        return str(x) == str(y)

    def _get_file(self, url):
        wdt.feed()
        payload = urequests.get(url, headers=self.headers)
        code = payload.status_code
        if code == 200:
            return payload.text
        else:
            return None
    def _check_all(self):
        changes = []
        for file in self.files:
            wdt.feed()
            latest_version = self._get_file(self.url + "/" + file)
            if latest_version is None:
                continue
            try:
                with open(file, "r") as local_file:
                    local_version = local_file.read()
            except:
                local_version = ""
            if not self._check_hash(latest_version, local_version):
                changes.append(file)
        return changes
    def fetch(self): #Check if newer version is available. Returns: True - if is, False - if not.
        return(len(self._check_all()) > 0)
    def update(self): #Replace all changed files with newer one. Returns: True - if changes were made, False - if not.
        changes = self._check_all()
        for file in changes:
            wdt.feed()
            with open(file, "w") as local_file:
                local_file.write(self._get_file(self.url + "/" + file))
        return(len(changes) > 0)
'''

GITHUB_URL = 'https://raw.githubusercontent.com/nanophysics/pico_nano_monitor/main'

class Ota_git:
    def __init__(self):
        self._headers={}
        
    def _get_remote_file(self, url = '', file = ''):
        _url = url + "/" + file
        payload = urequests.get(_url, headers=self._headers)
        if payload.status_code != 200:
            return None
        if len(payload.text) == 0: # seams to be wrong
            return None
        return payload.text

    def _get_local_file(self, file = ''):
        f = open(file, "r")
        try:
            text = f.read()
            f.close()
        except:
            return None
        if len(text) == 0: # seams to be wrong
            return None
        return text
    
    def update_files_if_changed(self, url = '', files=[]):
        updated = 0
        if files:
            for file in files:
                str_local = self._get_local_file(file = file)
                str_git = self._get_remote_file(url = url, file = file)
                if str_local != str_git:
                        f = open(file, "w")
                        f.write(str_git)
                        f.close
                        log.log(f'updated {file}', level= TRACE)
                        updated += 1
                else:
                        log.log(f'actual {file}', level= TRACE)
                return updated
            
    def _compare_strings(self, str_local, str_git): # in case we search for strange effects
        str_local = "".join(c for c in str_local if c != '\r')
        str_local_length = len(str_local)
        str_git_length = len(str_git)
        max_length = max(str_local_length, str_git_length)
        local = None; remote = None
        counter = 0
        counter_line = 0
        counter_char = 0
        for element in range(0, max_length-1):
            if element < str_local_length:
                counter_char += 1
                local = str_local[element]
                if local == '\n':
                    counter_line += 1
                    counter_char = 0
                local = repr(local)
            if element < str_git_length:
                remote = repr(str_git[element])
            if local != remote:
                print(f'Line: {counter_line}, character nr. {counter_char} local: {local} remote: {remote}')
                counter += 1
                if counter > 40:
                    break
        print(str_local[0:400])
        print(str_git[0:400])
        
ota_git = Ota_git()

def reset_after_delay():
    for counter in range(5, 0, -1):
        log.log("reboot in %d s" % counter)
        wdt.feed()
        time.sleep_ms(1000)
    machine.reset()

class Board:
    def __init__(self):
        import uniq_id_names
        import ubinascii
        unique_id_hex = ubinascii.hexlify(machine.unique_id())
        self._boardDict = uniq_id_names.names_id_dict.get(unique_id_hex)
        if self.get_board_name() == None:
            print('did not find boardName: Found %s in uniq_id_names.py for key %s' % (self.get_board_name(), unique_id_hex))
            print('-> add unique_id to uniq_id_names.py')
            assert False
        print('machine.unique_id(): %s found \'%s\''  % ( unique_id_hex, self.get_board_name()))
        self._led = machine.Pin('LED', machine.Pin.OUT)
        try: # test if main.py is on local file system. If so: real system (no development)
            self._main_is_local = True
            f = open('main.py', "r") 
            f.close()
            print('main.py local')
        except:
            print('main.py not local')
            self._main_is_local = False
    def get_board_name(self):
        return self._boardDict.get('name')
    def get_board_dict(self):
        return self._boardDict
    def set_led(self, value = True):
        self._led.value(value)
    def led_blink_once(self, time_ms = 50):
        self.set_led(value = 1)
        time.sleep_ms(time_ms)
        self.set_led(value = 0)
    def main_is_local(self):
        return self._main_is_local

board = Board()

class FileUpdater:
    def __init__(self):
        pass
    def update_if_local(self):
        gc.collect()
        if board.main_is_local():
            log.log('check for new files', level = TRACE)
            files=['utils.py','uniq_id_names.py','influxdb.py','oled_1_3.py']
            dict = board.get_board_dict()
            #print(dict)
            add_files = dict.get('src_files')
            #print(add_files)
            if files:
                for file in add_files:
                    print(file)
                    files.append(dict.get('src_folder')+file)
            #print('files: ', files)
            updates = ota_git.update_files_if_changed(url=GITHUB_URL, files=files)
            if updates:
                reset_after_delay()

file_updater = FileUpdater()

class Wdt:
    def __init__(self):
        self._wdt = None
    
    def enable(self):
        self._wdt = machine.WDT(timeout=8300) # The maximum value for timeout is 8388 ms.
    
    def feed(self):
        if self._wdt:
            self._wdt.feed()

wdt = Wdt()

class TimeManager():
    def __init__(self):
        self._time_start_ms = time.ticks_ms()
        self._time_restart_ms = None
        self._time_next_update_ms = None
    def need_to_wait(self, update_period_ms = 5000): # True if we need to wait
        if not self._time_next_update_ms:
            self._time_next_update_ms = time.ticks_add(self._time_start_ms, update_period_ms)
        if key0.get_key(): # extra measurement
            log.log('key0 pressed')
            log.log('extra measure')
            return False
        time_to_wait_ms = time.ticks_diff(self._time_next_update_ms, time.ticks_ms())
        if time_to_wait_ms > 0:
            if key1.get_key():
                log.log('key1 pressed')
                reset_after_delay()
            if self._time_restart_ms:
                if time.ticks_diff(time.ticks_ms(), self._time_restart_ms) > 0:
                    log.log('It is time to restart as the time period time_restart_ms is over.')
                    reset_after_delay()
            log.oled_progress_bar(1.0-time_to_wait_ms / update_period_ms)
            wdt.feed()
            return True
        log.log('uptime ', time_manager.uptime_s_str())
        self._time_next_update_ms = time.ticks_add(self._time_next_update_ms, update_period_ms)
        log.oled_progress_bar(0.0)
        gc.collect()
        log.log(f'gc.mem_alloc {gc.mem_alloc():d}, gc.mem_free  {gc.mem_free():d}', level = TRACE)
        return False
    def set_period_restart_ms(self, time_restart_ms =  3 * 60 * 60 * 1000): # optional, for periodic restart
        self._time_restart_ms = time.ticks_add(time_restart_ms, self._time_start_ms)
    def uptime_s(self):
        return time.ticks_diff(time.ticks_ms(), self._time_start_ms)/1000
    def uptime_s_str(self):
        string = ''
        s = int(self.uptime_s())
        seconds = s % 60
        if seconds: string = '%2ds' % seconds + string 
        s = s // 60
        minutes = s % 60
        if minutes: string = '%dm' % minutes + string 
        s = s // 60
        hours = s % 24
        if hours: string = '%dh' % hours + string 
        s = s // 24
        days = s % 365
        if days: string = '%dd' % days + string 
        s = s // 365
        years = s
        if years: string = '%dy' % years + string 
        return string

time_manager = TimeManager()

class Measurements:
    def __init__(self):
        self.measurements = []

    def append(self, dict_data):
        dict_data['measurement'] = board.get_board_name()
        self.measurements.append(dict_data)

    def upload_to_influx(self, credentials = 'nano_monitor'):
        influxdb.upload_to_influx(self.measurements, credentials)
        self.measurements = []

mmts = Measurements()
