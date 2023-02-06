# inspiriert von https://www.waveshare.com/wiki/Pico-OLED-1.3

from machine import Pin, SPI
import framebuf
import time

DC = 8
RST = 12
MOSI = 11
SCK = 10
CS = 9


class OLED_1inch3(framebuf.FrameBuffer):
    def __init__(self):
        self.width = 128
        self.height = 64

        self.cs = Pin(CS, Pin.OUT)
        self.rst = Pin(RST, Pin.OUT)

        self.cs(1)
        self.spi = SPI(1)
        self.spi = SPI(1, 2000_000)
        self.spi = SPI(
            1, 20000_000, polarity=0, phase=0, sck=Pin(SCK), mosi=Pin(MOSI), miso=None
        )
        self.dc = Pin(DC, Pin.OUT)
        self.dc(1)
        self.buffer = bytearray(self.height * self.width // 8)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_HMSB)
        self.init_display()

        self.white = 0xFFFF
        self.balck = 0x0000

    def write_cmd(self, cmd):
        self.cs(1)
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def write_data(self, buf):
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(bytearray([buf]))
        self.cs(1)

    def init_display(self):
        """Initialize dispaly"""
        self.rst(1)
        time.sleep(0.001)
        self.rst(0)
        time.sleep(0.01)
        self.rst(1)

        self.write_cmd(0xAE)  # turn off OLED display

        self.write_cmd(0x00)  # set lower column address
        self.write_cmd(0x10)  # set higher column address

        self.write_cmd(0xB0)  # set page address

        self.write_cmd(0xDC)  # set display start line
        self.write_cmd(0x00)
        self.write_cmd(0x81)  # contract control
        self.write_cmd(0x6F)  # 128
        self.write_cmd(0x21)  # Set Memory addressing mode (0x20/0x21) #

        self.write_cmd(0xA0)  # set segment remap
        self.write_cmd(0xC0)  # Com scan direction
        self.write_cmd(0xA4)  # Disable Entire Display On (0xA4/0xA5)

        self.write_cmd(0xA6)  # normal / reverse
        self.write_cmd(0xA8)  # multiplex ratio
        self.write_cmd(0x3F)  # duty = 1/64

        self.write_cmd(0xD3)  # set display offset
        self.write_cmd(0x60)

        self.write_cmd(0xD5)  # set osc division
        self.write_cmd(0x41)

        self.write_cmd(0xD9)  # set pre-charge period
        self.write_cmd(0x22)

        self.write_cmd(0xDB)  # set vcomh
        self.write_cmd(0x35)

        self.write_cmd(0xAD)  # set charge pump enable
        self.write_cmd(0x8A)  # Set DC-DC enable (a=0:disable; a=1:enable)
        self.write_cmd(0xAF)

    def show(self):
        self.write_cmd(0xB0)
        for page in range(0, 64):
            self.column = 63 - page
            self.write_cmd(0x00 + (self.column & 0x0F))
            self.write_cmd(0x10 + (self.column >> 4))
            for num in range(0, 16):
                self.write_data(self.buffer[page * 16 + num])


class OLED:  # zeilenweise rein schreiben und darstellen
    def __init__(self):
        self._OLED = OLED_1inch3()
        self._linienhoehe = 9
        self._display_strings = []
        self._totalwith = 128
        self._totalhigh = 64
        self._lines = self._totalhigh // self._linienhoehe
        self._chars = self._totalwith // 8 - 1
        self._progress = 0.0

    def printe(self, string="test"):
        self._display_strings.insert(0, string[: self._chars])
        if len(self._display_strings) > self._lines:
            self._display_strings.pop()
        self._show()

    def progress(self, progress=0.5):  # progress bar 0.0 ... 1.0
        self._progress = progress
        self._show()

    def _show(self):
        self._OLED.fill(0x0000)
        line = self._lines - 1
        for string in self._display_strings:
            self._OLED.text(string, 1, line * self._linienhoehe, self._OLED.white)
            line -= 1
        # self._OLED.rect(0,0,128,64,self._OLED.white)
        # self._OLED.line(0,0,65,64,self._OLED.white)
        # self._OLED.text('o',121,58,self._OLED.white)
        # self._OLED.line(127,0,127,63,self._OLED.white)
        bar = int(self._progress * (self._totalwith))
        bar = max(bar, 0)
        bar = min(bar, self._totalwith)
        if bar > 0:
            self._OLED.line(
                0, self._totalhigh - 1, bar, self._totalhigh - 1, self._OLED.white
            )
        self._OLED.show()


if __name__ == "__main__":
    oled_peter = OLED()
    counter = 0
    while True:
        oled_peter.printe("gagasadasdas %d" % counter)
        time.sleep(1)
        counter += 1
