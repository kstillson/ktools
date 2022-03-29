'''varz is a simple key/value singleton database used for tracking program state.

A great Google engineering best-practice I try to maintain is all programs
exporting a /varz web handler.  Use these functions to publish counters or
other internal useful state.  For example, each time some important
operation happens, call varz.inc('important-operation-#1').

This allows both humans and automated systems to easily check on how things
are going with a service, and inspect program state without a debugger or
digging into logs.

Avoid putting sensitive data into varz.  It's not access controlled.
'''

import time

# ----------------------------------------
# varz abstraction

VARZ = {}

# ---------- getters

def get(counter_name=None):
    return VARZ.get(counter_name, None) if counter_name else VARZ


# ---------- setters

def bump(counter_name): inc(counter_name, 1)

def inc(counter_name, add=1):
    global VARZ
    if counter_name not in VARZ: VARZ[counter_name] = 0
    VARZ[counter_name] += add

def set(var_name, value):
    global VARZ
    VARZ[var_name] = value

def stamp(stamp_name):  # Sets current epoch seconds.
    global VARZ
    VARZ[stamp_name] = int(time.time())

    
# ---------- management

def reset(counter_name=None):
    global VARZ
    if counter_name: VARZ[counter_name] = None
    else: VARZ = {}

