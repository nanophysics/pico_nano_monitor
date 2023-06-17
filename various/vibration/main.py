import machine
import time

import micropython
micropython.alloc_emergency_exception_buf(100)



class Vibration:
    def __init__(self):
        self._sig_counter = 0
        self._sig_integrator = 0
        self._sig_abs_difference = 0
        self._sig_peak = 0
        self._sig_average = 0.0
        self._sig_sig_measure = 0
        self._sig_ref_measure = 0
        self._vib_sig = machine.ADC(26)
        self._vib_ref = machine.ADC(27)
        self._doReset = False
        
    def process_isr(self, k):
        if self._doReset:
            self._sig_counter = 0
            self._sig_integrator = 0
            self._sig_abs_difference = 0
            self._sig_peak = 0
            self._sig_average = 0.0
            self._doReset = False
        self._sig_counter += 1
        self._sig_sig_measure = self._vib_sig.read_u16()//16 # the RP Pico ADC has only 12 bit
        self._sig_ref_measure = self._vib_ref.read_u16()//16
        expected_reference = 2250
        assert self._sig_ref_measure < expected_reference+1000 and self._sig_ref_measure > expected_reference-1000  # Test Reference and therefore circuit
        self._sig_abs_difference = abs(self._sig_sig_measure - self._sig_ref_measure)
        self._sig_integrator += self._sig_abs_difference
        self._sig_peak = max(self._sig_peak, self._sig_abs_difference)
        self._sig_average = float(self._sig_integrator) / float(self._sig_counter)
        
    def getPeakAverage(self): # value between 0 and 1, peak since lasst reset, arbitrary unit
        sig_peak_float = min(float(self._sig_peak)/2**11, 1.0)
        sig_average_float = min(float(self._sig_average)/2**11, 1.0)
        self._doReset = True
        return sig_peak_float, sig_average_float

tim1 = machine.Timer(-1)

vibration = Vibration()
tim1.init(period=1, mode=tim1.PERIODIC, callback=vibration.process_isr)

if __name__ == "__main__":
    while True:
        time.sleep_ms(1000)
        sig_peak, sig_average = vibration.getPeakAverage()
        print('sig %d, ref %d, diff %d, peak %d, average %d, counter %d' %  (vibration._sig_sig_measure, vibration._sig_ref_measure,vibration._sig_abs_difference,vibration._sig_peak,vibration._sig_average, vibration._sig_counter))
        #print('sig_counter %d' % vibration.sig_counter)


