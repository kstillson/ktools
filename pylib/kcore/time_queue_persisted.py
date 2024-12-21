'''Addon to TimeQueue to persist the queue into a specified file.

Also adds a EventDC (event dataclass) subtype of Event, and only supports
those for persistence.  This is because the default Event classes aren't
@dataclass's and hence aren't serializable.

Note that EventDC isn't added to time_queue.py because datetime isn't
available in CircuitPython, and time_queue.py is frequently used there.

'''

import datetime
from dataclasses import dataclass

import persister as P
import time_queue as TQ


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
    def fire(self): return eval(self.code_to_call)

    #override
    def __str__(self): return self.__repr__()


class TimeQueuePersisted(TQ.TimeQueue):
    def __init__(self, filename):
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
        with self._p.get_rw() as d:
            self.queue = d
            cnt = super().check(use_ms_time)
        return cnt
