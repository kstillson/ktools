
import os, pytest, time

import context_kcore     # fix path
import kcore.gpio as G


# ---------- helpers

@pytest.fixture(scope='session')
def init():
    G.init(simulation=True)


PRESS_TRACKING = None

def press_callback(bcm_pin):
    global PRESS_TRACKING
    PRESS_TRACKING = bcm_pin


# ---------- tests

def test_KButton(init):
    # (no point testing debounce_ms, that's done in RPi.GPIO, i.e. outside simuluation)
    kb1 = G.KButton(bcm_pin=1, func=press_callback, background=True, debounce_ms=0, require_pressed_ms=100)
    assert kb1.value()   # should be floating high.
    assert G.input(1)

    # Try a normal (simulated) press.  Input value should drop immediately,
    # but callback soundn't occur for 100ms.
    global PRESS_TRACKING
    PRESS_TRACKING = -1
    kb1.simulate_press(new_state=False, duration=150)
    assert not kb1.value()
    assert PRESS_TRACKING == -1
    time.sleep(.110)
    assert PRESS_TRACKING == 1
    time.sleep(.50)
    assert kb1.value()

    # Try a under-required-time press, it should not trigger callback.
    PRESS_TRACKING = -2
    kb1.simulate_press(new_state=False, duration=50)
    assert not kb1.value()
    time.sleep(.110)
    assert PRESS_TRACKING == -2
    assert kb1.value()

    # ----- Try a normally-low button, make sure logic reversal works.
    PRESS_TRACKING = -3
    kb2 = G.KButton(bcm_pin=2, func=press_callback, normally_high=False, background=False, debounce_ms=0, require_pressed_ms=0)
    assert not kb2.value()

    # "Press" to low; should have no effect.
    kb2.simulate_press(new_state=False, duration=10)
    assert not kb2.value()
    assert PRESS_TRACKING == -3
    time.sleep(.30)
    assert not kb2.value()
    assert PRESS_TRACKING == -3

    # Press high, should trigger immediately.
    kb2.simulate_press(new_state=True, duration=10)
    assert kb2.value()
    assert PRESS_TRACKING == 2
    time.sleep(.30)
    assert not kb2.value()


def test_dual_led(init):
    # implicitly tests KLed, as a KDualLed is just two of those..
    kl = G.KDualLed(3, 4)
    assert not G.SIM_LEDS[3]
    assert not G.SIM_LEDS[4]

    kl.yellow()
    assert G.SIM_LEDS[3]
    assert G.SIM_LEDS[4]

    kl.red()
    assert G.SIM_LEDS[3]
    assert not G.SIM_LEDS[4]
