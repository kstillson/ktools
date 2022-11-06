#!/usr/bin/python3
'''Relay signals from a serial port to web requests.

I've got an Arduino-based microcontroller listening for "espnow" messages for
general-use IoT buttons.  I really prefer Python to C++ / Arduino scripting,
and the board has very limited capabilities anyway.  So rather that trying to
get that board doing fancy simultaneous espnow and WiFi to report button
pushes, it simply reports events to the serial port.  This script watches that
port and relays the information about things like button presses out to the
rest of my network.

Like everything, this has a webserver with /healthz and /varz handlers that
allow it to be efficiently monitored, and is integrated with kAuth, so we can
send authenticated homesec triggers and the like.

'''

import glob, serial, sys, time

import kcore.auth as A
import kcore.common as C
import kcore.html as H
import kcore.uncommon as UC
import kcore.webserver as W
import kcore.varz as V


# ---------- global state

HEALTHZ_STATUS = 'No ping yet'
SERIAL_PORT = None


# ---------- serial port helpers

def find_serial_dev():
    sent_warning = False
    while True:
        found = glob.glob('/dev/ttyUSB*')
        if len(found) == 1: return found[0]
        if len(found) > 1:
            C.log_warning(f'choosing first of multiple serial ports: [found]')
            return found[0]
        if not sent_warning:
            C.log_warning('waiting for serial port to be attached');
            sent_warning = True
        time.sleep(3)  # never loop too fast.


def setup_serial(dev_name=None):
    if not dev_name: dev_name = find_serial_dev()
    port = serial.Serial(port=dev_name, baudrate=115200, bytesize=8, timeout=2, stopbits=serial.STOPBITS_ONE)
    C.log(f'monitoring {dev_name}')
    global SERIAL_PORT
    SERIAL_PORT = port
    return port


def sget(s): return s.readline().decode('UTF-8').strip()

def sput(s, msg): return s.write(msg.encode('UTF-8'))


# ---------- web handlers

def handler_default(request):
    send_request = request.get_params.get('send')
    if send_request:
        sput(SERIAL_PORT, send_request)
        return 'sent'
    return H.html_page_wrap('<li><a href="varz">varz</a><br/><li><a href="healthz">healthz</a>')

def handler_healthz(request):
    return HEALTHZ_STATUS

def handler_noop(request): return None


# ---------- business logic

def speak(msg):
    url = C.quote_plus('http://pi1/speak/' + msg)
    return C.read_web(url, timeout=5)


def handle_button_real(msg):  # format:    button: xx, mac: xx:xx:xx:xx:xx:xx
    parts = msg.split(' ')
    button_str = parts[1].replace(',', '')
    button = int(button_str) if button_str.isdigit() else -1
    mac = parts[3]
    V.bump(f'button_{button}')
    V.bump(f'mac_{mac}')

    if   button == 10: return speak('saw button')
    elif button == 11: return speak('saw button d0')
    elif button == 12:
        path0 = '/trigger/test'
        token = A.generate_token(path0)
        path = path0 + '?a2=' + token
        return C.read_web('http://jack:1111/' + path)
    else:
        C.log_warning(f'processed unknown button: {button}')
        V.bump('unknown_button')
        return None


def handle_button(msg):
    try:
        return handle_button_real(msg)
    except Exception as e:
        V.bump('handle_button_exception')
        C.log_error(f'exception during button processing: {str(e)}')


def now(): return int(time.time())


def ping(s):
    global HEALTHZ_STATUS
    sput(s, '?\n')
    got = sget(s)
    if not got:
        HEALTHZ_STATUS = 'ERROR: no response from ping'
        V.bump('ping-fail')
        return False
    elif got == 'hello!':
        HEALTHZ_STATUS = 'ok'
        V.bump('ping-success')
        return True
    else:
        HEALTHZ_STATUS = f'ERROR: unknown ping response: {got}'
        V.bump('ping-fail')
        return False


# ---------- main

def parse_args(argv):
    ap = UC.argparse_epilog(argv)
    ap.add_argument('--logfile',   '-l',  default='-')
    ap.add_argument('--ping_freq', '-P',  default=20,   type=int, help='ping every this many seconds')
    ap.add_argument('--port',      '-p',  default=8080, type=int, help='webserver port')
    ap.add_argument('--serial',    '-s',  default=None, help='serial port to monitor; default will auto-search /dev/ttyUSB* and wait if needed')
    return ap.parse_args(argv)


HANDLERS = {
    '/healthz': handler_healthz,
    '/favicon.ico': handler_noop,
    None: handler_default,
}


def serial_listen_loop(s, args):
    next_ping = 0
    while True:
        line = sget(s)
        if line:
            C.log(line)
            if line.startswith('button'): handle_button(line)
        if now() > next_ping:
            next_ping = now() + args.ping_freq
            if not ping(s):
                C.log_error(f'ping fail: {HEALTHZ_STATUS}')
                return
        time.sleep(0.5)  # never loop too fast.


def main(argv=[]):
    args = parse_args(argv or sys.argv[1:])

    C.init_log(log_title='button relay', logfile=args.logfile)
    W.WebServer(port=args.port, handlers=HANDLERS).start()

    while True:
        try:
            s = setup_serial(args.serial)
            serial_listen_loop(s, args)
        except Exception as e:
            C.log_error(f'exception during processing: {str(e)}')
        time.sleep(3)  # never loop too fast.


if __name__ == '__main__':
    main()
