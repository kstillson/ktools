
import time

'''Implement a queue of events to run at particular times daily.

Designed to run on systems without threading or timer support.  Compatible
with non-blocking call style.  Just call TimeQueue.check() occasionally, and
any events with times now in the past will fire.

use_daymins param is mostly for testing, but can be used for any cases
where you want to override real time.
'''

# ---------- daymins
# "daymins" are the number of minutes into a day at which an event happens.
# mostly for internal use, unless you're overriding time for testing.

def daymins(h, m): return h * 60 + m

def daymins_ts(ts): return ts.tm_hour * 60 + ts.tm_min   # Takes a struct_time

# ---------- TimedEvent
# A TimedEvent instance represents an action (function and arguments) to be
# run at a certain time each day.  Call fire() to test fire the event,
# is_past says whether the time is past for today.

class TimedEvent:
    def __init__(self, time_hour, time_min, func, args=[], kwargs={}):
        self.daymins = daymins(int(time_hour), int(time_min))
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def fire(self): return self.func(*self.args, **self.kwargs)

    # Note: returns true if event is in the past (or is right now) for today.
    # use_daymins overrides current real time (mostly for testing).
    def is_past(self, use_daymins=None):
        now = use_daymins or daymins_ts(time.localtime())
        return now >= self.daymins


# ---------- TimeQueue
# Pass a list of TimedEvents, and occasionally call check().
# This will fire any events whose time has passed since the last call, and
# returns the number of events that ran.
#
# use_daymins overrides real time (mostly for testing).  The constructor
# needs this so it can figure out which event is "next" (i.e. events whose
# time that day has already passed at time of construction are skipped).

class TimeQueue:
    def __init__(self, list_of_timed_events, use_daymins=None):
        self.queue = sorted(list_of_timed_events, key=lambda i: i.daymins)
        now = use_daymins or daymins_ts(time.localtime())
        self.last_check = now
        self.next_event_index = len(self.queue)  # Default to 1 beyond valid index, in-case all events have passed.
        for i, event in enumerate(self.queue):
            if not self.queue[i].is_past(now):
                self.next_event_index = i
                break

    def check(self, use_daymins=None):
        fired = 0
        now = use_daymins or daymins_ts(time.localtime())
        if now < self.last_check:
            # We've wrapped to the next day. Empty any left-over queue.
            while self.next_event_index < len(self.queue):
                self.queue[self.next_event_index].fire()
                fired += 1
                self.next_event_index += 1
            self.next_event_index = 0
        self.last_check = now
        if self.next_event_index >= len(self.queue):
            return fired                       # Nothing more until tomorrow.
        while self.queue[self.next_event_index].is_past(now):
            self.queue[self.next_event_index].fire()
            fired += 1
            self.next_event_index += 1
            if self.next_event_index >= len(self.queue):
                break
        return fired
