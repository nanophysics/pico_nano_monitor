def measure_voltage(average = 1000):
    # a single measurement takes about 2 us
    # @ average = 1000 it takes about 14ms (measured)
    uref = 3.0 # when using an external LT4040 3V reference
    value_n = 0
    counter = 0
    while counter < average:
        value_n += adc.read_u16()
        counter += 1
    return(float(value_n) / counter / 2**16 * uref)

if True:
    from machine import ADC
    adc = ADC(Pin(26))
    start_us = time.ticks_us()
    voltage = measure_voltage(average = 50000)
    stop_us = time.ticks_us()
    print(voltage)
    print(time.ticks_diff(stop_us, start_us) )