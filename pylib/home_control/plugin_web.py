'''home-control plugin to make web GET requests.

The plugin_params should be in the form "host[:port]/path", i.e. it should not
include the "http[s]://" prefix.  Whether TLS is used or not is determined by
the name of the plugin that's referenced.  For example, the following entries
in DEVICES:
  'insecure-get':   'WEB:server:8080/path',
  'secure-get':     'HTTPS:server2/other-path',

In debug mode, the GET request is performed synchronously and the correct
success or failure details are returned.  When not in debug mode, the GET
request is performed in a background thread, and the resulting status is lost;
the plugin returns a presumption of success.

'''

import requests, threading

SETTINGS = None


def init(settings):
  global SETTINGS
  SETTINGS = settings
  return ['HTTP', 'HTTPS', 'WEB', 'WEBS']


def control(plugin_name, plugin_params, device_name, command):
  if plugin_name in ['HTTP', 'WEB']: prefix = 'http://'
  elif plugin_name in ['HTTPS', 'WEBS']: prefix = 'https://'
  else: return False, f'error: unknown plugin {plugin_name}'

  url = prefix + plugin_params
  url = url.replace('%d', device_name).replace('%c', command)


  # ----- If we're in synchronous mode, send the web request synchronously
  #       and return the actual results.

  if not SETTINGS['fast']:
    try:
      rslt = requests.get(url, allow_redirects=True, timeout=SETTINGS['timeout'])
      status = 'ok' if rslt.ok else 'error'
      details = f'{device_name}: {status} [{rslt.status_code}]: {rslt.text}'
      if SETTINGS['debug']: print(f'DEBUG: web request [{url}] -> {details}')
      return rslt.ok, details

    except Exception as e:
      return False, f'{plugin_name} error: {str(e)} for {url}'

  # ----- If we're not in debug mode, send the request in the background.

  threading.Thread(target=requests.get,
                   kwargs={'url': url, 'allow_redirects': True, 'timeout': SETTINGS['timeout']},
                   daemon=True).start()

  return True, f'{device_name}: background sent {url}'
