'''varz is a simple key/value singleton database used for tracking program state.

A great Google engineering best-practice is that O(all) programs export a
/varz web handler.  Use these functions to publish counters or other internal
useful state.  For example, each time some important operation happens, call
varz.inc('important-operation-#1').

This allows both humans and automated systems to easily check on how things
are going with a service, and inspect program state without a debugger or
digging into logs.

Avoid putting sensitive data into varz, as it's not access controlled.

If the environment variable $KTOOLS_VARZ_PROM == "1", then this module will
also export varz (and optionally /healthz) as Prometheus /metrics.  This
requires the prometheus_client library to be installed, and the init_prom()
method to be called.

'''

import os, re, sys, time

if os.environ.get('KTOOLS_VARZ_PROM') == '1':
    USE_PROM = True
    import prometheus_client as PC
    import prometheus_client.exposition as PCE
    import kcore.webserver_base as WB
else:
    USE_PROM = False


# ---------- internal state

PROGRAM_NAME = os.path.basename(sys.argv[0])
VARZ = {}

# Prometheus related
HEALTHZ_HANDLER = None     # set by init_prom()
PROM_INSTANCES = {}        # Maps from varz name to prometheus metric instances.


# ---------- getters

def get(counter_name=None):
    return VARZ.get(counter_name, None) if counter_name else VARZ


# ---------- setters

def bump(counter_name): inc(counter_name, 1)


def inc(counter_name, add=1):
    global VARZ
    if counter_name not in VARZ: VARZ[counter_name] = 0
    VARZ[counter_name] += add
    if USE_PROM: _get_prom_instance(counter_name, PC.Counter).inc(add)


def set(var_name, value):
    global VARZ
    VARZ[var_name] = value
    if USE_PROM:
        if isinstance(value, int) or isinstance(value, float):
            _get_prom_instance(var_name, PC.Gauge).set(value)
        else:
            _get_prom_instance(var_name, PC.Info).info({'value': value})


def stamp(stamp_name):  # Sets current epoch seconds.
    global VARZ
    VARZ[stamp_name] = int(time.time())
    if USE_PROM: _get_prom_instance(stamp_name, PC.Counter).inc()


# ---------- management

def reset(counter_name=None):
    global VARZ
    if counter_name: VARZ[counter_name] = None
    else: VARZ = {}


# ---------- Prometheus specific

def init_prom(webserver, auto_healthz=True):
    '''To register a /metrics handler, pass in an already constructed
       kcore.webserver instance.  To also instrument /healthz, make sure any
       custom /healthz handler is registered before calling.'''
    if not USE_PROM: return
    webserver.add_handler('/metrics', _metrics_handler)
    if auto_healthz:
        hd = webserver._find_handler('/healthz')
        if hd:
            global HEALTHZ_HANDLER
            HEALTHZ_HANDLER = hd.func


# ==========  INTERNALS

def _get_prom_instance(varz_name, factory):
    prefix = '' if varz_name.startswith('healthz') else 'varz_'
    prom_name = prefix + re.sub(r'[^a-zA-Z0-9_:]', '_', varz_name)
    global PROM_INSTANCES
    if prom_name not in PROM_INSTANCES: PROM_INSTANCES[prom_name] = factory(prom_name, '', ['program'])
    return PROM_INSTANCES[prom_name].labels(PROGRAM_NAME)


def _metrics_handler(request):
    # This is an adaptor that matches the kcore handler API, but makes use of
    # prometheus_client.exposition.py to perform the work.
    # Essentially this is a translation of prometheus_client.exposition.do_GET().

    # ----- auto_healthz

    # If we know the webserver's /healthz handler, call it now, and translate
    # it's output into metrics data.
    if HEALTHZ_HANDLER:
        out = HEALTHZ_HANDLER(request)
        if isinstance(out, WB.Response): out = out.text
        _get_prom_instance('healthz', PC.Info).info({'value': out})
        status = 0 if (out.startswith('ok') or 'all ok' in out) else 1
        _get_prom_instance('healthz_status', PC.Gauge).set(status)

    # ----- Have prometheus_client.exposition generate the actual output.

    pc_encoder, content_type = PCE.choose_encoder(request.headers.get('Accept'))
    registry = PC.REGISTRY
    if 'name[]' in request.get_params:
        registry = registry.restricted_registry(request.get_params['name[]'])
    output = pc_encoder(registry).decode('utf-8')

    return WB.Response(output, msg_type=content_type)
