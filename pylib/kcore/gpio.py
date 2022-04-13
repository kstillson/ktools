'''GPIO abstraction for Raspberry PI's (not Circuit Python)

Requires the package "python3-rpi.gpio" to be installed, at least when not in
simulation mode.
'''

import atexit, signal, sys, threading, time
import kcore.varz as V


# ---------- global stats

SIMULATION = False

SIM_BUTTONS = {}  # pin -> Bool
SIM_LEDS = {}     # pin -> Bool


# ---------- init and cleanup

def init(simulation=False):
    if simulation:
        global SIMULATION
        SIMULATION = True
        return simout('gpio initialized in simulation mode')
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BOARD)
    signal.signal(signal.SIGTERM, my_atexit)
    atexit.register(my_atexit)

    
def my_atexit(signum=None, frame=None):
    if not SIMULATION: GPIO.cleanup()
    sys.exit()


# --------------------
# General support

def millis(): return int(1000 * time.time())

def simout(msg): print(msg, file=sys.stderr)


# --------------------
# passthru's

def input(pin):
    if SIMULATION: return SIM_BUTTONS.get(pin, True)
    return GPIO.input(pin)


# --------------------
# Python GPIO abstraction

class KButton(object):
    def __init__(self, pin, func=None, background=False,
                 float_high=True, detect_fall=True,
                 bounce=1000, require_pressed=50):
        '''Button abstraction.'''
        self._background = background
        self._float_value = float_high
        self._pin = pin
        self._func = func or self._internal
        self._require_pressed = require_pressed
        if SIMULATION:
            SIM_BUTTONS[pin] = self._float_value
            return
        GPIO.setup(pin, GPIO.IN,
            pull_up_down=GPIO.PUD_UP if self._float_value else GPIO.PUD_DOWN)
        GPIO.add_event_detect(pin,
            GPIO.FALLING if detect_fall else GPIO.RISING,
            callback=self._pressed, bouncetime=bounce)

    def __del__(self): self.disable()
    
    def disable(self):
        if not SIMULATION: GPIO.remove_event_detect(self._pin)

    def simulate_press(self, new_state=False, duration=200):
        if not SIMULATION: raise RuntimeException('cannot simulate button press when not in simulation mode.')
        if self._float_value and new_state: return simout('button on pin %d: press high and float high => no-op' % self._pin)
        if not self._float_value and not new_state: return simout('button on pin %d: press low and float low => no-op' % self._pin)
        SIM_BUTTONS[self._pin] = new_state
        threading.Timer(duration / 1000.0, self.simulate_unpress).start()
        simout('button on pin %d set %s for %d ms.' % (self._pin, new_state, duration))
        return self._pressed(self._pin)

    def simulate_unpress(self):
        SIM_BUTTONS[self._pin] = self._float_value
        return simout('button on pin %s unpressed (back to %s)' % (self._pin, self._float_value))
        
    def value(self):
        if SIMULATION: return SIM_BUTTONS.get(self._pin, True)
        return GPIO.input(self._pin)
    
    def _internal(pin): print('Button pressed: %s' % pin)
    
    def _pressed(self, pin):
        if self._require_pressed:
            start_val = self.value()
            sample_time = (self._require_pressed / 1000.0) / 5.0
            for sample in range(5):
                time.sleep(sample_time)
                if self.value() != start_val:
                    V.bump('dropped-unsustained-pin-%s' % pin)
                    return False
        V.bump('sensor-pin-%d' % pin)
        V.stamp('sensor-pin-%d-stamp' % pin)
        if self._background:
            t = threading.Thread(target=self._func, args=(pin,))
            t.daemon = True
            t.start()
            return True
        else:
            return self._func(pin)


class KLed(object):
    def __init__(self, pin):
        self._pin = pin
        if not SIMULATION: GPIO.setup(pin, GPIO.OUT)
        self.off()

    def get(self):
        if SIMULATION: return SIM_LEDS.get(self._pin, False)
        return GPIO.input(self._pin)

    def set(self, new_state):
        if SIMULATION:
            SIM_LEDS[self._pin] = new_state
            return simout('LED on pin %d set to %s' % (self._pin, new_state))
        GPIO.output(self._pin, new_state)

    def toggle(self): self.set(0 if self.get() else 1)

    def off(self): self.set(0)
    def on(self): self.set(1)
    def low(self): self.set(0)
    def hi(self): self.set(1)


class KDualLed(object):
    '''Red/Green LED abstraction.'''
    def __init__(self, red_pin, green_pin):
        self._red_pin = red_pin
        self._green_pin = green_pin
        if not SIMULATION:
            GPIO.setup(red_pin, GPIO.OUT)
            GPIO.setup(green_pin, GPIO.OUT)
        self.off()

    def set(self, red_status, green_status):
        if SIMULATION:
            SIM_LEDS[self._red_pin] = red_status
            SIM_LEDS[self._green_pin] = green_status
            return simout('set pin %d to %d and %d to %d.' % (self._red_pin, red_status, self._green_pin, green_status))
        GPIO.output(self._red_pin, red_status)
        GPIO.output(self._green_pin, green_status)

    def off(self): self.set(0, 0)
    def red(self): self.set(1, 0)
    def green(self): self.set(0, 1)
    def yellow(self): self.set(1, 1)
