#!/usr/bin/python3

'''Merge settings from various sources in an organized way.

I frequently find generating the correct settings for a particular operation
involves combining values from various different sources.  For example, some
settings are machine-specific and should come from global settings files or
perhaps environment variables, while some are operation-specific, and should
come from flags, a local settings file, and/or environment variables.  And
sometimes I need to override the normal settings, but don't want to change the
settings file for a one-time thing, so something like flags or environmental
variable override seem ideal.

This module combines all that into a single easy-to-use interface, and
supports several different formats for settings files (and auto-type detection
based on filename extension).

The class is integrated with kcore.common.special_arg_resolver, so settings
can pull values from files, keymaster, password-entry-via-tty, etc.

The easiest use of the class is just to pull in one-or-more settings files
(latest ones override earlier ones when they contain the same settings), e.g.:

  s = settings.Settings('global_settings_file.yaml')   # default global settings
  print(s['setting_name']                              # here'access the settings

You can add features (and complexity) incrementally

  s = settings.Settings('global_settings_file.env')   # default global settings
  s.parse_settings_file('local_settings_file.yaml')   # higher priority local settings
  s.add_setting('setting1', default='some-default', env_name='SETTING1')

With this, s['setting1'] will return the contents of $env_setting1 if that's defined,
and "some-default" otherwise.

Settings files can also contain include directives, which can point to other
individual settings files, glob expressions, or entire directories.
Similarly, arguments that provide a settings filename to either the Settings
constructor or to the parse_settings_file() method can be lists of filenames
or glob expressions.

A slightly more fully-featured use might look something more like this:

----- test.py:

import argparse
ap = argparse.ArgumentParser(add_help=False)  # Defer help until after we've added our settings-based flags.
ap.add_argument('--global_settings_file', '-g', default=None)
ap.add_argument('--local_settings_file', '-l', default=None)
ap.add_argument('--other_flags_unrelated_to_settings', default=None)
ap.add_argument('--help', '-h', action='store_true', help='print help')
args, _ = ap.parse_known_args()   # User may specify settings-based flags we haven't added to the parser yet; ignore those for now.

import kcore.settings as S
s = S.Settings(args.global_settings_file)
s.parse_settings_file(args.local_settings_file)
s.add_Settings([
  S.Setting('color', env_name='color', override_env_name='OVERRIDE_color', flag_name='color_name', flag_aliases=['-c'], default='black', doc='color we want'),
  S.Setting('size',  env_name='SIZE',  override_env_name='OVERRIDE_size',  doc='size we want'),
])

s.add_flags(ap)          # Add our defined settings to the argparser's flags,
args = ap.parse_args()   # and re-parse.

if args.help:            # We turned off auto-help, do it manually now if requested.
    print(ap.format_help())
else:
    print(f"color: {s['color']},  size: {s['size']}")

-----

You can then test out some of the interesting combinations like so:

./test.py -h
./test.py
./test.py -c red
./test.py --size extra-medium
COLOR=funky ./test.py   # no effect as flag default overrides env
OVERRIDE_color=green ./test.py
OVERRIDE_color=green ./test.py --color overriden_by_env
SIZE=tiny ./test.py
SIZE=tiny ./test.py --size 'flag-overrides-env'
OVERRIDE_size=huge ./test.py --size 'overriden-by-override-flag'

# and adding some settings files into the mix:
echo "{ 'color': 'blue', 'size': 'small' }" > global.dict
echo "color=pink" > local.env
./test.py -g global.dict -l local.env   # flag default overrides global setting for color
./test.py -g global.dict -l local.env --color=brown
OVERRIDE_color=yellow ./test.py -g global.dict -l local.env --color=brown --size=extra-medium

'''

import argparse, glob, os, sys, yaml
from dataclasses import dataclass, field
from typing import List

import kcore.common as C


@dataclass
class Setting:
    name: str                       # required: internal name by which we refer to this setting

    # settings metadata (used when add_flags() is creating argparse entries).
    doc: str = 'undocumented'
    flag_type: ... = str

    # settings sources, listed in presidence order
    override_env_name: str = None   # name of environment variable that overrides all other sources.  Not used unless explicitly set.
    flag_name: str = None           # name of flag to add for setting this setting.  Should not include "--" prefix (because it's going to have Settings.flag_prefix prepending).  This setting is disabled if Settings.flag_prefix is None.  If Settings.flag_prefix is not none (including ''), this defaults to {name}
    flag_aliases: List[str] = field(default_factory=list)  # list of aliases for the flag_name;   should include the "-" or "--" prefixes.
    setting_name: str = None        # name of the field in setting files where we look for this setting.  Defaults to {name}
    env_name: str = None            # name of environment variable to use if other sources don't provide a value.  Not used unless explicitly set.
    default: ... = None             # default value to use if no other source provides one.  can be a string or a callable that returns a string.

    # other controls
    default_env_value: str = None   # if value contains $X but $X not defined, return this.  If None, raise a ValueError.

    # internal cache for already-resolved setting values
    disable_cache: bool = False
    cached_value: str = None
    how: str = None                 # how the cached value was determined

# ----------

class Settings:

    # ----- constructors

    def __init__(self, settings_filename=None, add_Settings=[],
                 settings_data_type='auto', env_list_sep=';',
                 flag_prefix=None, include_directive='!include',
                 replacement_map={}, debug=False):
        # store our controls
        self.settings_filename = settings_filename
        self.settings_data_type = settings_data_type
        self.env_list_sep = env_list_sep
        self.flag_prefix = flag_prefix
        self.include_directive = include_directive
        self.replacement_map = replacement_map
        self.debug = debug

        # init internal caches
        self._settings_dict = {}               # settings name -> settings instance
        self._settings_file_value_cache = {}   # settings name -> value
        self._argparse_instance_cache = None
        self._args_dict_cache = {}             # arg name -> value

        # add any initially provided settings
        if add_Settings: self.add_Settings(add_Settings)

        # parse settings file(s), if provided
        if settings_filename: self.parse_settings_file(settings_filename, settings_data_type)


    # ----- add settings this instance is to control

    def add_setting(self, name, *args, **kwargs):
        self._settings_dict[name] = Setting(name, *args, **kwargs)

    def add_Setting(self, instance_of_Settings):
        self._settings_dict[instance_of_Settings.name] = instance_of_Settings

    def add_Settings(self, iter_of_Settings):
        for setting in iter_of_Settings: self.add_Setting(setting)

    def add_settings_groups(self, setting_groups, selected_groups=[]):
        if isinstance(setting_groups, dict): setting_groups = setting_groups.values()
        group_names = [i.name for i in setting_groups]
        for name in selected_groups:
            if name not in group_names: raise ValueError(f'unknown group requested: {name}')
        for group in setting_groups:
            if selected_groups and not group.name in selected_groups: continue
            self.add_Settings(group.settings._settings_dict.values())

    def add_simple_settings(self, iter_of_setting_names):
        for name in iter_of_setting_names: self.add_setting(name)

    def add_settings_from_settings_file_cache(self):
        for name, val in self._settings_file_value_cache.items():
            if not name in self._settings_dict:
                self.add_setting(name)


    # ----- tweak existing settings
    #       In-case you want to change things imported as simple settings.

    def set_replacement_map(self, replacement_map):
        '''Mostly for things like mapping "@basedir" to actual base directory values.'''
        self.replacement_map = replacement_map

    def tweak_setting(self, name, attr_name, newval):
        setting = self._settings_dict.get(name)
        setattr(setting, attr_name, newval.replace('{name}', setting.name))

    def tweak_all_settings(self, attr_name, replacement, context=None):
        # context is an arbitrary value passed as input to replacement() if replacemnt is callable.
        for setting in self._settings_dict.values():
            orig_val = getattr(setting, attr_name)
            newval = replacement(setting, attr_name, context) if callable(replacement) else replacement
            if newval: newval = newval.replace('{name}', setting.name)
            if newval != orig_val:
                ##@@ if self.debug: print(f'DEBUG: setting {setting.name}.{attr_name} tweaked "{orig_val}" -> "{newval}"', file=sys.stderr)
                setattr(setting, attr_name, newval)


    # ----- modify an argparse instance to add flags created by controls settings under our control.

    def add_flags(self, argparse_instance):
        if not self._argparse_instance_cache: self._argparse_instance_cache = argparse_instance
        for setting in self._settings_dict.values():
            flagname = self._get_flag_name(setting)
            if not flagname: continue
            args = [flagname]
            if setting.flag_aliases: args.extend(setting.flag_aliases)
            kwargs = {}
            if setting.flag_type == bool:
                default = eval_bool(setting.default)
                kwargs['action'] = 'store_false' if default else 'store_true'
                # Note: we do not propagate local var default to
                # kwargs['default'], because then the flag would always return
                # a value, and flags override explicit settings from files, so
                # this would mean that a default would cause the flag default
                # to always be used, even if no flag value was provided in the
                # CLI args.  Instead, specifically set the flag default to None.
                kwargs['default'] = None
            else:
                kwargs['type'] = setting.flag_type
            argparse_instance.add_argument(*args, **kwargs, help=setting.doc)

    def add_flags_in_groups(self, argparse_instance, settings_groups, selected_groups=None):
        if not self._argparse_instance_cache: self._argparse_instance_cache = argparse_instance
        if isinstance(settings_groups, dict): settings_groups = settings_groups.values()
        for group in settings_groups:
            if selected_groups and not group.name in selected_groups: continue
            ap_group = argparse_instance.add_argument_group(group.name, group.doc)
            group.settings.add_flags(ap_group)

    def set_args(self, parsed_args):
        self._args_dict_cache.update(vars(parsed_args))
        if self.debug: print(f'DEBUG: args updated to: {self._args_dict_cache}', file=sys.stderr)


    # ----- return setting's values

    def get(self, name, ignore_cache=False):
        # find our setting instance from the name
        setting = self._settings_dict.get(name)
        if not setting:
            answer = self._settings_file_value_cache.get(name)
            if answer:
                if self.debug: print(f'resolved setting "{name}" \t to \t "{answer}" \t as an unregistered setting from settings file', file=sys.stderr)
                return answer
            if self.debug: print(f'setting {name} requested, but we have no information on it; returning None', file=sys.stderr)
            return None

        # handle already-cached values
        if setting.cached_value and not setting.disable_cache and not ignore_cache:
            if self.debug: print(f'returning cached value {name} = {setting.cached_value}', file=sys.stderr)
            return setting.cached_value

        answer, how = self._resolve(setting)

        if self.replacement_map:
            if isinstance(answer, str):
                replacement = self.replacement_map.get(answer, False)
                if replacement is not False and replacement != answer:
                    how += f' (and replacement_map mapped from original value of "{answer})"'
                    answer = replacement

        if self.debug:
            print(f'resolved and cached setting "{name}" \t to \t "{answer}" \t via {how}', file=sys.stderr)

        if not setting.disable_cache:
            setting.cached_value, setting.how = answer, how
        return answer


    def __getitem__(self, name): return self.get(name)

    def get_dict(self):
        return {name: self.get(name) for name in self._settings_dict.keys()}

    def get_setting(self, name): return self._settings_dict.get(name)

    def get_bool(self, name, ignore_cache=False):
        return eval_bool(self.get(name, ignore_cache))

    def get_int(self, name, default=None, ignore_cache=False):
        val = self.get(name, ignore_cache)
        if isinstance(val, int): return val
        return int(val) if val and val.isdigit() else default


    # ----- read in a settings file
    #
    # usually called by the constructor, but can be called manually when using multiple files.
    # returns a dict of settings from loaded file, but effect on self._settings_file_value_cache is cumulative.

    def parse_settings_file(self, filename=None, data_type=None):
        # Handle special types of incoming filenames (lists and globs)
        if isinstance(filename, list):
            cumulative = {}
            for f in filename: cumulative.update(self.parse_settings_file(f))
            return cumulative

        elif '*' in filename:
            cumulative = {}
            for f in glob.glob(filename): cumulative.update(self.parse_settings_file(f))
            return cumulative

        # Handle a regular filename
        if not filename: filename = self.settings_filename
        else: self.settings_filename = filename
        if not filename:
            if self.debug: print('attempt to parse settings file, but no filename provided', file=sys.stderr)
            return False

        filename = filename.replace('$HOME', os.environ['HOME']).replace('${HOME}', os.environ['HOME'])

        if not data_type: data_type = self.settings_data_type
        else: self.settings_data_type = data_type
        if data_type == 'auto':
            _, ext = os.path.splitext(self.settings_filename)
            data_type = ext[1:]  # strip leading "."
        if self.debug: print(f'reading settings file {filename} of type {data_type}', file=sys.stderr)

        data = C.read_file(filename)
        if data is False: raise ValueError(f'unable to read settings file {filename}')
        return self.parse_settings_data(data, data_type, filename)


    def parse_settings_data(self, data, data_type, source=None):  # source just for logging...
        self.reset_cached_values()  # If settings already evaluated, results could be changed by this load.
        new_settings = {}

        if self.include_directive in data: data = self._handle_includes(data)

        if not data: return data

        if data_type in ('yaml', 'settings'):
            new_settings.update(yaml.safe_load(data))

        elif data_type == 'env':
            for line in data.split('\n'):
                if not line or line.startswith('#') or '=' not in line: continue
                key, value = line.split('=', 1)
                new_settings[key.strip()] = value.strip(" \t'\"")

        elif data_type == 'dict':
            new_settings.update(eval(data, {}, {}))

        else:
            print(f'unknown settings_data_type: {data_type}', file=sys.stderr)

        if self.debug: print(f'loaded {len(new_settings)} settings from {data_type} source {source}: {new_settings}', file=sys.stderr)

        self._settings_file_value_cache.update(new_settings)
        self.add_settings_from_settings_file_cache()
        return new_settings

    # ----- other state maintenance

    def reset_cached_values(self):
        for setting in self._settings_dict.values():
            setting.cached_value = None

    # ----- resolve an individual setting's value
    #       (done here rather than in Setting, as need access to the various caches)

    def _resolve(self, setting):
        answer, how = self._search_sources_for_setting(setting)

        # Check integration with special_arg_resolver (file and keymaster integration)
        resolve_special = C.special_arg_resolver(answer, setting.name, setting.default_env_value)
        if resolve_special != answer:
            how += f'; after arg resolved for: {answer}'
            answer = resolve_special
        if answer == r'\-': answer = '-'  # undo escaping used to precent special_arg_resolver for intended value of "-"

        return answer, how


    def _search_sources_for_setting(self, setting):
        # try override environment variable
        val = self._get_env_value(setting.override_env_name, setting.name, self.env_list_sep)
        if val: return val, f'override environment variable ${setting.override_env_name}'

        # Try flag
        if not self._args_dict_cache and self._argparse_instance_cache:
            tmp = vars(self._argparse_instance_cache.parse_args())
            self._args_dict_cache.update(tmp)
        flagname = self._get_flag_name(setting)
        val = self._args_dict_cache.get(flagname.replace('--', '')) if flagname else None
        if val is not None: return val, f'flag {flagname}'

        # Try settings file content
        setting_name = self._get_setting_name(setting)
        val = self._settings_file_value_cache.get(setting_name)
        if val: return val, f'setting {setting_name} from file {self.settings_filename}'

        # Try default environment variable
        val = self._get_env_value(setting.env_name, setting.name, self.env_list_sep)
        if val: return val, f'environment variable ${setting.env_name or setting.name}'

        # Return the fallback default value
        if isinstance(setting.default, str): return setting.default, 'default string'
        if callable(setting.default): return setting.default(), f'default value function {setting.default.__name__}'
        if setting.default: return str(setting.default), 'default value converted to string'
        return None, 'no value or default value provided'

    # ----- internal naming helpers

    def _get_env_value(self, varname, setting_name, env_list_sep=None):
        if varname is None: return None            # Disabled
        if not varname: varname = setting_name     # Not disabled but blank; use the setting name
        val = os.environ.get(varname)
        if val and env_list_sep and env_list_sep in val: val = val.split(env_list_sep)
        return val

    def _get_flag_name(self, setting):
        if self.flag_prefix is None: return None   # This disables flags.  Set to '' to enable but have it empty.
        if setting.flag_name and setting.flag_name.startswith('-'): return setting.flag_name  # Trick to bypass flag_prefix.
        base = setting.flag_name or setting.name
        if len(base) == 1 and not self.flag_prefix: return '-' + base
        flagname = self.flag_prefix + base
        return '--' + flagname.replace('-', '_')

    def _get_setting_name(self, setting):
        return setting.setting_name or setting.name

    # ----- include directives

    def _handle_includes(self, data):
        include_directive_lines = []
        lines = data.split('\n')
        for count, line in enumerate(lines):
            if line.startswith(self.include_directive): include_directive_lines.append(count)

        for line_number in include_directive_lines:
            line = lines[line_number]
            _, param = line.split(self.include_directive, 1)
            param = param.strip()
            if self.debug: print(f'processing include directive: {param}', file=sys.stderr)

            count = 0
            if os.path.isfile(param):
                count = len(self.parse_settings_file(param))

            elif os.path.isdir(param):
                for f in glob.glob(os.path.join(param, '*')):
                    count += len(self.parse_settings_file(f))

            elif '*' in param:
                for f in glob.glob(param):
                    count += len(self.parse_settings_file(f))

            else:
                raise ValueError(f'do not known how to handle include directive: {line}')

            if self.debug:
                if count > 0: print(f'include directive {param} added {count} settings.')
                else: print(f'WARNING: include directive {param} added no settings (failed glob?).')

        for line_number in reversed(include_directive_lines): lines.pop(line_number)
        return '\n'.join(lines)


# ---------- useful for creating a list of different SettingsGroup's

@dataclass
class SettingsGroup:
    name: str
    doc: str = None
    settings: Settings = None


# ---------- other assorted helpers

def eval_bool(value):
    if isinstance(value, bool): return value
    return value in ['1', 'y', 'Y', 'T', 'true', 'True', 'TRUE']


# ---------- main

def parse_main_args(argv):
    default_settings_file = os.path.join(os.environ.get('HOME'), '.ktools.settings')

    ap = C.argparse_epilog(description='settings resolver')
    ap.add_argument('--all',                '-a', action='store_true', help='just parse the settings file and dump its contents, do not attempt to resolve settings from other sources (environment, defaults, etc)')
    ap.add_argument('--debug',              '-d', action='store_true', help='verbose settings resolution data to stsderr')
    ap.add_argument('--settings_filename',  '-s', default=default_settings_file, help='name of settings file to parse')
    ap.add_argument('--settings_file_type', '-t', default='auto', help='yaml, env, or dict')
    ap.add_argument('--quotes',             '-q', action='store_true', help='add quotes around RHS of output (useful if feeding into shell assignments)')
    ap.add_argument('settings', nargs='*', help='list of settings to resolve')
    return ap.parse_args(argv) if argv else ap


def main(argv=[]):
    args = parse_main_args(argv or sys.argv[1:])
    settings = Settings(args.settings_filename, debug=args.debug)
    settings_dict = settings.get_dict()

    q = "'" if args.quotes else ""

    if args.all:
        for name, val in settings_dict.items(): print(f'{name}={q}{val}{q}')
    else:
        for name in args.settings: print(f'{name}={q}{settings_dict.get(name)}{q}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
