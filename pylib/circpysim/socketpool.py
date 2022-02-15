
import socket

class SocketPool:
    def __init__(self, __unused_radio):
        pass

    @staticmethod
    def socket():
        return socket.socket(socket.AF_INET, socket.SOCK_STREAM)
