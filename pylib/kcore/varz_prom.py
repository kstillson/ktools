'''Thin wrapper around varz to export Prometheus metrics.

Basically this wrapper mimcs the kcore.varz API, and will do exactly what
kcore.varz does, but in addition, will create matching prometheus_client
metric exports, with its best guess as to the appropriate type.

Once the caller has constructed their kcore.webserver, just add the provided
metrics_handler() method, below, to the /metrics path (or whatever path you
want), to get the values visible.

'''

import sys

import prometheus_client as PC
import prometheus_client.exposition as PCE
import kcore.webserver_base as WB
import kcore.varz as V

# ---------- state

METRIC_INSTANCES = {}
PROGRAM_NAME = sys.argv[0]


# ---------- /metrics handler (to be added to webserver's kcore.webserver handler list)

def metrics_handler(request):
    # This is an adaptor that matches the kcore handler API, but makes use of
    # prometheus_client.exposition.py:_bake_output() to perform the work.
    # Essentially this is a translation of prometheus_client.exposition.do_GET().
    #
    # Yes, this is slimy and somewhat fragile, as you're not supposed to
    # directly call leading underscore methods, as their signature might
    # change.  But we can't call PC.exposition.do_GET because our instance of
    # BaseHTTPRequestHandler has been lost by the time this handler method is
    # called, and besides, the way kcore.webserver handlers output generation
    # is rather incompatible.

    registry = PC.REGISTRY
    accept_header = request.headers.get('Accept')
    params = request.get_params

    status, header_tuple, output = PCE._bake_output(registry, accept_header, params)

    code = int(status.split(' ', 1)[0])
    headers = { header_tuple[0]: header_tuple[1] }
    return WB.Response(output.decode('utf-8'), code, headers)


# ---------- getters (just a passthrough)

def get(counter_name=None): return V.get(counter_name)


# ---------- setters

def bump(counter_name):
    if counter_name not in METRIC_INSTANCES: METRIC_INSTANCES[counter_name] = PC.Counter(get_prom_name(counter_name), '', ['program'])
    METRIC_INSTANCES[counter_name].labels(PROGRAM_NAME).inc()
    return V.bump(counter_name)

def inc(counter_name, add=1):
    if counter_name not in METRIC_INSTANCES: METRIC_INSTANCES[counter_name] = PC.Counter(get_prom_name(counter_name), '', ['program'])
    METRIC_INSTANCES[counter_name].labels(PROGRAM_NAME).inc(amount=add)
    return V.inc(counter_name, add)

def set(var_name, value):
    prom_name = get_prom_name(var_name)
    if isinstance(value, int) or isinstance(value, float):
        if var_name not in METRIC_INSTANCES: METRIC_INSTANCES[var_name] = PC.Gauge(prom_name, '', ['program'])
        METRIC_INSTANCES[var_name].labels(PROGRAM_NAME).set(value)
    else:
        if var_name not in METRIC_INSTANCES: METRIC_INSTANCES[var_name] = PC.Info(prom_name, '', ['program'])
        METRIC_INSTANCES[var_name].labels(PROGRAM_NAME).info({'value': value})
    return V.set(var_name, value)

def stamp(stamp_name):  # Implemented as a counter; take derivitive to get change rate.
    return bump(stamp_name)


# ---------- management (just a passthrough as prom can't reset counters)

def reset(counter_name=None): return V.reset(counter_name)


# ---------- internals

def get_prom_name(name):
    return 'varz_' + name.replace('-', '_')
