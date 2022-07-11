
This is a collection of python scripts intended to provide a
semi-functional CPython binding for common Circuit Python APIs.

i.e. include the following before importing any Circuit Python libraries,
and then you can import and call them as-per usual, at least if the
simulated calls are implemented...:

```
import os, sys
CIRCUITPYTHON = 'boot_out.txt' in os.listdir('/')
if not CIRCUITPYTHON: sys.path.insert(0, 'circuitpy_sim')
```

============================================================



- - - 
## circuitpy_sim

This is a library directory that provides a few modules that minic the Circuit
Python API, but use normal Python for their implementation.

Most of these are reasonably simple pass-throughs.  For example,
adafruit_requests.py just passes its functions through to normal "requests".

The one that's a bit special is neopixel.py.  It provides a mock of the
Circuit Python API that draws simulated Neopixels using the Python tkinter
graphics library.

What it all for?  If the circuitpy_sim directory is inserted into Python's
import path (see circuitpy_sim/README.md for specifics), you can run Circuit
Python code on your normal Linux computer.  This allows much quicker and
easier code iteration cycles than having to constantly upload code to a
Circuit Python board, and also allows use of standard Python debugging tools
(e.g. pdb) on your Circuit Python code.

In this way, you can unittest, manually test, and debug Circuit Python code on
a much more capable platform, and only upload it to a real Circuit Python
board once you're getting reasonably close.

NOTE: circuitpy_sim is still in a very early / alpha-type state.  Any
suggestions or additions would be most welcome.
