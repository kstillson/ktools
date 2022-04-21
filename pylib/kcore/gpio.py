'''GPIO abstraction for Raspberry PI's (not Circuit Python)

TODO: generalize so works in all the same modes as neo.py

Requires the package "python3-rpi.gpio" to be installed, at least when not in
simulation mode.
'''

import atexit, signal, sys, threading, time
from dataclasses import dataclass
import kcore.common as C
import kcore.varz as V


SIMULATION = False
try:
    import RPi.GPIO as GPIO
except ModuleNotFoundError:
    sys.stderr.write('Unable to import RPi.GPIO; entering simulation mode.\n')
    SIMULATION = True


# ---------- useful global constants

@dataclass
class PinMap:
    bcm_name: str
    bcm: int
    board: int

PIN_MAPPINGS = {
    'raspberry_pi': [
        #      name     bcm#   board#
        PinMap('D0',    0,     None),
        PinMap('D1',    1,     None),
        PinMap('3v',    None,  1),
        PinMap('5v',    None,  2),
        PinMap('D2',    2,     3),
        PinMap('SDA',   2,     3),
        PinMap('5v#2',  None,  4),
        PinMap('D3',    3,     5),
        PinMap('SCL',   3,     5),
        PinMap('gnd',   None,  6),
        PinMap('D4',    4,     7),
        PinMap('D14',   14,    8),
        PinMap('TX',    14,    8),
        PinMap('TXD',   14,    8),
        PinMap('gnd#2', None,  9),
        PinMap('D15',   15,    10),
        PinMap('RX',    15     10),
        PinMap('RXD',   15,    10),
        PinMap('D17',   17,    11),
        PinMap('D18',   18,    12),
        PinMap('D27',   27,    13),
        PinMap('gnd#3', None,  14),
        PinMap('D22',   22,    15),
        PinMap('D23',   23,    16),
        PinMap('3v#2',  None,  17),
        PinMap('D24',   24,    18),
        PinMap('D10',   10,    19),
        PinMap('MOSI',  10,    19),
        PinMap('gnd#4', None,  20),
        PinMap('D9',    9,     21),
        PinMap('MISO',  9,     21),
        PinMap('D25',   25,    22),
        PinMap('D11',   11,    23),
        PinMap('SCK',   11,    23),
        PinMap('SCLK',  11,    23),
        PinMap('CE0',   8,     24),
        PinMap('D8',    8,     24),
        PinMap('gnd#5', None,  25),
        PinMap('CE1',   7,     26),
        PinMap('D7',    7,     26),
        PinMap('id_sd', None,  27),
        PinMap('id_sc', None,  28),
        PinMap('D5',    5,     29),
        PinMap('gnd#6', None,  30),
        PinMap('D6',    6,     31),
        PinMap('D12',   12,    32),
        PinMap('D13',   13,    33),
        PinMap('gnd#7', None,  34),
        PinMap('D19',   19,    35),
        PinMap('MISO_1',19,    35),
        PinMap('D16',   16,    36),
        PinMap('D26',   26,    37),
        PinMap('D20',   20,    38),
        PinMap('MOSI_1',20,    38),
        PinMap('gnd#7', None,  39),
        PinMap('D21'    21,    40),
        PinMap('SCK_1', 21,    40),
        PinMap('SCLK_1',21,    40) ],
    }


# ---------- global state

SIM_BUTTONS = {}  # bcm pin# (int) -> Bool
SIM_LEDS = {}     # bcm pin# (int) -> Bool


# ---------- init and cleanup

def init(simulation=False):
    if simulation:
        global SIMULATION
        SIMULATION = True
        return simout('gpio initialized in simulation mode')
    # <rant> Personally, I've always preferred GPIO.BOARD, as I care a great
    # deal about where to plug the wire in, and very little about some
    # arbitrary numbering system that doesn't effect anything.  However,
    # RPi.GPIO throws a fatal exception if two calls are made to setmode()
    # with different values, and Adafruit's "board" module (which is necessary
    # for things like Neopixels) calls setmode() with GPIO.BCM upon import of
    # the module.  So now anything that wants to work with Neopixles is forced
    # to re-write all their software to use BCM mode.  And when someday some
    # other necessary library picks BOARD mode, well, the world will just come
    # crashing down. </rant>
    GPIO.setmode(GPIO.BCM)
    signal.signal(signal.SIGTERM, my_atexit)
    atexit.register(my_atexit)


def my_atexit(signum=None, frame=None):
    if not SIMULATION: GPIO.cleanup()
    sys.exit()


# --------------------
# General support

def millis(): return int(1000 * time.time())

def simout(msg): sys.stderr.write(msg + '\n')


# --------------------
# passthru's

def input(bcm_pin: int):
    if SIMULATION: return SIM_BUTTONS.get(bcm_pin, True)
    return GPIO.input(bcm_pin)


# --------------------
# Python GPIO abstraction

class KButton(object):
    def __init__(self, bcm_pin, func=None, name='?', log=False,
                 background=False, normally_high=True, pull_float_high=True,
                 debounce_ms=1000, require_pressed_ms=150):
        '''Button abstraction.'''
        self._background = background
        self._normally_high = normally_high
        self._bcm_pin = bcm_pin
        self._name = '%d(%s)' % (bcm_pin, name)
        self._log = log
        self._func = func or self._internal
        self._require_pressed_ms = require_pressed_ms
        if SIMULATION:
            SIM_BUTTONS[bcm_pin] = self._normally_high
            return
        GPIO.setup(bcm_pin, GPIO.IN,
            pull_up_down=GPIO.PUD_UP if pull_float_high else GPIO.PUD_DOWN)
        GPIO.add_event_detect(bcm_pin,
            GPIO.FALLING if normally_high else GPIO.RISING,
            callback=self._pressed, bouncetime=debounce_ms)
        if log: C.log('set up bcm_pin %s for normally %s' % (self._name, normally_high))

    def disable(self):
        if SIMULATION: return
        if self._log: C.log('disabling events for bcm_pin ' + self._name)
        GPIO.remove_event_detect(self._bcm_pin)

    def simulate_press(self, new_state=False, duration=200):
        if not SIMULATION: raise RuntimeException('cannot simulate button press when not in simulation mode.')
        if self._log: C.log('simulated push on %s to state %s for %s' % (self._name, new_state, duration))
        if self._normally_high and new_state: return simout('button on bcm_pin %d: press high and float high => no-op' % self._bcm_pin)
        if not self._normally_high and not new_state: return simout('button on bcm_pin %d: press low and float low => no-op' % self._bcm_pin)
        SIM_BUTTONS[self._bcm_pin] = new_state
        threading.Timer(duration / 1000.0, self.simulate_unpress).start()
        simout('button on bcm_pin %d set %s for %d ms.' % (self._bcm_pin, new_state, duration))
        return self._pressed(self._bcm_pin)

    def simulate_unpress(self):
        SIM_BUTTONS[self._bcm_pin] = self._normally_high
        return simout('button on bcm_pin %s unpressed (back to %s)' % (self._bcm_pin, self._normally_high))

    def value(self):
        if SIMULATION: return SIM_BUTTONS.get(self._bcm_pin, True)
        return GPIO.input(self._bcm_pin)

    def _internal(self, bcm_pin): print('Button pressed: %s' % bcm_pin)

    def _pressed(self, bcm_pin):
        if self._log: C.log('KButton event triggered for: ' + self._name)
        if self._background:
            t = threading.Thread(target=self._pressed2, args=(bcm_pin,))
            t.daemon = True
            t.start()
            return True
        else:
            return self._func(bcm_pin)

    def _pressed2(self, bcm_pin):
        if self._require_pressed_ms:
            samples = 5
            sample_time = (self._require_pressed_ms / 1000.0) / samples
            for sample in range(samples):
                time.sleep(sample_time)
                if self.value() == self._normally_high:
                    if self._log: C.log('dropped unsustained bcm_pin %s on sample %d' % (self._name, sample))
                    V.bump('dropped-unsustained-bcm_pin-%s' % self._name)
                    return False
        V.bump('count-sensor-bcm_pin-%s' % self._name)
        V.stamp('sensor-bcm_pin-%s-stamp' % self._name)
        return self._func(bcm_pin)


class KLed(object):
    def __init__(self, bcm_pin):
        self._bcm_pin = bcm_pin
        if not SIMULATION: GPIO.setup(bcm_pin, GPIO.OUT)
        self.off()

    def get(self):
        if SIMULATION: return SIM_LEDS.get(self._bcm_pin, False)
        return GPIO.input(self._bcm_pin)

    def set(self, new_state):
        if SIMULATION:
            SIM_LEDS[self._bcm_pin] = new_state
            return simout('LED on bcm_pin %d set to %s' % (self._bcm_pin, new_state))
        GPIO.output(self._bcm_pin, new_state)

    def toggle(self): self.set(0 if self.get() else 1)

    def off(self): self.set(0)
    def on(self): self.set(1)
    def low(self): self.set(0)
    def hi(self): self.set(1)


class KDualLed(object):
    '''Red/Green LED abstraction.'''
    def __init__(self, red_bcm_pin, green_bcm_pin):
        self._red_bcm_pin = red_bcm_pin
        self._green_bcm_pin = green_bcm_pin
        if not SIMULATION:
            GPIO.setup(red_bcm_pin, GPIO.OUT)
            GPIO.setup(green_bcm_pin, GPIO.OUT)
        self.off()

    def set(self, red_status, green_status):
        if SIMULATION:
            SIM_LEDS[self._red_bcm_pin] = red_status
            SIM_LEDS[self._green_bcm_pin] = green_status
            return simout('set bcm_pin %d to %d and %d to %d.' % (self._red_bcm_pin, red_status, self._green_bcm_pin, green_status))
        GPIO.output(self._red_bcm_pin, red_status)
        GPIO.output(self._green_bcm_pin, green_status)

    def off(self): self.set(0, 0)
    def red(self): self.set(1, 0)
    def green(self): self.set(0, 1)
    def yellow(self): self.set(1, 1)

