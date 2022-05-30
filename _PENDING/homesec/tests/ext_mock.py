
import inspect, sys

LAST = None
LAST_ARGS = None

def generalized_mock(*args, **kwargs):
  global LAST, LAST_ARGS
  LAST = inspect.stack()[1].code_context[0].strip()
  LAST_ARGS = args
  print(f'ext_mock call: {LAST}; args={LAST_ARGS}', file=sys.stderr)


import ext
for funcname in dir(ext):
  lead = funcname[0]
  if lead.isupper() or lead == '_': continue
  vars()[funcname] = generalized_mock

