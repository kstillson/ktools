
import os, pytest, time

import context_kcore     # fix path
import kcore.gpio as G


# ---------- helpers

@pytest.fixture(scope='session')
def sim_mode():
    G.init(simulation=True)


@pytest.fixture(scope='session')
def circpy_sim_mode():
    G.CIRCUITPYTHON = True
    G.init(simulation=True)


PRESS_TRACKING = None
def press_callback(bcm_pin):
    global PRESS_TRACKING
    PRESS_TRACKING = bcm_pin


# ---------- tests

def test_KButton_in_sim_mode(sim_mode):
    kb1 = G.KButton(bcm_pin=1, func=press_callback, background=True, debounce_ms=0, require_pressed_ms=100, log=True)
    assert kb1.value()   # should be floating high.
    assert G.input(1)

    # Try a normal (simulated) press.  Input value should drop immediately,
    # but callback soundn't occur for 100ms.
    global PRESS_TRACKING
    PRESS_TRACKING = -1
    kb1.simulate_press(duration_ms=150)
    assert not kb1.value()
    assert PRESS_TRACKING == -1
    time.sleep(.110)
    assert PRESS_TRACKING == 1
    time.sleep(.100)
    assert kb1.value()

    # Try a under-required-time press, it should not trigger callback.
    PRESS_TRACKING = -2
    kb1.simulate_press(duration_ms=50)
    assert not kb1.value()
    time.sleep(.110)
    assert PRESS_TRACKING == -2
    assert kb1.value()

    # ----- Try a normally-low button, make sure logic reversal works.
    PRESS_TRACKING = -3
    kb2 = G.KButton(bcm_pin=2, func=press_callback, normally_high=False, background=False, debounce_ms=80, require_pressed_ms=0, log=True)
    assert not kb2.value()

    # Press high, should trigger immediately.
    kb2.simulate_press(duration_ms=10)
    assert kb2.value()
    assert PRESS_TRACKING == 2
    time.sleep(.030)
    assert not kb2.value()

    # Press high again, should be ignored due to debounce.
    PRESS_TRACKING = -4
    kb2.simulate_press(duration_ms=10)
    assert kb2.value()
    assert PRESS_TRACKING == -4

    # and wait another 60ms for the debounce to wear off, and it should work.
    time.sleep(.060)
    kb2.simulate_press(duration_ms=10)
    assert PRESS_TRACKING == 2


def test_KButton_in_circpy_mode(circpy_sim_mode):
    kb1 = G.KButton(bcm_pin=3, func=press_callback, background=False, debounce_ms=500, require_pressed_ms=100, log=True)
    assert kb1.value()   # should be floating high.

    # Check nothing has happened yet.
    global PRESS_TRACKING
    PRESS_TRACKING = -5
    kb1.check()
    assert PRESS_TRACKING == -5
    assert len(kb1._event_queue.queue) == 0

    # Try a simulated press.  Initially, nothing should happen except we get
    # a queued check for require_press_ms.
    kb1.simulate_press(duration_ms=150)
    kb1.check()
    assert PRESS_TRACKING == -5
    assert len(kb1._event_queue.queue) == 1

    # Wait 100ms (total of 200ms in).  The event should now run, but only once
    # we call the check() method.
    time.sleep(0.100)
    assert PRESS_TRACKING == -5
    assert len(kb1._event_queue.queue) == 1
    kb1.check()
    assert PRESS_TRACKING == 3
    assert len(kb1._event_queue.queue) == 0


def test_dual_led(sim_mode):
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
