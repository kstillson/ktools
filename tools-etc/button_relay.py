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


# ---------- control constants

LOW_BATTERY_THRESHOLD = 4000


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
            C.log_info(f'choosing first of multiple serial ports: [found]')
            return found[0]
        if not sent_warning:
            C.log_info('waiting for serial port to be attached');
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
        C.log(f'sent to serial due to get request: {send_request}')
        sput(SERIAL_PORT, send_request)
        return 'sent'
    button_test = request.get_params.get('b')
    if button_test:
        rslt = handle_button_real(stoi(button_test), -1, 'na')
        C.log(f'button test {button_test} -> {rslt}')
        return rslt
    return H.html_page_wrap('<li><a href="varz">varz</a><br/><li><a href="healthz">healthz</a>')

def handler_healthz(request):
    return HEALTHZ_STATUS

def handler_noop(request): return None


# ---------- general helpers

def control(target, command='on'):
    url = f'http://web/control/{target}/{command}'
    return C.read_web(url, timeout=5)

def speak(msg):
    url = 'http://pi1/speak/' + C.quote_plus(msg)
    return C.read_web_e(url, timeout=5)

def stoi(s):
    s = s.replace(',', '').strip()
    return int(s) if s.isdigit() else -1

def trigger(trigger):
    path0 = '/trigger/' + trigger
    token = A.generate_token(path0)
    path = path0 + '?a2=' + token
    return C.read_web_e('http://homesecdock:1111' + path)


# ---------- business logic


def parse_button_msg(msg):  # format:    button: xx, voltage: yy, mac: aabbccddeeff
                            #            0       1   2        3   4    5
    parts = msg.split(' ')
    button = stoi(parts[1])
    battery = stoi(parts[3])
    mac = parts[5].strip()
    return button, battery, mac


def handle_button_real(button, battery, mac):
    V.bump(f'button_{button}')
    V.bump(f'mac_{mac}')

    if battery > 0 and battery < LOW_BATTERY_THRESHOLD:
        C.log_warning(f'low battery level on {mac}: {battery} < {LOW_BATTERY_THRESHOLD}')
        V.bump(f'low_batt_{mac}')

    # testing buttons (MAC independents)
    if button == 99: return speak('greetings professor falcon')
    if button == 98: return trigger('test')

    # sender specific buttons
    if mac == '84F73D97E46':   # qt py esp32-s2 single button, tv mode
       if button == 17: return control('tv')

    # If we get to here, unknown sender or unknown button
    C.log_error(f'unknown button {button} from {mac}')
    V.bump('unknown_button')
    return False


def handle_button(msg):
    try:
        button, battery, mac = parse_button_msg(msg)
        return handle_button_real(button, battery, mac)
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
        if got.startswith('button'):
            # oops; got a button push when expecting a ping response; forard it.
            # no opinion on healthz status update; leave it untouched.
            return handle_button(got)
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
            if line.startswith('button:'):
                rslt = handle_button(line)
                C.log(f'{line} -> {rslt}')
            else:
                C.log(f'unprocessed input: {line}')
        if now() > next_ping:
            next_ping = now() + args.ping_freq
            if not ping(s):
                C.log_warning(f'ping fail: {HEALTHZ_STATUS}')
                return
        time.sleep(0.5)  # never loop too fast.


def main(argv=[]):
    args = parse_args(argv or sys.argv[1:])

    C.init_log(log_title='button relay', logfile=args.logfile, filter_level_syslog=C.WARNING)
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
