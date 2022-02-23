
import sys
import k_log_queue as Q

# ---------- Controls

LOGFILE_LEVEL = Q.WARNING
QUEUE_LEVEL = Q.INFO
STDERR_LEVEL = Q.INFO

def debug(control):
    if control: QUEUE_LEVEL = STDERR_LEVEL = Q.DEBUG
    else: QUEUE_LEVEL = STDERR_LEVEL = Q.INFO

LOGFILE_NAME = 'circuitpy_sim.log'

# ---------- Re-expose levels from Q for our callers.

Levels = Q.Levels
LEVELS = Q.LEVELS
LEVELS.populate(globals())

# ---------- 

def log(msg, level=Q.INFO):
    msg2 = '%s: %s: %s' % (Q.LEVELS.name(level), Q.get_time(), msg)
    if level >= LOGFILE_LEVEL:
        with open(LOGFILE_NAME, 'a') as f: f.write(msg2)
    if level >= QUEUE_LEVEL:
        Q.log(msg, level)
    if level >= STDERR_LEVEL:
        sys.stderr.write(msg2)

