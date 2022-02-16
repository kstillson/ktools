
This is a collection of python scripts intended to provide a
semi-functional CPython binding for common Circuit Python APIs.

i.e. include the following before importing any Circuit Python libraries,
and then you can import and call them as-per usual, at least if the
simulated calls are implemented...:

```
import os, sys
CIRCUITPYTHON = 'boot_out.txt' in os.listdir('/')
if not CIRCUITPYTHON: sys.path.insert(0, 'circpysim')
```
