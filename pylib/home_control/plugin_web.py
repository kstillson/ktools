
import requests

SETTINGS = None

def process_web_request(addr, in_unit='web'):
  if in_unit == 'webs':
    host, path = addr.split('/', 1)
    url = 'https://' + host + ':8443/' + path
  else:
    url = 'http://' + addr


# ----------

def init(settings):
  global SETTINGS
  SETTINGS = settings
  return ['HTTP', 'HTTPS', 'WEB', 'WEBS']


def control(plugin_name, plugin_params, device_name, command):
  if plugin_name in ['HTTP', 'WEB']: prefix = 'http://'
  elif plugin_name in ['HTTPS, WEBS']: prefix = 'https://'
  else: return False, f'error: unknown plugin {plugin_name}'

  url = prefix + plugin_params
  url.replace('%d', device_name)
  url.replace('%c', command)

  # TODO: support backgrounded request for non-debug mode.
  
  try:
    r = requests.get(url, allow_redirects=True, timeout=SETTINGS['timeout'])
  except Exception as e:
    return False, f'{plugin_name} error: {str(e)} for {url}'
  if SETTINGS['debug']: print('web request [%s] -> (%d): %s' % (url, r.status_code, r.text))
  status = 'ok' if r.status_code == 200 else 'error'
  return (status == 'ok'), f'{device_name}: {status} [{r.status_code}]: {r.text}'
  
