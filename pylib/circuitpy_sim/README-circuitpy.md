# circuitpy_sim

This is a collection of python scripts intended to provide a
semi-functional CPython binding for common Circuit Python APIs.

In-other-words, if you include this directory in your Python path, then the
various imports that would be normally be provided by thge built-in
environment on a Circuit Python board will instead be provided by this code,
thus allowing you to run code intended for Circuit Python under normal Python.

Why would you want to do this?  Well, there are a lot of tools available for
standard Python that are not available for Circuit Python- for example PDB for
debugging and pytest-3 for unit tests.  In this way, you can develop your code
on a full-blown Python system, and only once it's passing its tests and seems
mostly-done do you need to actually upload it to the Circuit Python board.

Most of these are reasonably simple pass-throughs.  For example,
adafruit_requests.py just passes its functions through to normal "requests".

One that's a bit special is neopixel.py.  It provides a mock of the Circuit
Python API that draws simulated Neopixels using the Python tkinter graphics
library.  This allows you to test things like animation sequences without
needing to construct anything in actual hardware.

TODO(defer): eventually I'm hoping to also provide a tkinter inrterface for
GPIO inputs and outputs, so you can simulate use-cases that involve buttons
and LEDs, etc.  If anyone would like to help that along, your contributions
would be most appreciated.  :-D

To make it work, add the following block to the top of your Circuit Python
code:

```
import os, sys
CIRCUITPYTHON = 'boot_out.txt' in os.listdir('/')
if not CIRCUITPYTHON: sys.path.insert(0, 'circuitpy_sim')
```

NOTE: circuitpy_sim is still in a rather early / alpha-type state.  Any
suggestions or additions would be most welcome.
