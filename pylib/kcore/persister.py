
'''A very simple (but somewhat extensible) persistence mechanism for Python data.

It is frequently the case that datasets are small and simple enough that they
fit nicely into Python's existing data-structures, and although the data
doesn't change much, it does change sometimes, and that needs to be persisted.
Setting up a whole external database is way overkill in this case, never
mind all the trouble of creating and maintaining the schema.

Basically all this class does is this:

- when you tell it you're changing the data, it both serializes it to disk and
  caches a local in-memory copy.

- when you tell it you want to read the data, it checks if the file has been
  updated since the last cache update.  If not, it returns the cache, if so,
  it deserializes the file, updates the cache, and returns that.

Things are made a little more complicated by this additional goal: the
serialized data format should be easily human-readable and human-modifyable.

The base Persister class provides simple "deserialize" and "serialize" methods
that work reasonably for simple Python types (numbers, strings, lists, dicts,
etc).  But things get more complicated when @dataclass instances are involved,
primarily because deserialize() needs to eval() the serialized data in a
context that knows about the @dataclass type.  Therefore, several derived
classes are provided that specialize the deserialize() and serialize() methods
for some common arrangements: a stand-alone @dataclass, and lists and dicts of
@dataclass's.

There are simple get() and set() methods.  You don't need to call get() every
time you reference the data, just when you need to check if the data has changed
since the last time you called get().

There are also @contextmanager methods for those who prefer that structure
(although the get_ro one is a bit pointless).

And there are methods that provide either thread-based or file-based locking,
if you want to be moderately sure that concurrent writes don't mess things up.
However, these aren't thoroughly tested, and if you've really got a highly
concurrent application with strong concurrency guarantee requirements, you
should probably use a real database anyway.

'''

import os
from contextlib import contextmanager

class Persister:
    # ---------- primary API

    def __init__(self, filename=None, default_value=None):
        '''filename can be passed as None, but must then be set either by directly
           setting the field or calling load_from_file() or save_to_file().
           and providing the filename there.'''
        self.filename = filename
        self.default_value = default_value

        self.cache = self.default_value
        self.file_lock = None
        self.mtime = 0
        self.thread_lock = None
        self.load_from_file(filename)

    # ----- simple getter and setter

    def get(self):
        return self.cache if self.is_cache_fresh() else self.load_from_file(self.filename)

    # Passing None for data just saves the current cached data.
    def set(self, data=None):
        if data: self.cache = data
        self.save_to_file(self.filename)

    # ----- context manager getter and setter

    @contextmanager
    def get_ro(self):
        yield self.get()

    # WARNING: only works for types where a pointer is returned, i.e. things
    # like lists and dicts, not simple things like ints and strings.  For
    # those atomic types, use set().
    #
    # default_value is there so that if neither the internal cache nor the
    # saved file have contents, get_rw can yield some more useful starting
    # point, like an empty list, empty dict, or initialized class.
    @contextmanager
    def get_rw(self, default_value=None):
        local_data = self.get()
        if local_data is None:
            if default_value is None: default_value = self.default_value
            self.cache = local_data = default_value
        yield local_data

        self.save_to_file(self.filename)

    # ---------- API with locking options

    @contextmanager
    def get_rw_locked_thread(self):
        import threading
        if not self.thread_lock: self.thread_lock = threading.thread_lock()
        with self.thread_lock:
            local_data = self.get_ro()
            yield local_data
            self.save_to_file(self.filename)
            self.cache = local_data

    @contextmanager
    def get_rw_locked_file(self):
        import uncommon as UC
        if not self.file_lock: self.file_lock = UC.FileLock()
        with self.file_lock:
            local_data = self.get_ro()
            yield local_data
            self.save_to_file(self.filename)


    # ---------- serialization
    #            (often need to be overridden for more complex data types.)

    def deserialize(self, serialized):
        if not serialized or not os.path.isfile(self.filename): return self.default_value
        with open(self.filename) as f: serialized = f.read()
        return eval(serialized, {}, {})

    def serialize(self, data):
        out = "'%s'" % data if isinstance(data, str) else str(data)
        return out + '\n'


    # ---------- dealing with the saved file

    def get_file_mtime(self):
        try: return os.path.getmtime(self.filename)
        except: return None

    def is_cache_fresh(self):
        return self.mtime == self.get_file_mtime()

    def load_from_file(self, in_filename=None):
        filename = in_filename or self.filename
        self.filename = filename
        if not filename or not os.path.isfile(filename):
            self.cache = self.default_value
            return self.cache

        with open(filename) as f: serialized = f.read()
        self.cache = self.deserialize(serialized)
        self.mtime = self.get_file_mtime()
        return self.cache

    def save_to_file(self, in_filename=None):
        filename = in_filename or self.filename
        self.filename = filename
        if not filename: return False

        with open(self.filename, 'w') as f:
            f.write(self.serialize(self.cache))
        self.mtime = self.get_file_mtime()
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
        data = eval(serialized, {}, locals)
        return data


# ------------------------------------------------------------
# A Persister specialized for dictionaries of @dataclass instances.

class PersisterDictOfDC(Persister):
    def __init__(self, filename, rhs_type, default_value={}):
        self.filename = filename
        self.rhs_type = rhs_type
        super().__init__(filename, default_value)

    def deserialize(self, serialized):
        if not serialized: return self.default_value
        locals = { self.rhs_type.__name__: self.rhs_type }
        data = {}
        for line in serialized.split('\n'):
            if not line or line.startswith('#'): continue
            if not ': ' in line: continue
            k, v_str = line.split(': ', 1)
            k = k.replace("'", "").replace('"', '')
            data[k] = eval(v_str, {}, locals)
        return data

    def serialize(self, data):
        out = '\n'.join([f"'{k}': {str(v)}" for k, v in data.items()])
        return out + '\n'


class DictOfDataclasses(PersisterDictOfDC, dict):
    def __init__(self, filename, rhs_type):
        super().__init__(filename, rhs_type, self)


# ------------------------------------------------------------
# A Persister specialized for lists of @dataclass instances.

class PersisterListOfDC(Persister):
    def __init__(self, filename, dc_type, default_value=[]):
        self.dc_type = dc_type
        super().__init__(filename, default_value)

    def deserialize(self, serialized):
        if not serialized: return self.default_value
        locals = { self.dc_type.__name__: self.dc_type }
        data = []
        for line in serialized.split('\n'):
            if not line or line.startswith('#'): continue
            item = eval(line, {}, locals)
            data.append(item)
        return data

    def serialize(self, data):
        out = '\n'.join([str(x) for x in data])
        return out + '\n'


class ListOfDataclasses(PersisterListOfDC, list):
    def __init__(self, filename, dc_type):
        super().__init__(filename, dc_type, self)
