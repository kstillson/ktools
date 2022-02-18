
# TODO: add lots of docs

# TODO: add v2 proto that includes command in hashed part, then rm v1


import hashlib, socket, ssl, sys, time

PY_VER = sys.version_info[0]
if PY_VER == 2: import urllib2
else: import urllib.request


USER = None
SECRET = None
ERROR = '-'

SEP = '|'
HASHLEN = 12
WINDOW = 5 * 60


def read_web(url):
  ctx = ssl.create_default_context()
  ctx.check_hostname = False
  ctx.verify_mode = ssl.CERT_NONE
  if PY_VER == 2:
    return urllib2.urlopen(url, context=ctx).read()
  else:
    with urllib.request.urlopen(url, context=ctx) as f:
      return f.read().decode('utf-8')


# A wrapper around query_km() with a retry-forever, with failure delay.
def init(user=None, key_path=None, override_key=None):
  global ERROR, SECRET, USER
  if not user: user = socket.gethostname()
  USER = user
  if override_key:
    SECRET = override_key
    return True
  while True:
    done = query_km(user, key_path)
    if done: return True
    time.sleep(10)


def query_km(user, key_path=None):
  global ERROR, SECRET, USER
  if key_path is None: key_path = socket.gethostname()
  SECRET = read_web('https://jack:4443/%s' % key_path)
  if not SECRET or 'Error' in SECRET or 'ERR' in SECRET:
    ERROR = SECRET if SECRET else '???'
    SECRET = ''
    return False
  ERROR = None
  return True


def t(): return int(time.time())


def gen_key(unused_cmd=None):
  if not SECRET: return 'empty-secret'
  now = t()
  plaintext = '%s%s%s' % (SECRET, SEP, now)
  if PY_VER == 3: plaintext = plaintext.encode('utf-8')
  hash = hashlib.sha1(plaintext).hexdigest()[:12]
  return '%s%s%s%s%s' % (USER, SEP, now, SEP, hash)


# Returns error message or None if all ok.
def check_key(key, unused_cmd=None):
  try:
    id, t0, hash = key.split(SEP)
  except ValueError:
    return 'invalid key (%s)' % key
  my_hash = gen_key(t0, id)
  if my_hash != hash: return 'Incorrect hash'
  now = t()
  delta = abs(int(t0) - now)
  if delta > WINDOW: return 'Invalid timestamp'
  return None

