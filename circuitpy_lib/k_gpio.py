
import atexit, signal, sys, time
import RPi.GPIO as GPIO

# --------------------
# Make sure to run GPIO cleanup upon exit.

RAN_INIT = False

def init():
    GPIO.setmode(GPIO.BOARD)
    signal.signal(signal.SIGTERM, my_atexit)
    atexit.register(my_atexit)
    global RAN_INIT
    RAN_INIT = True
    
def my_atexit(signum=None, frame=None):
    GPIO.cleanup()
    sys.exit()


# --------------------
# General support

def millis(): return int(1000 * time.time())

# --------------------
# passthru's

def input(pin): return GPIO.input(pin)


# --------------------
# Python GPIO abstraction

'''Button abstraction.  Derive a subclass and define pressed(pin), or
   supply a replacement in the constructor.
   Must call GPIO.setmode() before instanciating,
   should call GPIO.cleanup() once done.
'''
class KButton(object):
    def __init__(self, pin, float_high=True, detect_fall=True, bounce=1200, func=None):
        if not func: func = self._internal
        self._pin = pin
        self._bounce = bounce
        self._func = func
        self._last_press = 0
        GPIO.setup(
            pin, GPIO.IN,
            pull_up_down=GPIO.PUD_UP if float_high else GPIO.PUD_DOWN)
        GPIO.add_event_detect(
            pin,
            GPIO.FALLING if detect_fall else GPIO.RISING,
            callback=self._pressed, bouncetime=bounce)

    def __del__(self): self.disable()

    def disable(self): GPIO.remove_event_detect(self._pin)

    def value(self):
        return GPIO.input(self._pin)

    def _internal(pin): print('Button pressed: %s' % pin)

    def _pressed(self, pin):
        delta = millis() - self._last_press
        if delta < self._bounce:
            print('Ignoring bounced button press.  %d < %d' % (delta, self._bounce))
            return
        self._last_press = millis()
        self._func(pin)



'''LED (or general output) abstraction.
   Must call GPIO.setmode() before instanciating,
   should call GPIO.cleanup() once done.
'''
class KLed(object):
    def __init__(self, pin):
        self._pin = pin
        GPIO.setup(pin, GPIO.OUT)
        self.off()

    def get(self): return GPIO.input(self._pin)

    def set(self, new_state): GPIO.output(self._pin, new_state)

    def toggle(self): self.set(0 if self.get() else 1)

    def off(self): self.set(0)
    def on(self): self.set(1)
    def low(self): self.set(0)
    def hi(self): self.set(1)


'''Red/Green LED abstraction.
   Must call GPIO.setmode() before instanciating,
   should call GPIO.cleanup() once done.
'''
class KDualLed(object):
    def __init__(self, red_pin, green_pin):
        self._red_pin = red_pin
        self._green_pin = green_pin
        GPIO.setup(red_pin, GPIO.OUT)
        GPIO.setup(green_pin, GPIO.OUT)
        self.off()

    def set(self, red_status, green_status):
        print('set pin %d to %d and %d to %d.' % (self._red_pin, red_status, self._green_pin, green_status))
        GPIO.output(self._red_pin, red_status)
        GPIO.output(self._green_pin, green_status)

    def off(self): self.set(0, 0)
    def red(self): self.set(1, 0)
    def green(self): self.set(0, 1)
    def yellow(self): self.set(1, 1)

