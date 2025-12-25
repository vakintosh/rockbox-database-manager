import struct

from utils import fat_to_mtime
from defs import MAGIC, TAGS, FILE_TAGS, EMBEDDED_TAGS
from tagfile import TagEntry

class IndexFile:
    def __init__(self, entries=None, tagfiles=None):
        self.magic = MAGIC
        self.serial = 0
        self.commitid = 0
        self.dirty = 0
        self.entries = entries if entries is not None else []

        # The index must have references to the tagfiles so that it can
        # calculate the size part of the header.
        self.tagfiles = tagfiles if tagfiles is not None else {}

    def __getitem__(self, key):
        return self.entries.__getitem__(key)

    def append(self, entry):
        self.entries.append(entry)

    @property
    def count(self):
        return len(self.entries)

    @property
    def size(self):
        """The size in an IndexFile represents the amount of memory that needs
        to be allocated to hold the tagcache.  It is calculated as the sum of
        the size of each TagFile (except the path TagFile), plus the size of
        the IndexFile (data size + header size).

        """
        return sum(
            f.size for k, f in self.tagfiles.items() if k is not 'path'
        ) + self.header_size + self.data_size

    @property
    def data_size(self):
        return IndexEntry.size * self.count

    header_size = 6 * 4

    def sort(self):
        self.entries.sort(key = lambda entry: entry.sort)

    def to_file(self, f):
        self.commitid += 1
        self.dirty = 0
        f.write(struct.pack('IIIIII', self.magic, self.size, self.count,
                                      self.serial, self.commitid, self.dirty))
        for entry in self.entries:
            entry.to_file(f)

    def write(self, filename):
        with open(filename, 'wb') as f:
            self.to_file(f)


    @staticmethod
    def from_file(f, tagfiles):
        index = IndexFile(tagfiles = tagfiles)
        index.magic, size, count, index.serial, index.commitid, index.dirty = \
            struct.unpack('IIIIII', f.read(4 * 6))
        for i in range(count):
            index.append(IndexEntry.from_file(f, tagfiles))
        assert size == index.size
        return index

    @staticmethod
    def read(filename, tagfiles):
        with open(filename, 'rb') as f:
            return IndexFile.from_file(f, tagfiles)



class IndexEntry(dict):
    def __init__(self):
        for field in FILE_TAGS:
            self[field] = None
        for field in EMBEDDED_TAGS:
            self[field] = 0

    def __getattr__(self, name):
        return self[name]
    def __setattr__(self, name, value):
        self[name] = value

    size = 4 * len(TAGS)

    def copy(self):
        other = IndexEntry()
        other.update(self)
        return other

    def to_file(self, f):
        for field in FILE_TAGS:
            tagentry = self[field]
            assert isinstance(tagentry, TagEntry) and tagentry.offset is not None
            f.write(struct.pack('I', tagentry.offset))

        for field in EMBEDDED_TAGS:
            f.write(struct.pack('I', self[field]))

    @staticmethod
    def from_file(f, tagfiles):
        """Read the index entry from a file.
         
        If tagfiles is a dictionary of { field: TagFile } pairs, which will be
        used to extract the actual TagEntry for each offset in the file.

        """

        index_entry = IndexEntry()
        for field in FILE_TAGS:
            offset = struct.unpack('I', f.read(4))[0]
            index_entry[field] = tagfiles[field].offsets[offset]

        for field in EMBEDDED_TAGS:
            index_entry[field] = struct.unpack('I', f.read(4))[0]
        index_entry.mtime = fat_to_mtime(index_entry.mtime)

        return index_entry
