
import socket, sys, uuid
import circpysim_logging as L

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
        L.log('wifi.connect called')

# Singleton class instance.
radio = Radio()
