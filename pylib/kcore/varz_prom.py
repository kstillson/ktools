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

HEALTHZ_HANDLER = None
METRIC_INSTANCES = {}
PROGRAM_NAME = sys.argv[0]


# ---------- initialization

def init(webserver=None, auto_healthz=True):
    '''To register a /metrics handler, pass in an already constructed
       kcore.webserver instance.  To also instrument /healthz, make
       sure any custom /healthz handler is already registered. '''
    if not webserver: return
    webserver.add_handler('/metrics', metrics_handler)

    hd = webserver._find_handler('/healthz')
    if hd and auto_healthz:
        global HEALTHZ_HANDLER
        HEALTHZ_HANDLER = hd.func

    return True


# ---------- getters (just a passthrough)

def get(counter_name=None): return V.get(counter_name)


# ---------- setters

def bump(counter_name):
    get_prom_instance(counter_name, PC.Counter).inc()
    return V.bump(counter_name)

def inc(counter_name, add=1):
    get_prom_instance(counter_name, PC.Counter).inc(amount=add)
    return V.inc(counter_name, add)

def set(var_name, value):
    if isinstance(value, int) or isinstance(value, float):
        get_prom_instance(var_name, PC.Gauge).set(value)
    else:
        get_prom_instance(var_name, PC.Info).info({'value': value})
    return V.set(var_name, value)

def stamp(stamp_name):  # Implemented as a counter; take derivitive to get change rate.
    return bump(stamp_name)


# ---------- management (just a passthrough as prom can't reset counters)

def reset(counter_name=None): return V.reset(counter_name)


# ---------- internals

def get_prom_instance(name, factory):
    global METRIC_INSTANCES
    if name not in METRIC_INSTANCES: METRIC_INSTANCES[name] = factory(get_prom_name(name), '', ['program'])
    return METRIC_INSTANCES[name].labels(PROGRAM_NAME)    


def get_prom_name(name):
    if name[0] == '_': return name[1:]          # _healthz   -> healthz
    return 'varz_' + name.replace('-', '_')     # whatever-x -> varz_whatever_x


def metrics_handler(request):
    # This is an adaptor that matches the kcore handler API, but makes use of
    # prometheus_client.exposition.py:_bake_output() to perform the work.
    # Essentially this is a translation of prometheus_client.exposition.do_GET().
    #
    # Yes, this is slimy and somewhat fragile, as you're not supposed to
    # directly call PCE's leading underscore methods, as their signature might
    # change.  But we can't call PC.exposition.do_GET because our instance of
    # BaseHTTPRequestHandler has been lost by the time this handler method is
    # called, and besides, the way kcore.webserver handlers output generation
    # is rather incompatible.

    # ----- auto_healthz
    
    # If we know the webserver's /healthz handler, call it now, and translate
    # it's output into metrics data.
    if HEALTHZ_HANDLER:
        out = HEALTHZ_HANDLER(request)
        if isinstance(out, WB.Response): out = out.text
        get_prom_instance('_healthz', PC.Info).info({'value': out})
        status = 0 if (out.startswith('ok') or 'all ok' in out) else 1
        get_prom_instance('_healthz_status', PC.Gauge).set(status)
        
    # ----- Have prometheus_client.exposition generate the actual output.
    
    registry = PC.REGISTRY
    accept_header = request.headers.get('Accept')
    params = request.get_params

    status, header_tuple, output = PCE._bake_output(registry, accept_header, params)

    # ----- Populate a Response object for our output.
    
    code = int(status.split(' ', 1)[0])
    headers = { header_tuple[0]: header_tuple[1] }
    return WB.Response(output.decode('utf-8'), code, headers)

