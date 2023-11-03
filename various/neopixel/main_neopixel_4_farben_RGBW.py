# Selbsttest Neopixel RGBW also mit 4 LED's

#import rp2
import time
#import machine
import neopixel


farben={
"RED" : (255, 0, 0,0),
"GREEN" : (0, 255, 0,0),
"BLUE" : (0, 0, 255,0),
"WHITE_RGB" : (255, 255, 255,0),
"WHITE_WHITE" : (0, 0, 0,255),
"DARK" : (0, 0, 0,0),
}

np = neopixel.NeoPixel(machine.Pin("GPIO0"), 1, bpp=4)

    
while True:
    for key in farben:
        np[0]=farben[key]
        print(key, np[0])
        np.write()
        time.sleep_ms(2000)
