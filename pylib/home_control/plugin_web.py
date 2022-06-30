'''
TODO(doc)

'''

import requests, threading

SETTINGS = None


def init(settings):
  global SETTINGS
  SETTINGS = settings
  return ['HTTP', 'HTTPS', 'WEB', 'WEBS']


def control(plugin_name, plugin_params, device_name, command):
  if plugin_name in ['HTTP', 'WEB']: prefix = 'http://'
  elif plugin_name in ['HTTPS, WEBS']: prefix = 'https://'
  else: return False, f'error: unknown plugin {plugin_name}'

  url = prefix + plugin_params
  url = url.replace('%d', device_name).replace('%c', command)


  # ----- If we're in debug mode, send the web request synchronously
  #       and return the actual results.

  if SETTINGS['debug']:
    try:
      rslt = requests.get(url, allow_redirects=True, timeout=SETTINGS['timeout'])
      status = 'ok' if rslt.ok else 'error'
      details = f'{device_name}: {status} [{rslt.status_code}]: {rslt.text}'
      print(f'web request [{url}] -> {details}')
      return rslt.ok, details

    except Exception as e:
      return False, f'{plugin_name} error: {str(e)} for {url}'

  # ----- If we're not in debug mode, send the request in the background.

  threading.Thread(target=requests.get,
                   kwargs={'url': url, 'allow_redirects': True, 'timeout': SETTINGS['timeout']},
                   daemon=True).start()

  return True, f'{device_name}: background sent {url}'
