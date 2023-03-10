import machine
import time

class Adc:
    def __init__(self, pin = 'GPIO26'):
        self.adc = machine.ADC(machine.Pin(pin))
        
    def measure(self, average_n = 1) -> float: # 0...1
        # a single measurement takes about 2 us
        # @ average = 1000 it takes about 14ms (measured)
        value_n = 0
        for i in range(average_n):
            value_n += self.adc.read_u16()
        return(float(value_n) / average_n / 2**16)

class Pressure_15_psi_sensor_ali():
    def __init__(self):
        self.adc_5V_GP0 = Adc_5V_GP0()
        self.overload = True

    def get_pressure_pa(self, average_n = 1000):
        voltage_V = self.adc_5V_GP0.voltage(average_n = average_n)
        # Drucksensor absolut von Alie XIDIBEI Official Store 15 psi
        pa_per_psi = 6894.75729 # https://www.unitconverters.net/pressure/psi-to-pascal.htm
        p1_pa = 0.0
        p2_pa = 15.0 * pa_per_psi
        u1_V = 0.5
        u2_V = 4.5
        self.overload = voltage_V < u1_V or voltage_V > u2_V
        return((p2_pa - p1_pa)/(u2_V - u1_V) * (voltage_V - u1_V))
    
    def get_overload(self):
        return self.overload
    
pressure_15_psi_sensor_ali = Pressure_15_psi_sensor_ali()

while True:
    start_us = time.ticks_us()
    print('pressure %0.0f Pa' % pressure_15_psi_sensor_ali.get_pressure_pa(average_n = 1000))
    stop_us = time.ticks_us()
    print('Time %d us' % time.ticks_diff(stop_us, start_us) )
    time.sleep_ms(1000)