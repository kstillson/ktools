
import threading, time, sys
import kcore.common as C

GRAPHICS = True
try:
    import tkinter
except:
    sys.stderr.write('Unable to import tkinter; disabling Neopixel graphical simulation')
    GRAPHICS = False


# ---------- global controls

LOG_LEVEL_SETUP = C.INFO
LOG_LEVEL_SET_PIXEL = C.DEBUG

PIXEL_X = 15
PIXEL_Y = 15

# ---------- global state

ROOT = None


# ---------- constants used by callers

RGB = 0
GRB = 0
RGBW = 0
GRBW = 0


# ---------- tkinter based Neopixel simulator

def sep_rgb(rgb):
    b = rgb & 0xff
    tmp = rgb >> 8
    g = tmp & 0xff
    r = tmp >> 8
    return r, g, b


class NeoPixel:
    def __init__(self, pin, num_pixels, **kwargs):
        if LOG_LEVEL_SETUP: C.log(f'NeoPixel: new array of {num_pixels} dots', LOG_LEVEL_SETUP)
        self.n = num_pixels
        self.kwargs = kwargs
        self.brightness = 1.0
        self.data = []
        for i in range(num_pixels): self.data.append((0, 0, 0))
        if not GRAPHICS: return
        t = threading.Thread(target=self._start_tkinter, daemon=True).start()
        # Wait until other thread is ready.
        while not ROOT: time.sleep(0.2)

    def _start_tkinter(self):
        root = tkinter.Tk()
        self.x_width = PIXEL_X * self.n
        self.y_width = PIXEL_Y
        root.geometry(f'{self.x_width}x{self.y_width}')
        root.title(f'circ py neopixel strip {self.n}')
        self.canvas = tkinter.Canvas(root, width=self.x_width, height=self.y_width)
        self.canvas.pack()
        self.rects = []
        for i in range(self.n):
            x0 = PIXEL_X * i
            x1 = x0 + PIXEL_X - 2
            self.rects.append(self.canvas.create_rectangle(x0, 0, x1, PIXEL_Y, fill='red'))
        global ROOT
        ROOT = root
        root.mainloop()

    def __getitem__(self, index):
        return self.data[index]

    def __len__(self): return self.n

    def __setitem__(self, index, val_orig):
        val = val_orig
        if isinstance(index, slice):
            seq_index = 0
            for i in range(index.start or 0, index.stop or self.n, index.step or 1):
                self.__setitem__(i, val[seq_index])
                seq_index += 1
            return
        if isinstance(val, int): val = sep_rgb(val)
        if self.brightness != 1.0:
            val = (int(val[0] * self.brightness), int(val[1] * self.brightness), int(val[2] * self.brightness))
        if LOG_LEVEL_SET_PIXEL: C.log(f'NeoPixel: set {index} to {val}  val_orig={val_orig}', LOG_LEVEL_SET_PIXEL)
        if not GRAPHICS: return
        hexcol = '#%02x%02x%02x' % val
        self.canvas.itemconfig(self.rects[index], fill=hexcol)

    def __setslice__(self, start, stop, val):
        for i in range(start, stop): 
            self.__setitem__(i, val)
            
    def fill(self, color):
        for i in range(self.n): self[i] = color

    def show(self): pass

