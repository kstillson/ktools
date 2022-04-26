'''
This file adapted from:
https://circuitpython.readthedocs.io/projects/requests/en/latest/examples.html
by Ken Stillson

Tweaked so as to work as a unittest under circuitpy-sim's adafruit_requests.

(changes basically are adding the path injection to load circuitpy_sim,
 moving the whole thing into a test function, and changing so that rather
 than just dumping output to stdout, a series of assert statements check
 that the results are approximately right).

What is this test doing?  circuitpy_sim emulates the circuit python API
by mapping it into standard CPython calls.  This test is a client of the
circuit python API, specifically "adafruit_requests".  It calls the
API to make real-live requests out to the Internet and checks the results.

If this test passes, it indicates that the circuitpy_sim's mapping of
adafruit_requests API is sufficiently good as to fool this client program

--------------------------------------------------
'''

# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT


import os, sys
CIRCUITPYTHON = 'boot_out.txt' in os.listdir('/')
if not CIRCUITPYTHON: sys.path.insert(0, 'circuitpy_sim')


# adafruit_requests usage with an esp32spi_socket
import board
import busio
from digitalio import DigitalInOut
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
from adafruit_esp32spi import adafruit_esp32spi
import adafruit_requests as requests


def test_adafruit_requests_under_circuitpy_sim():
    
    # If you are using a board with pre-defined ESP32 Pins:
    esp32_cs = DigitalInOut(board.ESP_CS)
    esp32_ready = DigitalInOut(board.ESP_BUSY)
    esp32_reset = DigitalInOut(board.ESP_RESET)
    
    # If you have an externally connected ESP32:
    # esp32_cs = DigitalInOut(board.D9)
    # esp32_ready = DigitalInOut(board.D10)
    # esp32_reset = DigitalInOut(board.D5)
    
    # If you have an AirLift Featherwing or ItsyBitsy Airlift:
    # esp32_cs = DigitalInOut(board.D13)
    # esp32_ready = DigitalInOut(board.D11)
    # esp32_reset = DigitalInOut(board.D12)
    
    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
    
    print("Connecting to AP...")
    while not esp.is_connected:
        try:
            esp.connect_AP("ssid", "password")
        except RuntimeError as e:
            print("could not connect to AP, retrying: ", e)
            continue
    print("Connected to", str(esp.ssid, "utf-8"), "\tRSSI:", esp.rssi)
    
    # Initialize a requests object with a socket and esp32spi interface
    socket.set_interface(esp)
    requests.set_socket(socket, esp)
    
    TEXT_URL = "http://wifitest.adafruit.com/testwifi/index.html"
    JSON_GET_URL = "https://httpbin.org/get"
    JSON_POST_URL = "https://httpbin.org/post"

    print("Fetching text from %s" % TEXT_URL)
    response = requests.get(TEXT_URL)
    assert 'If you can read this, its working :)' in response.text
    response.close()
    
    print("Fetching JSON data from %s" % JSON_GET_URL)
    response = requests.get(JSON_GET_URL)
    assert response.json()['url'] == JSON_GET_URL
    response.close()
    
    data = "31F"
    print("POSTing data to {0}: {1}".format(JSON_POST_URL, data))
    response = requests.post(JSON_POST_URL, data=data)
    json_resp = response.json()
    assert json_resp["data"] == '31F'
    response.close()
    
    json_data = {"Date": "July 25, 2019"}
    print("POSTing data to {0}: {1}".format(JSON_POST_URL, json_data))
    response = requests.post(JSON_POST_URL, json=json_data)
    json_resp = response.json()
    assert json_resp["json"]['Date'] == 'July 25, 2019'
    response.close()
    
