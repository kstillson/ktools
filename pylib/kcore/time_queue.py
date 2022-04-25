
'''Implement a queue of events to run at particular times daily.

Designed to run on systems without threading or timer support.  Compatible
with non-blocking call style.  Just call TimeQueue.check() occasionally, and
any events with times now in the past will fire.

use_daymins param is mostly for testing, but can be used for any cases
where you want to override real time.
'''

import time


# ---------- time conversions


# Theis are based on time.monotonic_ns(), which is valid for comparison to
# itself, but does not represent absolute time (e.g. ms since the epoch).
def now_in_ms(): return int(time.monotonic_ns() / 1000000)

# This is an offset of ms into a day; not absolute time.
def hm_to_ms(h, m): return 1000 * 60 * (60 * h + m)

ONE_DAY_IN_MS = hm_to_ms(24, 0)

# ---------- Events

# Event fires in a number of miliseconds relative to time of construcation.
class Event:
    def __init__(self, fire_in_ms, func, args=[], kwargs={}, repeat_after_ms=None):
        self.fire_at_ms = now_in_ms() + fire_in_ms
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.repeat_after_ms = repeat_after_ms
        
    def fire(self): return self.func(*self.args, **self.kwargs)

    def __str__(self):
        return 'ms=%d, rep=%s, args=%s, kwargs=%s' % (
            self.fire_at_ms, self.repeat_after_ms, self.args, self.kwargs)

    
# TimedEvent's fire at a given hour/min of the day, repeating daily.
class TimedEvent(Event):
    def __init__(self, time_hour, time_min, func, args=[], kwargs={}, force_now_ms=None):
        # Compute hour/min offset into a day, in ms
        wanted_ms = hm_to_ms(time_hour, time_min)
        # And find the offset into today's current time, again in ms.
        now_ts = time.localtime()
        now_ms = force_now_ms or hm_to_ms(now_ts.tm_hour, now_ts.tm_min)
        # If event time for today has already passed, bump it to tomorrow.
        if now_ms > wanted_ms:
            wanted_ms += ONE_DAY_IN_MS
            print(f'@add day wrapped {wanted_ms=}')
        #
        self.fire_at_ms = wanted_ms
        print(f'@add {time_hour=} {time_min=} {wanted_ms=} {now_ms=} so {self.fire_at_ms=}')
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.repeat_after_ms = ONE_DAY_IN_MS


# ---------- TimeQueue

# Pass a list of Events, and then occasionally call check().
# This will fire any events whose time has passed since the last call, and
# returns the number of events that ran.

class TimeQueue:
    def __init__(self, list_of_events):
        self.queue = list_of_events

    def add_event(self, event):
        self.queue.append(event)
        
    def check(self, use_ms_time=None):
        now_ms = use_ms_time or now_in_ms()
        print(f'@@ now_ms: {now_ms}')
        fired = 0
        rm_events = []
        for i, e in enumerate(self.queue):
            if e.fire_at_ms <= now_ms:
                print(f'@@ firing: {e}')
                e.fire()
                fired += 1
                if e.repeat_after_ms:
                    e.fire_at_ms += e.repeat_after_ms
                else:
                    rm_events.append(i)
            else:
                print(f'@@ not firing: {e}')
        for i in reversed(rm_events): self.queue.pop(i)
        return fired
