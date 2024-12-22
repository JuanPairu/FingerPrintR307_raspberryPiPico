import time
import network
def do_connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():

        wlan.connect('RedmiA3x','12345678')

        while wlan.isconnected() == False:
            time.sleep(0.5)
