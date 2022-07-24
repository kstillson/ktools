'''Neopixel abstraction / wrapper.

The idea of this module is to provide basic Neopixel operations that provides
the exact same API on 4 rather different platforms:

 - Raspberry PI

 - A Circuit Python board

 - Under normal full Python ("CPyhon"), using ../circuitpy_sim, which uses
   tkinter to draw simulated graphical LEDs

 - Running with simulation=True passed to the constructor, which is
   "headless" (i.e. no LED or graphical output).  You can set() and get()
   colors, but that's about it.  It's mostly for testing.

                                --------------

To run on a Raspberry PI, this module uses the Adafruit "blinka" library as
a backend.  To get that installed:
   sudo pip3 install rpi_ws281x adafruit-circuitpython-neopixel

To get this working on a real Circuit Python board, you'll need the Adafruit
NeoPixel library, see https://learn.adafruit.com/circuitpython-essentials/circuitpython-neopixel

To get circuitpy_sim working, you need the circuitpy_sim directory in the Python
path, so something like this:
    import os, sys
    CIRCUITPYTHON = 'boot_out.txt' in os.listdir('/')
    if not CIRCUITPYTHON: sys.path.insert(0, 'circuitpy_sim')


Various pieces copied from Adafruit's libraries.  Thanks Adafruit!

'''

# ---------- color def constants

AMBER = (255, 100, 0)
AQUA = (50, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
CYAN = (0, 255, 255)
GOLD = (255, 222, 30)
GREEN = (0, 255, 0)
JADE = (0, 255, 40)
MAGENTA = (255, 0, 20)
OFF = (0, 0, 0)
ORANGE = (255, 40, 0)
PINK = (242, 90, 255)
PURPLE = (180, 0, 255)
RED = (255, 0, 0)
TEAL = (0, 255, 120)
WHITE = (255, 255, 255)
YELLOW = (255, 150, 0)
RGBW_WHITE_RGB = (255, 255, 255, 0)
RGBW_WHITE_RGBW = (255, 255, 255, 255)
RGBW_WHITE_W = (0, 0, 0, 255)


# ---------- color mapping functions

# map circuit python pixel API into rpi_ws281x python API
# (based on http://circuitpython.readthedocs.io/projects/neopixel/en/latest/_modules/neopixel.html)

def wheel(pos):
    '''Takes an int between 0 and 255, returns a color tuple r->g->b->r...'''
    if pos < 85:
        return (int(pos*3), int(255 - (pos*3)), 0)
    elif pos < 170:
        pos -= 85
        return (int(255 - (pos*3)), 0, int(pos*3))
    else:
        pos -= 170
        return (0, int(pos*3), int(255 - pos*3))

def color_to_rgb(color):
    '''Takes a color number (e.g. 0x123456) and returns an RGB tuple (e.g. (0x12, 0x34, 0x56))'''
    store = []
    for i in range(3):
        element = color & 0xff
        store.append(element)
        color = color >> 8
    tmp = store[::-1]  # reverses list order
    return tuple(i for i in tmp)

def rgb_to_color(rgb):
    '''Takes a rgb tuple and returns a merged color number.'''
    color = 0
    for i in rgb: color = (color << 8) + int(i)
    return color


# ---------- Neopixel abstraction

class Neo:
    '''Object oriented abstraction for Adafruit Neopixels.

       n is the number of chained neopixels.

       RPi in non-simulation mode:
        - MUST BE RUN BY ROOT
        - Allowed pins: GPIO10(doesn't work?), GPIO12, GPIO18, or GPIO21
        - will autoselect D18 (Adafruit's default) if not otherwise specified.

       reverse_rg is used for cases where the hardware has red and green LEDs in reverse order
       (i.e. if you ask for red and get green, set this).  include_w is for RGBW leds.'''

    # ---------- general API

    def __init__(self, n=1, pin=None, brightness=1.0,
                 auto_write=True, simulation=False,
                 reverse_rg=False, include_w=False):
        self._auto_write = auto_write
        self._brightness = brightness
        self._n = n
        self._vals = [0] * n
        if simulation:
            self._strip = None
            return

        import neopixel
        if include_w:
            order = neopixel.RGBW if reverse_rg else neopixel.GRBW
        else:
            order = neopixel.RGB if reverse_rg else neopixel.GRB
        if not pin:
            import board
            pin = board.D18
        self._strip = neopixel.NeoPixel(pin, n, brightness=brightness, auto_write=auto_write, pixel_order=order)


    def get(self, index):
        if index >= self._n or index < 0: raise IndexError
        return self._vals[index]

    def set(self, index, value):
        if index < 0: index += len(self)
        if index >= self._n or index < 0: raise IndexError
        self._vals[index] = value  # Raw value, without brightness applied.
        if self._strip: self._strip[index] = value

    @property
    def brightness(self): return self._brightness

    @brightness.setter
    def brightness(self, brightness):
        self._brightness = min(max(brightness, 0.0), 1.0)
        if self._strip: self._strip.brightness = self._brightness

    def redraw(self):
        for i in range(self._n): self.set(i, self._vals[i])
        if not self._auto_write: self.show()

    def show(self):
        if self._strip: self._strip.show()


    # ----- helpers to set multiple LEDs

    def black(self):
        self.fill(0)
        if not self._auto_write: self.show()

    def fill(self, color):
        for i in range(self._n): self.set(i, color)
        if not self._auto_write: self.show()

    def fill_wheel(self):
        for i in range(self._n):
            wheel_pos = int(255.0 * i / self._n)
            self.set(i, wheel(wheel_pos))
        if not self._auto_write: self.show()

    def wipe(self):
        self.black()


    # ---------- internals

    def __getitem__(self, index): return self._vals[index]

    # basically just a wrapper around set() that supports slices.
    def __setitem__(self, index, val):
        if isinstance(index, slice):
            for index_i, val_i in enumerate(range(index.start, index.stop + 1, index.step or 1)):
                v = val[index_i] if isinstance(val, list) else val
                self.set(val_i, v)
        else: self.set(index, val)
