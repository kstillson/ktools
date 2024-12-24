
import datetime, sys, time

import context_kcore   # fixup Python include path
import kcore.time_queue_persisted as TQP

COUNT = 0

def myfire(add=1):
    global COUNT
    COUNT += add


def test_serialization_and_deseraialization(tmp_path):
    context = sys.modules[__name__]

    filename = str(tmp_path / "tqp_test.p")
    q = TQP.TimeQueuePersisted(filename, context)

    dt1 = datetime.datetime.now() + datetime.timedelta(seconds=1)
    dt2 = dt1 + datetime.timedelta(seconds=1)

    q.add_event(TQP.EventDC(dt1, 'myfire'))
    q.add_event(TQP.EventDC(dt2, 'myfire', [20]))
    assert len(q.queue) == 2

    # Now load persisted data into a new instance
    q2 = TQP.TimeQueuePersisted(filename, context)
    assert len(q2.queue) == 2

    # and test the queue just to be sure...
    for i in range(3):
        time.sleep(1)
        q2.check()
    assert COUNT == 21
