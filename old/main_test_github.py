import time
import machine
import utils
import config




import urequests
utils.wlan.start_wlan()

GITHUB_URL = 'https://raw.githubusercontent.com/nanophysics/pico_nano_monitor/main'

file = 'influxdb_structure.py'

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
        for file in files:
            str_local = self._get_local_file(file = file)
            str_git = self._get_remote_file(url = url, file = file)
            if str_local != str_git:
                    f = open(file, "w")
                    f.write(str_git)
                    f.close
                    utils.log.log(f'updated {file}', level= utils.TRACE)
            else:
                    utils.log.log(f'actual {file}', level= utils.TRACE)
            
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


ota_git.update_files_if_changed(url='https://raw.githubusercontent.com/nanophysics/pico_nano_monitor/main', files=('influxdb_structure.py',))



#ota_git._compare_strings(str_local, str_git)


