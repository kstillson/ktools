'''GPIO abstraction for Raspberry PI's (not Circuit Python)

TODO: more doc

This module supports 3 modes of operation:
 - Running on a Raspberry PI via the RPi.GPIO library.
   (sudo apt-get install python3-rpi.gpio)
 - Running on a Circuit Python board using the digitalio library.
 - Running with simulation=True passed to init(), which is
   "headless" (an all in-memory simulation).

It tries to provide the same API for each mode, *HOWEVER* Circuit Python
doesn't have threading, so instead it uses an event queuing model and
cooperative multi-tasking, and the caller must regularly (ideally multiple
times a second) call the check() method to run any pending actions.

In simulation mode, bcm_pin's should be an int.
For CircuitPython, they must be an instance from the board.* module
For RPi, they can be either of those.

TODO: add support for:
 - Running using ../circuitpy_sim, which uses tkinter to draw simulated
   graphical buttons on a Linux workstation

'''

import atexit, os, sys, time
import kcore.common as C
import kcore.time_queue as TQ
import kcore.varz as V

CIRCUITPYTHON = 'boot_out.txt' in os.listdir('/')
SIMULATION = False

if CIRCUITPYTHON:
    import digitalio
else:
    import signal, threading
    try:
        import RPi.GPIO as GPIO
    except ModuleNotFoundError:
        C.stderr('Unable to import RPi.GPIO; entering simulation mode.')
        SIMULATION = True


# ---------- global state

SIM_BUTTONS = {}  # bcm pin# (int) -> Bool
SIM_LEDS = {}     # bcm pin# (int) -> Bool


# ---------- init and cleanup

def init(simulation=False):
    if simulation:
        global SIMULATION
        SIMULATION = True
        return simout('gpio initialized in simulation mode')
    if not CIRCUITPYTHON:
        atexit.register(rpi_atexit)
        signal.signal(signal.SIGTERM, rpi_atexit)
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


def rpi_atexit(signum=None, frame=None):
    if SIMULATION or CIRCUITPYTHON: return
    GPIO.cleanup()


# --------------------
# General support

def simout(msg): C.stderr(msg)


# --------------------
# passthru's


def input(bcm_pin):  # Returns bool (even for RPi, which usually returns int 1 or 0)
    if SIMULATION: return SIM_BUTTONS.get(bcm_pin, True)
    elif CIRCUITPYTHON:
        dio = digitalio.DigitalInOut(bcm_pin)
        return dio.value
    else:
        return GPIO.input(bcm_pin) == 1


# --------------------
# Python GPIO input abstraction

class KButton:
    def __init__(self, bcm_pin, func=None, name='?', log=False,
                 background=True, normally_high=True, pull_float_high=True,
                 debounce_ms=1000, require_pressed_ms=100):
        '''Button abstraction.'''

        # ----- sanity checks

        if CIRCUITPYTHON and background:
            background = False
            C.log_warning('KButton: Background mode disabled: not available in Circuit Python')
        if not CIRCUITPYTHON and require_pressed_ms and not background:
            require_pressed_ms = 0
            C.log_warning('KButton: require_pressed_ms disabled without background mode')

        # ----- init internal state

        self._background = background
        self._bcm_pin = bcm_pin
        self._debounce_ms = debounce_ms
        self._event_queue = TQ.TimeQueue()   # Only used in Circuit Python mode.
        self._func = func or self._internal_press_func
        self._name = '%s(%s)' % (bcm_pin, name)
        self._normally_high = normally_high
        self._last_press = 0
        self._log = log
        self._require_pressed_ms = require_pressed_ms

        if SIMULATION:
            SIM_BUTTONS[bcm_pin] = self._normally_high

        elif CIRCUITPYTHON:
            self._dio = digitalio.DigitalInOut(bcm_pin)
            self._dio.direction = digitalio.Direction.INPUT
            self._dio.pull = digitalio.Pull.UP if pull_float_high else digitalio.Pull.Down

        else: # RPi
            GPIO.setup(bcm_pin, GPIO.IN,
                       pull_up_down=GPIO.PUD_UP if pull_float_high else GPIO.PUD_DOWN)
            GPIO.add_event_detect(bcm_pin,
                                  GPIO.FALLING if normally_high else GPIO.RISING,
                                  callback=self._pressed1, bouncetime=debounce_ms)

        if log: C.log('set up bcm_pin %s for normally %s' % (self._name, normally_high))

    def check(self):
        if not CIRCUITPYTHON: return -1
        return self._event_queue.check()

    def disable(self):
        if self._log: C.log('disabling events for KButton ' + self._name)
        if SIMULATION:
            return
        elif CIRCUITPYTHON:
            self._dio.deinit()
            self._dio = None
        else: # Rpi
            GPIO.remove_event_detect(self._bcm_pin)

    def simulate_press(self, duration_ms=200):
        if not SIMULATION: raise RuntimeError('cannot simulate button press when not in simulation mode.')
        new_state = not self._normally_high
        if self._log: C.log('simulated push on %s to state %s for %s' % (self._name, new_state, duration_ms))
        SIM_BUTTONS[self._bcm_pin] = new_state
        threading.Timer(duration_ms / 1000.0, self.simulate_unpress).start()
        simout('button on bcm_pin %d set %s for %d ms.' % (self._bcm_pin, new_state, duration_ms))
        return self._pressed1(self._bcm_pin)

    def simulate_unpress(self):
        SIM_BUTTONS[self._bcm_pin] = self._normally_high
        return simout('button on bcm_pin %s unpressed (back to %s)' % (self._bcm_pin, self._normally_high))

    def value(self):   # Returns bool (even for RPi, which usually returns int 1 or 0)
        if SIMULATION: return SIM_BUTTONS.get(self._bcm_pin, True)
        elif CIRCUITPYTHON: return self._dio.value
        else: return GPIO.input(self._bcm_pin) == 1 # RPi

    # ----- internals

    def _internal_press_func(self, bcm_pin): print('Button pressed: %s' % bcm_pin)

    # 1st stage: check for debounce filtering, then either launch required
    # duration check in the background, or jump right to the callback.
    def _pressed1(self, bcm_pin):
        if self._debounce_ms:
            if TQ.now_in_ms() - self._last_press < self._debounce_ms:
                V.bump('count-sensor-debounced-%s' % self._name)
                if self._log: C.log('KButton debounce ignored: ' + self._name)
                return False
        if CIRCUITPYTHON:
            # TODO: multiple samples...?
            evt = TQ.Event(self._require_pressed_ms, self._pressed2_circpy, [bcm_pin])
            self._event_queue.add_event(evt)
            return True
        if self._background:
            t = threading.Thread(target=self._pressed2, args=(bcm_pin,))
            t.daemon = True
            t.start()
            return True
        else:
            return self._pressed3(bcm_pin)

    # 2nd stage: intended to be run a background thread.  Re-sample the button
    # a few times during the required_press_ms period, and filter it if needed.
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
        return self._pressed3(bcm_pin)

    # 2nd stage alternative mode for circuit python.  This activates after
    # require_pressed_ms, so just verify the button is still pressed.
    def _pressed2_circpy(self, bcm_pin):
        if self.value() == self._normally_high:
            if self._log: C.log('dropped unsustained bcm_pin %s' % (self._name))
            V.bump('dropped-unsustained-bcm_pin-%s' % self._name)
            return False
        return self._pressed3(bcm_pin)

    # 3rd stage: log, varz, and actually process the button's callback.
    def _pressed3(self, bcm_pin):
        self._last_press = TQ.now_in_ms()
        if self._log: C.log('KButton event triggered for: ' + self._name)
        V.bump('count-sensor-bcm_pin-%s' % self._name)
        V.stamp('sensor-bcm_pin-%s-stamp' % self._name)
        return self._func(bcm_pin)


class KLed:
    def __init__(self, bcm_pin):
        self._bcm_pin = bcm_pin
        if SIMULATION:
            pass
        elif CIRCUITPYTHON:
            self._dio = digitalio.DigitalInOut(bcm_pin, direction=digitalio.OUTPUT)
        else:
            GPIO.setup(bcm_pin, GPIO.OUT)
        self.set(0)

    def get(self):
        return SIM_LEDS.get(self._bcm_pin, False)

    def set(self, new_state):
        if SIMULATION:
            SIM_LEDS[self._bcm_pin] = new_state
            return simout('LED on bcm_pin %d set to %s' % (self._bcm_pin, new_state))
        elif CIRCUITPYTHON:
            self._dio = new_state
        else:
            GPIO.output(self._bcm_pin, new_state)

    def toggle(self): self.set(0 if self.get() else 1)

    def off(self): self.set(0)
    def on(self): self.set(1)
    def low(self): self.set(0)
    def hi(self): self.set(1)


class KDualLed:
    '''Red/Green LED abstraction.'''
    def __init__(self, red_bcm_pin, green_bcm_pin):
        self._red = KLed(red_bcm_pin)
        self._green = KLed(green_bcm_pin)
        self.off()

    def set(self, red_status, green_status):
        self._red.set(red_status)
        self._green.set(green_status)

    def off(self): self.set(0, 0)
    def red(self): self.set(1, 0)
    def green(self): self.set(0, 1)
    def yellow(self): self.set(1, 1)
