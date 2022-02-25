
import context_pylib  # includes ../ in path so we can import things there.

import k_log_queue as B

# Override time function..
B.get_time = lambda: 'TIME'

def test_basics():
    B.set_queue_len(3)
    B.log_debug('msg1')
    B.log('msg2', 'invalid-level-name-goes-to-info')
    B.log_warning('msg3')
    B.log('msg4', 'crit')

    assert B.LOG_QUEUE[0] == 'CRITICAL: TIME: msg4'
    assert B.LOG_QUEUE[1] == 'WARNING: TIME: msg3'
    assert B.LOG_QUEUE[2] == 'INFO: TIME: msg2'
    assert len(B.LOG_QUEUE) == 3

    B.set_queue_len(2)
    assert B.LOG_QUEUE[0] == 'CRITICAL: TIME: msg4'
    assert B.LOG_QUEUE[1] == 'WARNING: TIME: msg3'
    assert len(B.LOG_QUEUE) == 2

    B.log_alert('msg5')
    assert B.LOG_QUEUE[0] == 'CRITICAL: TIME: msg5'
    assert B.LOG_QUEUE[1] == 'CRITICAL: TIME: msg4'
    assert len(B.LOG_QUEUE) == 2

    assert B.last_logs() == 'CRITICAL: TIME: msg5\nCRITICAL: TIME: msg4'
    assert B.last_logs_html() == '<p>CRITICAL: TIME: msg5<br/>CRITICAL: TIME: msg4'
