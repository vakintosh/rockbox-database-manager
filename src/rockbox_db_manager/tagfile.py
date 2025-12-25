import math
import os
import struct

from .defs import MAGIC, ENCODING

class TagFile:
    def __init__(self, entries=None):
        self.magic = MAGIC
        self.entrydict = {}
        self.entries = []
        self.offsets = {}
        if entries is not None:
            for entry in entries:
                self.append(entry)

    def __contains__(self, key):
        return key in self.entrydict

    def __getitem__(self, key):
        return self.entrydict[key]

    def __iter__(self):
        return iter(self.entries)

    @property
    def count(self):
        return len(self.entries)

    @property
    def size(self):
        return sum(entry.size for entry in self.entries)

    def append(self, entry):
        self.entrydict[entry.key] = entry
        self.entries.append(entry)

    def sort(self):
        self.entries.sort(key = lambda entry: entry.sort)

    def to_file(self, f):
        self.offsets.clear()
        f.write(struct.pack('III', self.magic, self.size, self.count))
        for entry in self.entries:
            self.offsets[f.tell()] = entry
            entry.to_file(f)

    def write(self, filename):
        with open(filename, 'wb') as f:
            self.to_file(f)

    @staticmethod
    def from_file(f, is_path=False):
        """Return a TagFile given a file object."""
        tf = TagFile()
        magic, size, entry_count = struct.unpack('III', f.read(4 * 3))
        for i in range(entry_count):
            offset = f.tell()
            entry = TagEntry.from_file(f, is_path)
            tf.offsets[offset] = entry
            tf.append(entry)
        assert tf.size == size
        return tf

    @staticmethod
    def read(filename, is_path=None):
        """Return a TagFile given a file name."""
        if is_path is None:
            base = os.path.basename(filename)
            if base.startswith('database_'):
                is_path = (base[9:] == '4.tcd')
            else:
                is_path = False

        with open(filename, 'rb') as f:
            return TagFile.from_file(f, is_path)


class TagEntry:
    def __init__(self, data='<Untagged>', sort=None, is_path=False):
        self.data = data
        self.sort = sort
        self.is_path = is_path
        self.index_entries = []
        self.index = None
        self.offset = None

    def add_index_entry(self, entry):
        self.index_entries.append(entry)

    def __get_data(self):
        return str(self.__data, ENCODING)
    def __set_data(self, data):
        self.__data = data.encode(ENCODING)
    data = property(__get_data, __set_data)

    @property
    def key(self):
        return self.data

    def __get_raw_data(self):
        return (self.__data + b'\x00').ljust(self.length, b'X')
    def __set_raw_data(self, raw_data):
        self.__data = raw_data.partition(b'\x00')[0]
    raw_data = property(__get_raw_data, __set_raw_data)

    def __get_index(self):
         return self.__index if self.__index is not None else 0xffffffff
    def __set_index(self, index):
        self.__index = index
    index = property(__get_index, __set_index)

    def __get_sort(self):
        return self.__sort if self.__sort is not None else self.data
    def __set_sort(self, sort):
        if sort is not None:
            sort = sort.lower()
        self.__sort = sort
    sort = property(__get_sort, __set_sort)

    def sort_value(self):
        return self.offset if self.offset is not None else self.sort

    def matches(self, str):
        return self.data == str

    @property
    def length(self):
        """
        Length must be a multiple of 8 (including the nul-terminator), UNLESS
        this is part of the 'path' database file, in which case Length is simply
        the length of the data plus a nul-terminator
        """
        if self.is_path:
            return len(self.__data) + 1
        else:
            data_len = len(self.__data) + 1
            return ((data_len + 7) // 8) * 8

    @property
    def size(self):
        return self.length + 4 * 2

    def __unicode__(self):
        return self.data

    def __repr__(self):
        return f'TagEntry({self.data!r})'

    def to_file(self, f):
        self.offset = f.tell()
        f.write(struct.pack('II', self.length, self.index))
        f.write(self.raw_data)

    @staticmethod
    def from_file(f, is_path=False):
        """Return a TagFile given a file object."""
        length, index = struct.unpack('II', f.read(4 * 2))
        entry = TagEntry()
        entry.offset = f.tell()
        entry.raw_data = f.read(length)
        entry.index = index
        entry.is_path = is_path
        return entry
