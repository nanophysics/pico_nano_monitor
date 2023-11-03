import machine
import neopixel

np = neopixel.NeoPixel(machine.Pin('GPIO0'), 1)

WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
DARK = (0,0,0)

np[0] = GREEN

np.write()

