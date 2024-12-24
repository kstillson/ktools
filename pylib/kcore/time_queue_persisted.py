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


'''Slimy-as-heck: need a way to communicate the CONTEXT passed to the
   constructor of TimeQueuePersisted to be forwarded to the EventDC.fire()
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
CONTEXT = globals()


@dataclass
class EventDC(TQ.Event):
    fire_dt: datetime.datetime
    func_name: str
    args: list[str]
    kwargs: dict[str, str]
    repeat_after_ms: int

    def __init__(self, fire_dt, func_name, args=[], kwargs={}, repeat_after_ms=None, _force_now_dt=None):
        self.fire_dt = fire_dt
        self.func_name = func_name

        now = _force_now_dt or datetime.datetime.now()
        fire_in_ms = int((fire_dt - now).total_seconds() * 1000)

        # we could set func=self.fire, but this won't serialize or deserialize
        # well, so instead we'll just override the local fire() method and
        # set self.func to None, as it's no longer used.

        super().__init__(fire_in_ms, None, args, kwargs, repeat_after_ms)

    #override
    def fire(self):
        func = getattr(CONTEXT, self.func_name)
        return func(*self.args, **self.kwargs)

    #override
    def __str__(self): return self.__repr__()


class TimeQueuePersisted(TQ.TimeQueue):
    def __init__(self, filename, context):
        self.context = context
        self._p = P.PersisterListOfDC(filename, EventDC, eval_globals=globals())
        with self._p.get_rw() as d:
            super().__init__(d)

    #override
    def add_event(self, event):
        with self._p.get_rw() as d:
            self.queue = d
            super().add_event(event)

    #override
    def check(self, use_ms_time=None):
        global CONTEXT
        CONTEXT = self.context
        with self._p.get_rw() as d:
            self.queue = d
            cnt = super().check(use_ms_time)
        return cnt

    def get_queue_ro(self): return self._p.get_data()
