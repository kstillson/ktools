
'''A very simple (but somewhat extensible) persistence mechanism for Python data.

It is frequently the case that datasets are small and simple enough that they
fit nicely into Python's existing data-structures, and although the data
doesn't change much, it does change sometimes, and that needs to be persisted.
Setting up a whole external database is way overkill in this case, never
mind all the trouble of creating and maintaining the schema.

Basically all this class does is:

- when you tell it you're changing the data, it both serializes it to disk and
  caches a local in-memory copy.

- when you tell it you want to read the data, it checks if the file has been
  updated since the last cache update.  If not, it returns the cache, if so,
  it deserializes the file, updates the cache, and returns that.

Things are made a little more complicated by this additional goal: the
serialized data format should be easily machine-readable, human-readable and
human-modifyable (assuming it's not encrypted, which is also an option).

The base Persister class provides simple "serialize" and "deserialize" methods
that work reasonably for simple Python types (numbers, strings, lists, dicts,
etc).  But things get more complicated when @dataclass instances are involved,
primarily because deserialize() uses eval() to read the data, and needs to run
in a context that knows about the @dataclass type.  Therefore, several derived
classes are provided that specialize the deserialize() and serialize() methods
for some common arrangements: a stand-alone @dataclass, and lists and dicts of
@dataclass's.

There are simple get_data() and set_data() methods.  You don't need to call
get_data() every time you reference the data, just when you need to check if
the data has changed since the last time you called get_data().

There are also @contextmanager methods for those who prefer that structure.

And there are methods that provide either thread-based or file-based locking,
if you want to be moderately sure that concurrent writes don't mess things up.
However, these aren't thoroughly tested, and if you've really got a highly
concurrent application with strong concurrency guarantee requirements, you
should probably use a real database anyway. '''

import os, sys
from contextlib import contextmanager

import kcore.uncommon as UC

class Persister:
    # ---------- primary API

    def __init__(self, filename=None, default_value=None, password=None):
        '''filename can be passed as None (e.g. if you don't know it yet because
           this instance is created as a global variable and command-line flags
           indicating the filename haven't been parsed yet.  But if you pass
           filename=None, you must set the .filename field directly before any
           file-based actions take place, or those actions will (silently) fail.

           default_value is so that if neither the internal cache nor the
           saved file have contents, you can get a more useful starting point,
           like an empty list, empty dict, or blank initialized class.

           providing a password will encrypt the stored data using
           kcore.uncommon.symmetric_crypt().
        '''

        self.filename = filename
        self.default_value = default_value
        self.password = password

        self.cache = self.default_value
        self.file_lock = None
        self.cache_mtime = 0
        self.thread_lock = None
        if filename: self.load_from_file()

    # ----- simple getter and setter

    # Can't call it "get" as that would conflct with Dict.get() in derived classes.
    def get_data(self):
        return self.cache if self.is_cache_fresh() else self.load_from_file()

    def set_data(self, data=None):
        '''Passing data=None just saves the current cached data.'''
        if data: self.cache = data
        self.save_to_file()

    # ----- context manager getter and setter

    @contextmanager
    def get_ro(self):
        yield self.get_data()

    @contextmanager
    def get_rw(self):
        '''Yield latest data, then save any changes upon exit.
           WARNING: only works for types where a pointer is returned, i.e. things
           like lists and dicts, not simple things like ints and strings.  For
           those atomic types, use set_data().'''

        local_data = self.get_data()
        if local_data is None:
            self.cache = local_data = self.default_value
        yield local_data

        self.save_to_file()

    # ---------- API with locking options

    @contextmanager
    def get_rw_locked_thread(self):
        import threading
        if not self.thread_lock: self.thread_lock = threading.thread_lock()
        with self.thread_lock:
            local_data = self.get_ro()
            yield local_data
            self.save_to_file()
            self.cache = local_data

    @contextmanager
    def get_rw_locked_file(self):
        import uncommon as UC
        if not self.file_lock: self.file_lock = UC.FileLock()
        with self.file_lock:
            local_data = self.get_ro()
            yield local_data
            self.save_to_file()


    # ---------- internal methods

    # ----- serialization (often need to be overridden for more complex data types.)

    def deserialize(self, serialized):
        if not serialized: return self.default_value
        return eval(serialized, {}, {})

    def serialize(self, data):
        out = "'%s'" % data if isinstance(data, str) else str(data)
        return out + '\n'


    # ----- dealing with the saved file

    def get_file_mtime(self):
        try: return os.path.getmtime(self.filename)
        except: return None

    def is_cache_fresh(self):
        return self.cache_mtime == self.get_file_mtime()

    def load_from_file(self):
        if self.filename == '-':
            serialized = sys.stdin.read()
        else:
            if not self.filename or not os.path.isfile(self.filename):
                self.cache = self.default_value
                return self.cache
            with open(self.filename) as f: serialized = f.read()
        
        if self.password:
            serialized = UC.decrypt(serialized, self.password)
            if serialized.startswith('ERROR'): raise ValueError('incorrect password')
        self.cache = self.deserialize(serialized)
        self.cache_mtime = self.get_file_mtime()
        return self.cache

    def save_to_file(self):
        if not self.filename: return False
        serialized = self.serialize(self.cache)
        if self.password: serialized = UC.encrypt(serialized, self.password)
        if self.filename == '-':
            print(serialized)
        else:
            with open(self.filename, 'w') as f: f.write(serialized)
        self.cache_mtime = self.get_file_mtime()
        return True


# ------------------------------------------------------------
# A Persister specialized for storing a @dataclass instance.

class PersisterDC(Persister):
    def __init__(self, filename, dc_type):
        self.filename = filename
        self.dc_type = dc_type
        super().__init__(filename, None)

    def deserialize(self, serialized):
        if not serialized: return None
        locals = { self.dc_type.__name__: self.dc_type }
        try:
            data = eval(serialized, {}, locals)
        except:
            return None
        return data


# ------------------------------------------------------------
# A Persister specialized for dictionaries of @dataclass instances.

class PersisterDictOfDC(Persister):
    def __init__(self, filename, rhs_type, default_value=None, **kwargs):
        if default_value is None: default_value = dict()
        self.filename = filename
        self.rhs_type = rhs_type
        super().__init__(filename=filename, default_value=default_value, **kwargs)

    def deserialize(self, serialized):
        if not serialized: return self.default_value
        locals = { self.rhs_type.__name__: self.rhs_type }
        data = self.default_value
        data.clear()
        for line in serialized.split('\n'):
            if not line or line.startswith('#'): continue
            if not ': ' in line: continue
            k, v_str = line.split(': ', 1)
            k = k.replace("'", "").replace('"', '')
            try:
                data[k] = eval(v_str, {}, locals)
            except:
                return None
        return data

    def serialize(self, data):
        out = '\n'.join([f"'{k}': {str(v)}" for k, v in data.items()])
        return out + '\n'


class DictOfDataclasses(PersisterDictOfDC, dict):
    def __init__(self, filename, rhs_type, **kwargs):
        super().__init__(filename=filename, rhs_type=rhs_type, default_value=self, **kwargs)


# ------------------------------------------------------------
# A Persister specialized for lists of @dataclass instances.

class PersisterListOfDC(Persister):
    def __init__(self, filename, dc_type, default_value=[], **kwargs):
        self.dc_type = dc_type
        super().__init__(filename=filename, default_value=default_value, **kwargs)

    def deserialize(self, serialized):
        if not serialized: return self.default_value
        locals = { self.dc_type.__name__: self.dc_type }
        data = []
        for line in serialized.split('\n'):
            if not line or line.startswith('#'): continue
            try:
                item = eval(line, {}, locals)
            except:
                return None
            data.append(item)
        return data

    def serialize(self, data):
        out = '\n'.join([str(x) for x in data])
        return out + '\n'


class ListOfDataclasses(PersisterListOfDC, list):
    def __init__(self, filename, dc_type, **kwargs):
        super().__init__(filename=filename, dc_type=dc_type, default_value=self, **kwargs)

