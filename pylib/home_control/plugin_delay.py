'''Trivial plugin that runs another plugin after a specified delay.

plugin_params should be in the form:
"{time_to_wait_in_seconds}:{device-after-delay}:{control-after-delay}"

Note that if we are not in debug mode, the logic to delay-and-then-command is
deferred to a background thread, and the control() call returns an immediate
assumption of success.  There is no way to discover the actual success of the
delayed control() call; it is lost other than any logging performed by
whatever plugin eventually processes the command.

'''

import threading, time

SETTINGS = None

def init(settings):
  global SETTINGS
  SETTINGS = settings
  return ['DELAY']


def control(plugin_name, plugin_params, device_name, command):
  plugin_params = plugin_params.replace('%d', device_name).replace('%c', command)
  try:
      delay_time_str, delayed_target, delayed_command = plugin_params.split(':', 2)
      delay_time = int(delay_time_str)
  except Exception:
      return False, f'DELAY device config error: params should be delay_time:delayed_target:delayed_command, but saw "{plugin_params}"'

  global SETTINGS
  if SETTINGS['debug']:
      # Single threaded syncronous mode.
      time.sleep(delay_time)
      return SETTINGS['_control'](delayed_target, delayed_command)

  else:
      # Background the delay.
      t = threading.Timer(delay_time, SETTINGS['_control'], [delayed_target, delayed_command])
      t.start()
      SETTINGS['_threads'].append(t)
      return True, f'{device_name}: ok (queued {delay_time} for {delayed_target} -> {delayed_command})'
