'''
TODO: doc

'''


# Circuit py supports time but not datetime, so let's use that.
# NB: CircuitPy boards don't always have an RTC or it might not be set.
import time

# Internal state
LOG_QUEUE = []
LOG_QUEUE_LEN_MAX = 40

# ---------- Low-dep levels

# (Circuit Python doesn't have a logging module, so let's repeat the levels here
#  in a no-dependency way.)
#
# You can use  kcore.log_queue.LEVELS.INFO  or even just  k_log_queue.INFO
# and get name for a number using kcore.log_queue.Levels.name(20)

LEVEL_DICT = {'ALERT': 50, 'CRIT': 50,  'CRITICAL': 50,
              'ERR': 40,   'ERROR': 40, 'WARNING': 30,
              'INFO': 20,  'DEBUG': 10, 'NOTSET': 0,
              'NEVER': 99 }
NAME_TO_NUM = {}   # Populated by LEVELS singleton during construction.

class Levels(object):
    def __init__(self): self.populate()
        
    def populate(self, target_ns=globals()):
        global NAME_TO_NUM
        for text in sorted(LEVEL_DICT):
            num = LEVEL_DICT[text]
            setattr(self, text, num)    # e.g. kcore.log_queue.LEVELS.INFO
            target_ns[text] = num       # e.g. kcore.log_queue.INFO
            NAME_TO_NUM[num] = text     # last entry rules for dups.
            
    @staticmethod
    def name(num): return NAME_TO_NUM.get(num)

LEVELS = Levels()                       # global singleton available to all.

FORCE_TIME = None

# User can override this to print log messags at or above a given level.
# This goes to stdout, which on a circ-py board, goes to serial.
PRINT_LEVEL = LEVEL_DICT['NEVER']

# ---------- Logging and controls

def log(msg, level=LEVELS.INFO):
    if isinstance(level, str): level = LEVEL_DICT.get(level.upper(), LEVELS.INFO)
    global LOG_QUEUE
    if LOG_QUEUE_LEN_MAX and len(LOG_QUEUE) >= LOG_QUEUE_LEN_MAX: del LOG_QUEUE[LOG_QUEUE_LEN_MAX - 1]
    msg2 = decorate_msg(msg, level)
    LOG_QUEUE.insert(0, msg2)
    if level >= PRINT_LEVEL: print(msg2)

def decorate_msg(msg, level):
    return '%s: %s: %s' % (Levels.name(level), get_time(), msg)

def clear():
    global LOG_QUEUE
    LOG_QUEUE = []

def set_print_level(level):
    if isinstance(level, str): level = LEVEL_DICT.get(level.upper(), LEVELS.INFO)
    global PRINT_LEVEL
    PRINT_LEVEL = level
    
def set_queue_len(new_len):
    global LOG_QUEUE, LOG_QUEUE_LEN_MAX
    LOG_QUEUE_LEN_MAX = new_len
    if len(LOG_QUEUE) > new_len: LOG_QUEUE = LOG_QUEUE[:new_len]
    

# ---------- Handy shortcuts

def log_crit(msg): log(msg, LEVELS.CRITICAL)
def log_alert(msg): log(msg, LEVELS.ALERT)
def log_error(msg): log(msg, LEVELS.ERROR)
def log_warning(msg): log(msg, LEVELS.WARNING)
def log_info(msg): log(msg, LEVELS.INFO)
def log_debug(msg): log(msg, LEVELS.DEBUG)

# ---------- Log queue access

def last_logs(): return '\n'.join(LOG_QUEUE)
def last_logs_html(): return '<p>' + '<br/>'.join(LOG_QUEUE)

# ---------- Overridable for testing...

def get_time():
    if FORCE_TIME: return FORCE_TIME
    t = time.localtime()
    return '%d-%d-%d %d:%d:%d' % (t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
