'''Addon to TimeQueue to persist the queue into a specified file.

Also adds a EventDC (event dataclass) subtype of Event, and only supports
those for persistence.  This is because the default Event classes aren't
@dataclass's and hence aren't serializable.

Note that EventDC isn't added to time_queue.py because datetime isn't
available in CircuitPython, and time_queue.py is frequently used there.

NOT MULTI-THREAD SAFE.  See "slimy" below.

'''

import datetime
from dataclasses import dataclass

import kcore.persister as P
import kcore.time_queue as TQ


'''Slimy-as-heck: need a way to communicate the eval_globals context passed to
   the constructor of TimeQueuePersisted to be forwarded to the EventDC.fire()
   method.  Can't trivially add it to the constructor of EventDC, as those
   instances must be able to be restored via deserialization, can't trivially
   just store it in the TimeQueuePersisted instance, as the parent's check()
   method wouldn't know to pass it to the overridden fire() method.  Sigh.

   So for now will just use a module-global for the communication.  This is
   set during the check() call, i.e. right before any fire() calls, so the
   opportunity for multiple threads/instances to stomp on each other is
   minimized, but not eliminated-- especially if fire() methods are
   long-running.  TODO(defer): find a better way.

'''
EVAL_GLOBALS = {}


@dataclass
class EventDC(TQ.Event):
    fire_dt: datetime.datetime
    code_to_call: str
    repeat_ms: int = None

    def __init__(self, fire_dt, code_to_call, repeat_ms=None, _force_now_dt=None):
        self.fire_dt = fire_dt
        self.code_to_call = code_to_call
        self.repeat_ms = repeat_ms

        now = _force_now_dt or datetime.datetime.now()
        fire_in_ms = int((fire_dt - now).total_seconds() * 1000)
        super().__init__(fire_in_ms, func=None, args=None, kwargs=None, repeat_after_ms=repeat_ms)

    #override
    def fire(self): return eval(self.code_to_call, EVAL_GLOBALS)

    #override
    def __str__(self): return self.__repr__()


class TimeQueuePersisted(TQ.TimeQueue):
    def __init__(self, filename, eval_globals={}):
        self.eval_globals = eval_globals
        self._p = P.PersisterListOfDC(filename, EventDC, eval_globals=globals())
        with self._p.get_rw() as d:
            super().__init__(d)

    def add_dt(self, dt, code): self.add_event(EventDC(dt, code))

    #override
    def add_event(self, event):
        with self._p.get_rw() as d:
            self.queue = d
            super().add_event(event)

    #override
    def check(self, use_ms_time=None):
        global EVAL_GLOBALS
        EVAL_GLOBALS = self.eval_globals
        with self._p.get_rw() as d:
            self.queue = d
            cnt = super().check(use_ms_time)
        return cnt
