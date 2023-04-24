#!/usr/bin/python3

import time
import kcore.webserver as W

VALUE = 'all ok'

def h_default(request):
    v = request.get_params.get('v')
    if v:
        global VALUE
        VALUE = v
    return VALUE

print('dummy server starting')
W.WebServer(port=1234, use_standard_handlers=False, handlers={None: h_default}).start()
print('dummy server stopping')
time.sleep(60)
