
import tkinter, threading, time, sys
import circpysim_base

# Global controls
LOG_LEVEL_SETUP = 1
LOG_LEVEL_SET_PIXEL = 3
GRAPHICS = True

PIXEL_X = 15
PIXEL_Y = 15

# Global state
ROOT = None

class NeoPixel:
    def __init__(self, pin, num_pixels, **kwargs):
        if LOG_LEVEL_SETUP: circpysim_base.log(f'NeoPixel: new array of {num_pixels} dots', LOG_LEVEL_SETUP)
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

    def __setitem__(self, index, val):
        if isinstance(index, slice):
            seq_index = 0
            for i in range(index.start or 0, index.stop or self.n, index.step or 1):
                self.__setitem__(i, val[seq_index])
                seq_index += 1
            return
        if isinstance(val, int): val=(val, val, val)
        if LOG_LEVEL_SET_PIXEL: circpysim_base.log(f'NeoPixel: set {index} to {val}', LOG_LEVEL_SET_PIXEL)
        if not GRAPHICS: return
        col = (val[0] << 16) + (val[1] << 8) + val[2]
        hexcol = "#"+"{0:#0{1}x}".format(col, 8)[2:]
        self.canvas.itemconfig(self.rects[index], fill=hexcol)

    def __setslice__(self, start, stop, val):
        for i in range(start, stop): 
            self.__setitem__(i, val)
            
    def fill(self, color):
        for i in range(self.n): self[i] = color

    def show(self): pass

