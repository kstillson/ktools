
import context_circuitpy_lib   # fixup Python include path

import k_time_queue as Q


VALUE = -1

def setter(new_val):
    global VALUE
    VALUE = new_val


def test_basics():
    tq = Q.TimeQueue([
        Q.TimedEvent(3, 0,   setter, [300]),
        Q.TimedEvent(4, 0,   setter, [400]),
        Q.TimedEvent(2, 0,   setter, [200]),
        Q.TimedEvent(1, 0,   setter, [100]),
        Q.TimedEvent(23, 59, setter, [2359])],
                     use_daymins = Q.daymins(1, 30))

    # Check that things got sorted correctly.
    assert tq.queue[0].daymins == Q.daymins(1, 0)

    # Check the next queued item is the 02:00 event, as the time we
    # set during construction was 01:30.
    assert tq.next_event_index == 1
    assert tq.queue[1].daymins == Q.daymins(2, 0)

    # Let's call again before 02:00 and confirm nothing changes.
    assert tq.check(Q.daymins(1, 31)) == 0
    assert VALUE == -1
    assert tq.check(Q.daymins(1, 59)) == 0
    assert VALUE == -1

    # Okay, now let's try at 2:01, and confirm a single event fires.
    assert tq.check(Q.daymins(2, 1)) == 1
    assert VALUE == 200

    # Make sure nothing else fires until 0300
    assert tq.check(Q.daymins(2, 1)) == 0
    assert VALUE == 200
    assert tq.check(Q.daymins(2, 31)) == 0
    assert VALUE == 200

    # Now let's skip all the way until past 0400 and confirm 2 events fire.
    assert tq.check(Q.daymins(4, 1)) == 2
    assert VALUE == 400
    assert tq.next_event_index == 4

    # Wrap around to a call the next morning before 0100 and confirm the
    # final event ran, and we're queued for 0100.
    assert tq.check(Q.daymins(0, 1)) == 1
    assert VALUE == 2359
    assert tq.next_event_index == 0

    # And finally check that the 0100 event fires as expected.
    assert tq.check(Q.daymins(1, 2)) == 1
    assert VALUE == 100


def test_empty_queue():
    tq = Q.TimeQueue([], use_daymins = Q.daymins(1, 30))
    assert tq.check(Q.daymins(1, 31)) == 0
    assert tq.check(Q.daymins(23, 59)) == 0
    assert tq.check(Q.daymins(4, 0)) == 0


def test_only_one_event_and_it_is_passed():
    global VALUE
    VALUE = -2
    tq = Q.TimeQueue([
        Q.TimedEvent(2, 0,   setter, [200])],
                     use_daymins = Q.daymins(2, 30))
    assert VALUE == -2  # event should not have run.

    # Advance clock a few mins and call check.  Event should still not have run.
    assert tq.check(Q.daymins(2, 45)) == 0
    assert VALUE == -2

    # Now wrap to before the event time.  Still should not have run.
    assert tq.check(Q.daymins(1, 1)) == 0
    assert VALUE == -2

    # Finally wrap until after the event time, and it should have run.
    assert tq.check(Q.daymins(2, 1)) == 1
    assert VALUE == 200


def test_end_of_day_without_wrapping():
    global VALUE
    VALUE = -3
    tq = Q.TimeQueue([
        Q.TimedEvent(10, 0,   setter, [1000]),
        Q.TimedEvent(18, 0,   setter, [1800])],
                     use_daymins = Q.daymins(15, 30))

    # Check immediately upon construction.
    assert tq.check(Q.daymins(15, 30)) == 0
    assert VALUE == -3

    # Check again right before 18:00 event.
    assert tq.check(Q.daymins(17, 59)) == 0
    assert VALUE == -3

    # And check at 18:00
    assert tq.check(Q.daymins(18, 0)) == 1
    assert VALUE == 1800

    # And check again after 18:00 but before daily wrap.
    # (this catches some bugs discovered during development)
    assert tq.check(Q.daymins(18, 5)) == 0

    # Now wrap, but to a time before the next event.
    assert tq.check(Q.daymins(8, 0)) == 0

    # And finally check after the 10:00 event passes.
    assert tq.check(Q.daymins(10, 0)) == 1
    assert VALUE == 1000
