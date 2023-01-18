import rp2
import network
import secrets
import time
import machine

rp2.country('CH')
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.config(pm = 0xa11140) # Diable powersave mode
status_dict = {
"0": "CYW43_LINK_DOWN (0): Es besteht keine WLAN-Verbindung.",
"1": "CYW43_LINK_JOIN (1): Verbindungsaufbau-Versuch, noch nicht abgeschlossen.",
"2": "CYW43_LINK_NOIP (2): Verbindungsaufbau war erfolgreich, IP-Konfiguration fehlt noch.",
"3": "CYW43_LINK_UP (3): Der Verbindungsaufbau war erfolgreich.",
"-1": "CYW43_LINK_FAIL (-1): Verbindungsaufbau abgebrochen.",
"-2": "CYW43_LINK_NONET (-2): Verbindungsaufbau abgebrochen, WLAN (SSID) nicht gefunden.",
"-3": "CYW43_LINK_BADAUTH (-3): Verbindungsaufbau abgebrochen, Authentifizierung fehlgeschlagen. Vemutlich WLAN-Passwort falsch."
} 

logRepl = True # if False: no log to Repl


def print_oled(*string):
    global logRepl
    try:
        oled.printe(''.join(string))
        if logRepl:
            print(*string)
    except:
        if logRepl:
            print(*string)

connected = False

def start_wlan():
    global connected
    for secret in secrets.wlan_credentials:
        status_old = None
        wlan.connect(secret["SSID"], secret["PASSWORD"])
        for max_wait in range(20):
            feedWDT()
            time.sleep_ms(500)
            status = wlan.status()
            if status != status_old:
                print("WLAN: SSID:", secret["SSID"], status_dict.get("%s" % status))
                print_oled('SSID:', secret["SSID"], ':s%s' % status)
            status_old = status
            if status < 0 or status >= 3:
                break
        if status == 3:
            ifconfig = wlan.ifconfig()
            print("WLAN: SSID:", secret["SSID"],' connected to ip = ' + ifconfig[0])
            print_oled(ifconfig[0])
            connected = True
            break

    if not connected:
        for counter in range(60, 0, -1):
            print("Could not establish a wlan connection, reboot in %d seconds" % counter)
            time.sleep_ms(1000)
        machine.reset()

import urequests
import uhashlib

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

        if str(x) == str(y):
            return True
        else:
            return False

    def _get_file(self, url):
        feedWDT()
        payload = urequests.get(url, headers=self.headers)
        code = payload.status_code
        if code == 200:
            return payload.text
        else:
            return None

    def _check_all(self):
        changes = []
        for file in self.files:
            feedWDT()
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
            feedWDT()
            with open(file, "w") as local_file:
                local_file.write(self._get_file(self.url + "/" + file))
        return(len(changes) > 0)

def reset_after_delay():
    for counter in range(10, 0, -1):
        #print("Rebooting in %d seconds" % counter)
        print_oled("reboot in %d s" % counter)
        feedWDT()
        time.sleep_ms(1000)
    machine.reset()
    
def update_if_required(folder = "", files = [], restart_if_new = False):
    # folder is the subfolder in the git project folder folder = "" or folder = "/app"
    # files are copied to the top level of the RP2
    GITHUB_URL = "https://raw.githubusercontent.com/nanophysics/pico_nano_monitor/main" + folder
    OTA = Senko(url=GITHUB_URL , files = files)
    print('Check if there are more actual files on github, if so, do update the local ones. Files: %s' % files)
    updated = OTA.update()
    if updated:
        print('Senko: updated git: %s file %s' % (GITHUB_URL, files))
        if restart_if_new:
            print('Found new version of %s' % files)
            print_oled('new:%s' % files)
            reset_after_delay()
    return updated

boardName = None

def findboardName():
    global boardName
    import uniq_id_names
    import ubinascii
    unique_id_hex = ubinascii.hexlify(machine.unique_id())
    boardName = uniq_id_names.names_id_dict.get(unique_id_hex)
    if boardName == None:
        print('did not find boardName: Found %s in uniq_id_names.py for key %s' % (boardName, unique_id_hex))
        print('-> add unique_id to uniq_id_names.py')
    print('For machine.unique_id(): %s found name: \'%s\''  % ( unique_id_hex, boardName))

def update_files():
    global boardName
    print_oled('check for new files')
    update_if_required(files = ['wlan_helper.py'], restart_if_new = True)
    update_if_required(files = ['uniq_id_names.py'])
    findboardName()
    update_if_required(folder = "/pico/" + boardName , files = ["main.py"], restart_if_new = True)

wdt = None
def enableWDT():
    global wdt
    wdt = machine.WDT(timeout=8300) # The maximum value for timeout is 8388 ms.
    #print('WDT enabled')
    
def feedWDT():
    global wdt
    if wdt:
        wdt.feed()

def time_since_start(s):
    string = ''
    s = int(s)
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

time_start_ms = time.ticks_ms()
time_next_update_ms = time_start_ms

def time_since_start_s():
    return time.ticks_diff(time.ticks_ms(), time_start_ms)/1000

def print_time_since_start_s():
    print_oled('uptime:', time_since_start(time_since_start_s()))

findboardName()
oled = None

def enable_oled():
    global oled
    import oled_1_3
    oled = oled_1_3.OLED()

from machine import Pin
led = Pin('LED', Pin.OUT)

runs_from_thonny = None
try: # test if main.py is on local file system. If so: real system (no development)
    runs_from_thonny = False
    f = open('main.py', "r") 
    f.close()
    print('main.py: local')
except:
    print('main.py: Thonny')
    runs_from_thonny = True

    
def update_if_local():
    global runs_from_thonny
    if runs_from_thonny == False:
        print_oled('main.py is local')
        update_files()
        update_if_required(files = ["uniq_id_names.py","influxdb.py","oled_1_3.py"])
        enableWDT()
    else:
        print_oled('started: Thonny')
    
