#!/usr/bin/python3

'''Send commands to Shelly Plug smart plugs

  https://shelly-api-docs.shelly.cloud/gen2/General/RPCProtocol
'''

import argparse, socket, sys
import kcore.common as C


DEFAULT_TIMEOUT = 5
SETTINGS = {}

CMD_LOOKUP = {
 # ---------- basic set relay status

    'on'             : { 'method': 'Switch.Set', 'id': 0,  'on': 'true' },
    'off'            : { 'method': 'Switch.Set', 'id': 0,  'on': 'false' },
    'toggle'         : { 'method': 'Switch.Toggle', 'id': 0 },

  # approximate (any dim level maps to "on") hard-coded normalizations...
  # TODO(defer): something better...
    'dim'            : { 'method': 'Switch.Set', 'id': 0,  'on': 'true' },
    'dim:@@'         : { 'method': 'Switch.Set', 'id': 0,  'on': 'true' },
    'med'            : { 'method': 'Switch.Set', 'id': 0,  'on': 'true' },
    'full'           : { 'method': 'Switch.Set', 'id': 0,  'on': 'true' },
    'bulb-on'        : { 'method': 'Switch.Set', 'id': 0,  'on': 'true' },
    'bulb-dim'       : { 'method': 'Switch.Set', 'id': 0,  'on': 'true' },
    'bulb-dim:@@'    : { 'method': 'Switch.Set', 'id': 0,  'on': 'true' },
    'bulb-med'       : { 'method': 'Switch.Set', 'id': 0,  'on': 'true' },
    'bulb-full'      : { 'method': 'Switch.Set', 'id': 0,  'on': 'true' },


# ---------- queries

    'info'           : { 'method': 'Shelly.GetStatus' },
    'status'         : { 'method': 'Switch.GetStatus', 'id': 0 },

}


# ---------- hc plugin API entry points

def init(settings):
    global SETTINGS
    SETTINGS = settings
    return [ 'SHELLY-PLUG' ]


def control(plugin_name, plugin_params, device_name, dev_command):
    plugin_params = plugin_params.replace('%d', device_name).replace('%c', dev_command)
    hostname, command = plugin_params.split(':', 1)
    return shelly_send(hostname, command)


# ---------- actual command io

def shelly_send(hostname, command):
    if ':' in command:
        tmp, cmd_param = command.split(':', 1)
        command = tmp + ':@@'    # (This is what to we'll earch for in CMD_LOOKUP)
    else:
        cmd_param = None

    params = CMD_LOOKUP.get(command)
    if not params: return False, f'{hostname}: unknown shelly command: {command}'

    method = params.pop('method')
    url = f'http://{hostname}/rpc/{method}'

    resp = C.web_get(url, get_dict=params, timeout=SETTINGS.get('timeout', 10))
    return resp.ok, str(resp)


# ---------- main (cli)

def parse_args(argv):
    ap = argparse.ArgumentParser(description='tplink command sender')
    ap.add_argument('--debug', '-d', action='store_true', help='wait for response, print extra diagnostics')
    ap.add_argument('--raw', '-r', action='store_true', help='return raw output rather than simplified')
    ap.add_argument('--test', '-T', action='store_true', help='print what would be done without doing it')
    ap.add_argument('--timeout', '-t', default=DEFAULT_TIMEOUT, help='timeout for response (seconds)')
    ap.add_argument('hostname', help='device to control (dns or ip)')
    ap.add_argument('command', nargs='?', default='on', help='command to send')
    return ap.parse_args(argv)


def main():
    args = parse_args(sys.argv[1:])

    # Copy appropriate items from args to global SETTINGS (which is shared with API caller)
    global SETTINGS
    for i in ['debug', 'raw', 'test', 'timeout']: SETTINGS[i] = getattr(args, i)

    return shelly_send(args.hostname, args.command)


if __name__ == '__main__':
    print(main())
