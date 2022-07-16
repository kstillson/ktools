'''This is part of circuitpy_sim.  See README-circuitpy.md for details.'''

import time, socket, sys, uuid
import kcore.common as C

PY_VER = sys.version_info[0]

class Radio:
    def __init__(self):
        self.hostname = socket.gethostname()
        self.ipv4_address = socket.gethostbyname(self.hostname)
        if PY_VER == 3:
            self.mac_address = uuid.getnode().to_bytes(6, 'big')
        else:
            self.mac_address = '?'

    @staticmethod
    def connect(unused_ssid, unused_wifi_password):
        C.log('wifi.connect called')
        time.sleep(1)

# Singleton class instance.
radio = Radio()
