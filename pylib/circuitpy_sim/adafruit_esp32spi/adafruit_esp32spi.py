
class Esp:
    def __init__(self):
        self.ssid = b'ssid'
        self.rssi = 'rssi'
    def is_connected(): return True
    def connect_AP(ssid, password): return True
    
    
#B#class Adafruit_esp32spi:
#    def ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset):
#        return Esp()
#adafruit_esp32spi = Adafruit_esp32spi()


def ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset):
    return Esp()



class Adafruit_esp32spi_socket:
    def set_interface(esp): pass

adafruit_esp32spi_socket = Adafruit_esp32spi_socket()
