
import time

import context_kcore   # fixup Python include path
import kcore.time_queue as Q


# ---------- helpers

VALUE = None
def setter(new_val):
    global VALUE
    VALUE = new_val


# Same as Q.hm_to_ms, but if the "hour" param is less than the previous call,
# assume we're wrapped around, so add a day.
ADD_DAYS = 0
LAST_HOUR = None
def hm_to_ms_wrap(h, m):
    ms = Q.hm_to_ms(h, m)
    global ADD_DAYS, LAST_HOUR
    if LAST_HOUR is None: LAST_HOUR = h
    elif h < LAST_HOUR:
        ADD_DAYS += 1
        LAST_HOUR = h
    return ms + ADD_DAYS * Q.ONE_DAY_IN_MS

def reset(reset_value_to=-1):
    global ADD_DAYS, LAST_HOUR, VALUE
    ADD_DAYS = 0
    LAST_HOUR = None
    VALUE = reset_value_to


# ---------- tests

def test_Events_against_real_time():
    reset(-8)
    tq = Q.TimeQueue([
        Q.Event(100, setter, [1], repeat_after_ms=300),
        Q.Event(110, setter, [2]),
        Q.Event(300, setter, [3])])

    # An immediate call shouldn't fire anything.
    assert tq.check() == 0
    assert VALUE == -8

    # Wait 150ms, and the first two events should fire.
    time.sleep(0.15)
    assert tq.check() == 2
    assert VALUE == 2

    # Wait another 200ms (total of 350), and event 3 should have fired.
    time.sleep(0.2)
    assert tq.check() == 1
    assert VALUE == 3

    # Wait another 100ms (total of 450), and event 1 should have re-fired.
    time.sleep(0.1)
    assert tq.check() == 1
    assert VALUE == 1

def test_TimedEvents_against_mocked_time():
    reset(-1)
    start_ms = Q.hm_to_ms(1, 30)  # event [100] should push to tomorrow.
    tq = Q.TimeQueue([
        Q.TimedEvent(3, 0,   setter, [300], _force_now_ms=start_ms),
        Q.TimedEvent(4, 0,   setter, [400], _force_now_ms=start_ms),
        Q.TimedEvent(2, 0,   setter, [200], _force_now_ms=start_ms),
        Q.TimedEvent(1, 0,   setter, [100], _force_now_ms=start_ms),
        Q.TimedEvent(23, 59, setter, [2359], _force_now_ms=start_ms)])

    # Confirm sort order.
    last = 0
    for e in tq.queue:
        assert e.fire_at_ms > last
        last = e.fire_at_ms

    # Let's call before 02:00 and confirm nothing changes.
    # The 1:00 event should have wrapped until tomorrow.
    assert tq.check(hm_to_ms_wrap(1, 31)) == 0
    assert VALUE == -1
    assert tq.check(hm_to_ms_wrap(1, 59)) == 0
    assert VALUE == -1

    # Okay, now let's try at 2:01, and confirm a single event fires.
    assert tq.check(hm_to_ms_wrap(2, 1)) == 1
    assert VALUE == 200

    # Make sure nothing else fires until 0300
    assert tq.check(hm_to_ms_wrap(2, 1)) == 0
    assert VALUE == 200
    assert tq.check(hm_to_ms_wrap(2, 31)) == 0
    assert VALUE == 200

    # Now let's skip all the way until past 0400 and confirm 2 events fire.
    assert tq.check(hm_to_ms_wrap(4, 1)) == 2
    assert VALUE == 400

    # Wrap around to a call the next morning before 0100 and confirm the
    # final event ran, and we're queued for 0100.
    assert tq.check(hm_to_ms_wrap(0, 1)) == 1
    assert VALUE == 2359

    # And finally check that the 0100 event fires as expected.
    assert tq.check(hm_to_ms_wrap(1, 2)) == 1
    assert VALUE == 100

def test_empty_queue():
    reset(-9)
    tq = Q.TimeQueue()
    assert tq.check(hm_to_ms_wrap(1, 31)) == 0
    assert tq.check(hm_to_ms_wrap(23, 59)) == 0
    assert tq.check(hm_to_ms_wrap(4, 0)) == 0

def test_only_one_event_and_it_is_passed():
    reset(-2)
    start_ms = Q.hm_to_ms(2, 30)  # event [200] should push to tomorrow.

    global VALUE
    tq = Q.TimeQueue([
        Q.TimedEvent(2, 0,   setter, [200], _force_now_ms=start_ms)])
    assert VALUE == -2  # event should not have run.

    # Advance clock a few mins and call check.  Event should still not have run.
    assert tq.check(hm_to_ms_wrap(2, 45)) == 0
    assert VALUE == -2

    # Now wrap to before the event time.  Still should not have run.
    assert tq.check(hm_to_ms_wrap(1, 1)) == 0
    assert VALUE == -2

    # Finally wrap until after the event time, and it should have run.
    assert tq.check(hm_to_ms_wrap(2, 1)) == 1
    assert VALUE == 200

def test_end_of_day_without_wrapping():
    reset(-3)
    start_ms = Q.hm_to_ms(14, 30)  # event [1000] should push to tomorrow.

    global VALUE
    tq = Q.TimeQueue([
        Q.TimedEvent(10, 0, setter, [1000], _force_now_ms=start_ms),
        Q.TimedEvent(18, 0, setter, [1800], _force_now_ms=start_ms)])

    # Check immediately upon construction.
    assert tq.check(hm_to_ms_wrap(15, 30)) == 0
    assert VALUE == -3

    # Check again right before 18:00 event.
    assert tq.check(hm_to_ms_wrap(17, 59)) == 0
    assert VALUE == -3

    # And check at 18:00
    assert tq.check(hm_to_ms_wrap(18, 0)) == 1
    assert VALUE == 1800

    # And check again after 18:00 but before daily wrap.
    # (this catches some bugs discovered during development)
    assert tq.check(hm_to_ms_wrap(18, 5)) == 0

    # Now wrap, but to a time before the next event.
    assert tq.check(hm_to_ms_wrap(8, 0)) == 0

    # And finally check after the 10:00 event passes.
    assert tq.check(hm_to_ms_wrap(10, 0)) == 1
    assert VALUE == 1000
