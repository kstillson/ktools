
# ----------------------------------------
# varz abstraction

VARZ = {}

def bump(counter_name):
    global VARZ
    if counter_name not in VARZ: VARZ[counter_name] = 0
    VARZ[counter_name] += 1


def set(var_name, value):
    global VARZ
    VARZ[var_name] = value


def stamp(stamp_name):
    global VARZ
    VARZ[stamp_name] = int(time.time())


