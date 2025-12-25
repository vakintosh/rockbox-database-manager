

import os
import pickle
from itertools import product
try:
    from . import tagging
    from .tagging import titleformat
except ImportError:
    tagging = None
    titleformat = None
    import warnings
    def warn_no_tags():
        warnings.warn("Tagging support is disabled!\n" + \
                      "Please install the mutagen tag library.\n" +\
                      "(Available from http://code.google.com/p/mutagen/)")

from .defs import FORMATTED_TAGS, FILE_TAGS, EMBEDDED_TAGS
from .utils import mtime_to_fat
from .tagfile import TagFile, TagEntry
from .indexfile import IndexFile, IndexEntry

def myprint(*args, **kwargs):
    """Emulates the print() function.
    
    Arguments that cannot be printed are converted using repr()

    This is used as the default callback function for Dabatabase functions
    that ask for a callback.

    """
    converted_args = []
    for a in args:
        try:
            converted_args.append(str(a))
        except UnicodeEncodeError:
            converted_args.append(repr(a))

    try:
        sep = kwargs['sep']
    except KeyError:
        sep = ' '
    try:
        end = kwargs['end']
    except KeyError:
        end = '\n'
    import sys
    sys.stdout.write(sep.join(converted_args) + end)

class Database:

    #---------------------------------------------------------------------------
    # Tag cache
    #---------------------------------------------------------------------------

    # The tag cache is shared between Database instances.  The user can save
    # and later load a given database "session" (all files and folders added
    # to a certain database).  If multiple instances of a Database are created,
    # They share a global tag_cache.  However, if an individual Database saves
    # a session, only files added to that particular database are saved.
    #
    # This file can get HUGE (my music database takes up 45 mb pickled).
    #
    # The format is
    #   { u'/path/to/file/without/drive' :  ( (size, mtime), Tags ) }
    tag_cache = {}

    def load_tags(self, path, callback=None):
        """Update paths and tag_cache from a pickled file."""

        try:
            with open(path, 'rb') as f:
                nItems = pickle.load(f)
                assert isinstance(nItems, int)
                callback(nItems)
                for i in range(nItems):
                    try:
                        path, ((size, mtime), tags) = pickle.load(f)
                    except EOFError:
                        break
                    else:
                        callback(path)
                        self.__add_file(path, size, mtime, tags)
        except OSError:
            pass

    def save_tags(self, path, callback=None):
        """Save tags in self.paths to a pickled file."""
        with open(path, 'wb') as f:
            if callback: callback(len(self.paths))
            pickle.dump(len(self.paths), f, 2)
            for path in sorted(self.paths):
                if callback: callback(path)
                pickle.dump((path, self.tag_cache[path]), f, 2)


    #---------------------------------------------------------------------------
    # Basic class stuff
    #---------------------------------------------------------------------------
    def __init__(self):
        self.clear()
        self.formats = {}

        # Files added to *this* instance
        self.paths = set()
        self.failed = []

        for field in FORMATTED_TAGS:
            self.set_format(field, '%' + field + '%')
        self.set_format('grouping', '%title%')

    def clear(self):
        self.tagfiles = dict( (field, TagFile()) for field in FILE_TAGS )
        self.index = IndexFile(tagfiles = self.tagfiles)
        self.multiple_fields = {}

    def set_format(self, field, format, sortformat=None):
        """Set the format and the sorting format for a field.

        field must be present in FORMATTED_TAGS.  This function will attempt to
        compile the titleformat strings and will raise an exception of they do
        not correctly compile.

        """

        if titleformat is None:
            warn_no_tags()
            return

        assert field in FORMATTED_TAGS
        self.formats[field] = (
            titleformat.compile(format),
            titleformat.compile(sortformat) if sortformat is not None else None
        )

    def __getattr__(self, key):
        """Allow access to self.tagfiles[field] via self.field."""
        return self.tagfiles[key]

    def __getitem__(self, key):
        """Allow access to self.tagfiles[field] via self[field]."""
        if key == 'index':
            return self.index
        else:
            return self.tagfiles[key]

    #---------------------------------------------------------------------------
    # Adding Files to the tag_cache
    #---------------------------------------------------------------------------
    def __add_file(self, path, size=None, mtime=None, tags=None):
        """Add a file to the database.

        Add or update the tag_cache, and add the path to the files set.  If
        mtime is more recent than the cached mtime, the tags will be updated.

        A file will be read only if the tags argument is None.        

        """

        path = os.path.abspath(path)
        lowerpath = path.lower()

        if size is None or mtime is None:
            stat = os.stat(path)
            size, mtime = stat.st_size, int(stat.st_mtime)

        try:
            cached_size, cached_mtime = self.tag_cache[lowerpath][0]
        except KeyError:
            if tags is None:
                tags = tagging.read(path)
            if tags is None:
                self.failed.append(path)
                return
            self.tag_cache[lowerpath] = ((size, mtime), tags)
        else:
            if mtime > cached_mtime:
                self.tag_cache[lowerpath] = ((size, mtime), tags)
        self.paths.add(lowerpath)

    def add_file(self, file, callback=myprint):
        """Add a file and rewrite the tag_cache."""
        if tagging is None:
            warn_no_tags()
            return

        path = str(file)
        if callback: callback(path)
        self.__add_file(file)

    def add_files(self, files, callback=myprint):
        """Add a list of files.  Rewrite the tag_cache at the end."""
        if tagging is None:
            warn_no_tags()
            return

        for file in files:
            file = str(file)
            if callback: callback(file)
            self.__add_file(file)

    def add_dir(self, path, recursive=True,
                dircallback=myprint, filecallback=None, estimatecallback=None):
        """Add a directory (recursively by default)."""

        if tagging is None:
            warn_no_tags()
            return

        def blank(*args, **kwargs):
            pass
        if not dircallback: dircallback = blank
        if not filecallback: filecallback = blank
        if estimatecallback:
            finishedFiles = 0
            totalTopLevelDirs = 0
            finishedTopLevelDirs = 0
            currentTopLevelDir = None

            # For exponential moving average (EMA)
            lastEstimate = None
            # between 0 and 1; lower value = greater smoothing
            smoothingFactor = 0.03

        original_root = str(path)
        for root, dirs, files in os.walk(original_root):
            dircallback(root)

            if estimatecallback:
                # Record the total number of top level directories (one
                # directory below the original path)
                if root == original_root:
                    totalTopLevelDirs = len(dirs)

                # Is this is one of the top level directories?
                if os.path.dirname(root) == original_root:
                    # Increment after we have finished one top level dir
                    # and have moved to the next
                    finishedTopLevelDirs += 1
                    currentTopLevelDir = root

                finishedFiles += len(files)

                estimatedFiles = 0
                if finishedTopLevelDirs > 1:
                    estimatedFiles = (
                        float(finishedFiles) / finishedTopLevelDirs
                        * totalTopLevelDirs
                    )
                else:
                    estimatedFiles = float(finishedFiles) * totalTopLevelDirs

                if estimatedFiles != 0:
                    if lastEstimate is not None:
                        estimatedFiles = (
                            smoothingFactor * estimatedFiles
                            + (1 - smoothingFactor) * lastEstimate
                        )
                    estimatecallback(int(estimatedFiles))
                    lastEstimate = estimatedFiles

            for file in files:
                path = os.path.join(root, file)
                filecallback(path)
                self.__add_file(path)

            if not recursive:
                break

    #---------------------------------------------------------------------------
    # Database generation
    #---------------------------------------------------------------------------
    def generate_database(self, callback=myprint):
        """Generate the database from on files or dirs that have been added.

        This creates an IndexFile and TagFiles for each formatted field.
        Use write() to write the database to files.

        """

        self.clear()

        # Make the format strings
        formats = {}
        self.multiple_fields = {}
        for field, (format, sort) in self.formats.items():
            if format.is_multiple:
                self.multiple_fields[field] = TagEntry('<BLANK>')
            format = titleformat.compile(
                f"$if2({format.to_string()},'<Untagged>')"
            )
            if sort is not None:
                sort = titleformat.compile(
                    f"$if2({sort.to_string()},{format.to_string()})"
                )
            formats[field] = (format, sort)

        # Standard formats
        formats['date']        = titleformat.compile('$if2(%date%,0)')
        formats['discnumber']  = titleformat.compile('$if2(%discnumber%,0)')
        formats['tracknumber'] = titleformat.compile('$if2(%tracknumber%,0)')
        formats['bitrate']     = titleformat.compile('$if2(%bitrate%,0)')

        for path in sorted(self.paths):
            (size, mtime), tags = self.tag_cache[path]
            # Remove drive letter and convert to Unix-style path for Rockbox
            # (Rockbox expects forward slashes on all platforms)
            path = os.path.splitdrive(tags['path'][0])[1]
            path = path.replace(os.sep, '/')

            if callback: callback(path)

            entry = IndexEntry()

            entry.path = TagEntry(path, is_path = True)
            entry.path.index = self.index.count
            self.path.append(entry.path)

            try:
                entry.title = TagEntry(tags['title'][0])
            except KeyError:
                entry.title = TagEntry('<Untagged>')
            entry.title.index = self.index.count
            self.title.append(entry.title)

            entry.mtime = mtime_to_fat(mtime)
            # Length is milliseconds
            entry.length = int(tags['length'][0] * 1000)

            for field in EMBEDDED_TAGS:
                try:
                    formatted_value = str(formats[field].format(tags))
                    entry[field] = int(formatted_value)
                except (KeyError, ValueError):
                    # KeyError: field not found in formats
                    # ValueError: cannot convert formatted string to int
                    pass

            multiple_tags = {}
            for field, blank_tag in self.multiple_fields.items():
                multiple_tags[field] = [blank_tag]

            for field in FILE_TAGS:
                try:
                    fmt, sort = formats[field]
                except KeyError:
                    continue

                if field not in multiple_tags:

                    value = fmt.format(tags)
                    try:
                        tagentry = self[field][value]
                    except KeyError:
                        tagentry = TagEntry(value)
                        if sort is not None:
                            tagentry.sort = sort.format(tags)
                        self[field].append(tagentry)

                    entry[field] = tagentry

                else:
                    # Make data / sort order lists
                    if sort is not None:
                        sort = sort.format(tags)
                        if not isinstance(sort, (tuple, list)):
                            sort = [sort]
                    else:
                        sort = [None]
                    data = fmt.format(tags)
                    if not isinstance(data, (tuple, list)):
                        data = [data]

                    for v, s in zip(data, sort):
                        multiple_tags[field].append(TagEntry(v,s))

            # Make all combinations of the IndexEntry
            combinations = []
            for field, tagentries in multiple_tags.items():
                combinations.append( [ (field, tagentry) for tagentry in tagentries ] )

            for fields in product(*combinations):
                index_entry = entry.copy()
                for field, value in fields:
                    # Make sure the TagEntry is present in the TagFile
                    try:
                        tagentry = self[field][value.key]
                    except KeyError:
                        tagentry = value
                        self[field].append(tagentry)
                    index_entry[field] = tagentry
                self.index.append(index_entry)

        for field in FILE_TAGS:
            self[field].sort()

    #---------------------------------------------------------------------------
    # Database read / write
    #---------------------------------------------------------------------------
    def write(self, out_dir='', callback=myprint):
        """Write the database to a directory.

        Files that will be written:
            database_0.tcd
            database_1.tcd
            database_2.tcd
            database_3.tcd
            database_4.tcd
            database_5.tcd
            database_6.tcd
            database_7.tcd
            database_8.tcd
            database_idx.tcd

        """
        # Write the tag files
        for i, field in enumerate(FILE_TAGS):
            filename = os.path.join(out_dir, f'database_{i}.tcd')
            callback(f'Writing {filename} . . .', end='')
            self[field].write(filename)
            callback('done')

        # Write the index file
        filename = os.path.join(out_dir, 'database_idx.tcd')
        callback(f'Writing {filename} . . .', end='')
        self.index.write(filename)
        callback('done')

    @staticmethod
    def read(in_dir='', callback=myprint):
        """Read the database from a directory and return a Database object.

        Files that will be read:
            database_0.tcd
            database_1.tcd
            database_2.tcd
            database_3.tcd
            database_4.tcd
            database_5.tcd
            database_6.tcd
            database_7.tcd
            database_8.tcd
            database_idx.tcd

        """
        db = Database()
        # Read the tag files
        for i, field in enumerate(FILE_TAGS):
            filename = os.path.join(in_dir, f'database_{i}.tcd')
            callback(f'Reading {filename} . . .', end='')
            db.tagfiles[field] = TagFile.read(filename)
            callback('done')

        # Read the index file
        filename = os.path.join(in_dir, 'database_idx.tcd')
        callback(f'Reading {filename} . . .', end='')
        db.index = IndexFile.read(filename, db.tagfiles)
        callback('done')

        return db
