
import threading, time

SETTINGS = None

def init(settings):
  global SETTINGS
  SETTINGS = settings
  return ['DELAY']


def control(plugin_name, plugin_params, device_name, command):
  global SETTINGS
  try:
      delay_time, delayed_target, delayed_command = plugin_params.split(':')
  except Expcetion:
      return 'DELAY device config error: params should be delay_time:deferred_target:deferred_commend'
  delayed_target.replace('%d', device_name)
  delayed_command.replace('%c', command)

  if settings['debug']:
      # Single threaded syncronous mode.
      time.sleep(delay_time)
      return settings['_control'](deferred_target, deferred_commend)

  else:
      # Background the delay.
      t = threading.Timer(delay_time, SETTINGS['_control'], delayed_target, delayed_command)
      t.start()
      SETTINGS.append(t)
      return f'{device_name}: ok (queued {delay_time} for {delayed_target} -> {delayed_command})'
