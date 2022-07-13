'''This is part of circuitpy_sim.  See README-circuitpy.md for details.'''

import socket

class SocketPool:
    def __init__(self, __unused_radio):
        pass

    @staticmethod
    def socket():
        return socket.socket(socket.AF_INET, socket.SOCK_STREAM)
