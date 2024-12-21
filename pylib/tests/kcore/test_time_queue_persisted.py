
import datetime, time

import context_kcore   # fixup Python include path
import kcore.time_queue_persisted as TQP

COUNT = 0

def fire():
    global COUNT
    COUNT += 1


def test_serialization_and_deseraialization(tmp_path):
    filename = str(tmp_path / "tqp_test.p")
    q = TQP.TimeQueuePersisted(filename, globals())

    dt1 = datetime.datetime.now() + datetime.timedelta(seconds=1)
    dt2 = dt1 + datetime.timedelta(seconds=1)

    code = 'fire()'
    q.add_dt(dt1, code)
    q.add_dt(dt2, code)
    assert len(q.queue) == 2

    # Now load persisted data into a new instance
    q2 = TQP.TimeQueuePersisted(filename, globals())
    assert len(q2.queue) == 2

    # and test the queue just to be sure...
    for i in range(3):
        time.sleep(1)
        q2.check()
    assert COUNT == 2
