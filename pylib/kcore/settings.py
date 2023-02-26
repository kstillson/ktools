#!/usr/bin/python3

'''...'''

import argparse, os, pprint, sys, yaml
from dataclasses import dataclass, field

import kcore.common as C


# ----------

@dataclass
class Setting:
    name: str

    doc: str = 'undocumented'
    override_env_name: str = None
    flag_name: str = None
    flag_aliases: list = field(default_factory=list)  # list of strings
    setting_name: str = None
    env_name: str = None
    override_env_name: str = None
    default: ... = None
    value_type: ... = str     # just used when add_flags() is creating argparse entries.

    cached_value: str = None


# ----------

class Settings:

    # ----- constructors

    def __init__(self, settings_filename=None, settings_data_type='auto',
                 env_override_prefix=None, env_prefix=None, env_list_sep=';',
                 flag_prefix=None, debug_mode=False):
        # store our controls
        self.settings_filename = settings_filename
        self.settings_data_type = settings_data_type
        self.env_override_prefix = env_override_prefix
        self.env_prefix = env_prefix
        self.env_list_sep = env_list_sep
        self.flag_prefix = flag_prefix
        self.debug_mode = debug_mode

        # init internal caches
        self._settings_dict = {}               # settings name -> settings instance
        self._settings_file_value_cache = {}   # settings name -> value
        self._argparse_instance_cache = None
        self._args_dict_cache = {}             # arg name -> value

        # parse the settings file, if provided
        if settings_filename: self.parse_settings_file(settings_filename, settings_data_type)


    # ----- add settings this instance is to control

    def add_setting(self, name, doc='undocumented', value_type=str,
            override_env_name=None, flag_name=None, flag_aliases=[],
            setting_name=None, env_name=None, default=None):
        self._settings_dict[name] = Setting(
            name, doc, override_env_name, flag_name, flag_aliases,
            setting_name, env_name, default, value_type)

    def add_Setting(self, instance_of_Settings):
        self._settings_dict[instance_of_Settings.name] = instance_of_Settings

    def add_Settings(self, iter_of_Settings):
        for setting in iter_of_Settings: self.add_Setting(setting)

    def add_simple_settings(self, iter_of_setting_names):
        for name in iter_of_setting_names: self.add_setting(name)


    # ----- modify an argparse instance to add flags created by controls settings under our control.

    def add_flags(self, argparse_instance):
        self._argparse_instance_cache = argparse_instance
        for setting in self._settings_dict.values():
            flagname = self._get_flag_name(setting)
            if not flagname: continue
            args = [flagname]
            if setting.flag_aliases: args.append(setting.flag_aliases)
            default = str(setting.default) if setting.default else None
            argparse_instance.add_argument(
                *args, type=setting.value_type, default=default, help=setting.doc)

    def set_args(self, parsed_args):
        self._args_dict_cache.update(vars(parsed_args))


    # ----- return setting's values

    def get(self, name, ignore_cache=False):
        setting = self._settings_dict.get(name)
        if not setting:
            answer = self._settings_file_value_cache.get(name)
            if answer:
                if self.debug_mode: print(f'resolved setting "{name}" \t to \t "{answer}" \t as an unregistered setting from settings file', file=sys.stderr)
                return answer
            # Otherwise, we know nothing about this setting, so just return None.
            return None

        if setting.cached_value and not ignore_cache: return setting.cached_value
        answer, how = self._resolve(setting)

        resolve_special = C.special_arg_resolver(answer, name)
        if resolve_special != answer:
            how += f'; after arg resolved for: {answer}'
            answer = resolve_special

        if self.debug_mode:
            print(f'resolved and cached setting "{name}" \t to \t "{answer}" \t via {how}', file=sys.stderr)

        setting.cached_value= answer
        return answer

    def __getitem__(self, name): return self.get(name)

    def get_dict(self):
        return {name: self.get(name) for name in self._settings_dict.keys()}

    def get_setting(self, name): return self._settings_dict.get(name)


    # ----- read in a settings file
    #
    # usually called by the constructor, but can be called manually when using multiple files.
    # returns a dict of settings from loaded file, but effect on self._settings_file_value_cache is cumulative.

    def parse_settings_file(self, filename=None, data_type=None):
        if not filename: filename = self.settings_filename
        else: self.settings_filename = filename
        if not filename:
            if self.debug_mode: print('attempt to parse settings file, but no filename provided', file=sys.stderr)
            return False

        if not data_type: data_type = self.settings_data_type
        else: self.settings_data_type = data_type
        if data_type == 'auto':
            _, ext = os.path.splitext(self.settings_filename)
            data_type = ext[1:]  # strip leading "."
        if self.debug_mode: print(f'reading settings file {filename} of type {data_type}', file=sys.stderr)

        data = C.read_file(filename)
        if not data: raise ValueError(f'unable to read settings file {filename}')
        return self.parse_settings_data(data, data_type, filename)


    def parse_settings_data(self, data, data_type, filename=None):  # filename just for logging...
        self.reset_cached_values()  # If settings already evaluated, results could be changed by this load.
        new_data = {}

        if data_type == 'yaml':
            new_data.update(yaml.safe_load(data))

        elif data_type == 'env':
            for line in data.split('\n'):
                if not line or line.startswith('#') or '=' not in line: continue
                key, value = line.split('=', 1)
                new_data[key.strip()] = value.strip(" \t'\"")

        elif data_type == 'dict':
            new_data.update(eval(data, {}, {}))

        else:
            print(f'unknown settings_data_type: {data_type}', file=sys.stderr)

        if self.debug_mode: print(f'loaded {len(new_data)} settings from {data_type} file {filename}', file=sys.stderr)

        self._settings_file_value_cache.update(new_data)
        return new_data

    # ----- other state maintenance

    def reset_cached_values(self):
        for setting in self._settings_dict.values():
            setting.cached_value = None

    # ----- resolve an individual setting's value
    #       (done here rather than in Setting, as need access to the various caches)

    def _resolve(self, setting):
        # try override environment variable
        varname = self._get_override_env_name(setting)
        val = self._get_env_value(varname, self.env_list_sep)
        print(f'@@EO {varname=} {val=}')
        if val: return val, f'override environment variable ${varname}'

        # Try flag
        if not self._args_dict_cache and self._argparse_instance_cache:
            self._args_dict_cache.update(vars(self._argparse_instance_cache.parse_args()))
        flagname = self._get_flag_name(setting)
        val = self._args_dict_cache.get(flagname.replace('--', '')) if flagname else None
        if val is not None: return val, f'flag {flagname}'

        # Try settings file content
        setting_name = self._get_setting_name(setting)
        val = self._settings_file_value_cache.get(setting_name)
        if val: return val, f'setting {setting_name} from file {self.settings_filename}'

        # Try default environment variable
        varname = self._get_env_name(setting)
        val = self._get_env_value(varname, self.env_list_sep)
        if val: return val, f'environment variable ${varname}'

        # Return the fallback default value
        if isinstance(setting.default, str): return setting.default, 'default string'
        if callable(setting.default): return setting.default(), f'default value function {setting.default.__name__}'
        if setting.default: return str(setting.default), 'default value converted to string'
        return None, 'no value or default value provided'

    # ----- internal naming helpers

    def _get_override_env_name(self, setting):
        if self.env_override_prefix is None: return None
        return f'{self.env_override_prefix or ""}{setting.override_env_name or setting.name}'

    def _get_env_name(self, setting):
        if self.env_prefix is None: return None
        return f'{self.env_prefix or ""}{setting.env_name or setting.name}'

    def _get_env_value(self, varname, env_list_sep=None):
        if not varname: return None
        val = os.environ.get(varname)
        if val and env_list_sep and env_list_sep in val: val = val.split(env_list_sep)
        return val

    def _get_flag_name(self, setting):
        if setting.flag_name and setting.flag_name.startswith('-'): return setting.flag_name
        base = setting.flag_name or setting.name
        if len(base) == 1 and not self.flag_prefix: return '-' + base
        flagname = (self.flag_prefix or "") + base
        return '--' + flagname.replace('-', '_')

    def _get_setting_name(self, setting):
        return setting.setting_name or setting.name


# ---------- main

def parse_main_args(argv):
    default_settings_file = os.path.join(os.environ.get('HOME'), '.ktools.settings')

    ap = C.argparse_epilog(description='settings resolver')
    ap.add_argument('--all',                '-a', action='store_true', help='just parse the settings file and dump its contents, do not attempt to resolve settings from other sources (environment, defaults, etc)')
    ap.add_argument('--debug',              '-d', action='store_true', help='verbose settings resolution data to stsderr')
    ap.add_argument('--settings_filename',  '-s', default=default_settings_file, help='name of settings file to parse')
    ap.add_argument('--settings_file_type', '-t', default='auto', help='yaml, env, or dict')
    ap.add_argument('settings', nargs='*', help='list of settings to resolve')
    return ap.parse_args(argv)


def main(argv=[]):
    args = parse_main_args(argv or sys.argv[1:])
    settings = Settings(args.settings_filename, debug_mode=args.debug)

    if args.all:
        pprint.pprint(settings._settings_file_value_cache)
        return 0

    for setting_name in args.settings:
        prefix = (setting_name + ': ') if len(args.settings) > 1 else ''
        print(f'{prefix}{settings.get(setting_name)}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
