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
also export varz (and optionally /healthz) as Prometheus /metrics.

'''

import os, re, sys, time

# varz is intended to be a very low level module, so don't included the
# complicated Prometheus deps unless really necessary.  Also worth noting that
# the inclusion of webserver_base is technically a leveling violation (varz is
# supposed to be lower level than webserver, and this is technically an import
# cycle, which fortunately Python resolves for us).  This could be resolved by
# refactoring the WB.Response class into an even lower-level file (as that's
# all we need from WB), but the web-server is already spread amoungst too many
# files, and splitting it further just for this doesn't seem justified.
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
PROM_INSTANCES = {}        # Maps from varz name to prometheus metric instances.
WEBSERVER = None           # Populated by webserver_base:__init__ if $KTOOLS_VARZ_PROM is set.


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


# ==========  INTERNALS

def _get_prom_instance(varz_name, factory):
    prefix = '' if varz_name.startswith('healthz') else 'varz_'
    prom_name = prefix + re.sub(r'[^a-zA-Z0-9_:]', '_', varz_name)
    global PROM_INSTANCES
    if prom_name not in PROM_INSTANCES: PROM_INSTANCES[prom_name] = factory(prom_name, '', ['program'])
    return PROM_INSTANCES[prom_name].labels(PROGRAM_NAME)


def metrics_handler(request):
    # This is an adaptor that matches the kcore handler API, but makes use of
    # prometheus_client.exposition.py to perform the work.
    # Essentially this is a translation of prometheus_client.exposition.do_GET().

    # ----- auto_healthz

    # If the webserver registered itself with our singleton, try to call its
    # /healthz handler, and translate the results into metrics.
    if WEBSERVER:
        # The API for _find_handler is more convenient than find_and_run_handler,
        # as we don't need a fake request.  We also shouldn't cache the results
        # of finding the handler, as the user might change the handler map.
        hh = WEBSERVER._find_handler('/healthz')
        if hh:
            out = hh.func(request)
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
