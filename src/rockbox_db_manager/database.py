import os
import pickle
import gc
import multiprocessing
from itertools import product
from typing import Optional, Callable, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
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
    MAX_CACHE_SIZE = 10000  # Maximum number of entries to keep in cache

    def load_tags(self, path, callback=None):
        """Update paths and tag_cache from a pickled file.
        
        Loads tags efficiently with error handling for corrupted files.
        """

        try:
            with open(path, 'rb') as f:
                nItems = pickle.load(f)
                assert isinstance(nItems, int)
                if callback:
                    callback(nItems)
                for i in range(nItems):
                    try:
                        path, ((size, mtime), tags) = pickle.load(f)
                    except EOFError:
                        break
                    except (pickle.UnpicklingError, ValueError) as e:
                        # Skip corrupted entries
                        if callback:
                            callback(f"Warning: Skipped corrupted entry {i+1}/{nItems}: {e}")
                        continue
                    else:
                        if callback:
                            callback(path)
                        self.__add_file(path, size, mtime, tags)
        except (OSError, IOError):
            pass

    def save_tags(self, path: str, callback: Optional[Callable] = None) -> None:
        """Save tags in self.paths to a pickled file.
        
        Args:
            path: Path to save the pickled tags file
            callback: Optional callback function for progress updates
        """
        with open(path, 'wb') as f:
            if callback:
                callback(len(self.paths))
            pickle.dump(len(self.paths), f, 2)
            for path in sorted(self.paths):
                if callback:
                    callback(path)
                pickle.dump((path, self.tag_cache[path]), f, 2)

    @classmethod
    def cleanup_cache(cls, keep_paths=None):
        """Remove unused entries from the shared tag_cache to free memory.
        
        Args:
            keep_paths: Optional set of paths to keep. If None, keeps all paths
                       from all Database instances currently in use.
        """
        if keep_paths is not None:
            # Remove entries not in keep_paths
            keys_to_remove = [k for k in cls.tag_cache if k not in keep_paths]
            for key in keys_to_remove:
                del cls.tag_cache[key]
            
            # Force garbage collection to free memory immediately
            if keys_to_remove:
                gc.collect()
    
    @classmethod
    def _trim_cache(cls):
        """Trim cache to 80% of MAX_CACHE_SIZE by removing oldest 20% of entries.
        
        This is called when cache exceeds MAX_CACHE_SIZE to prevent unbounded growth.
        """
        if len(cls.tag_cache) > cls.MAX_CACHE_SIZE:
            remove_count = len(cls.tag_cache) // 5  # Remove 20%
            keys_to_remove = list(cls.tag_cache.keys())[:remove_count]
            for key in keys_to_remove:
                del cls.tag_cache[key]
            gc.collect()


    #---------------------------------------------------------------------------
    # Basic class stuff
    #---------------------------------------------------------------------------
    def __init__(self):
        self.clear()
        self.formats = {}

        # Files added to *this* instance
        self.paths = set()
        self.failed = []
        
        # Parallelization configuration
        self.max_workers = min(multiprocessing.cpu_count(), 8)  # Cap at 8 workers
        self.use_parallel = True  # Can be toggled via parameters
        self._lock = Lock()  # Thread-safe operations

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
        
        # Check cache size and trim if needed to prevent unbounded growth
        if len(self.tag_cache) > self.MAX_CACHE_SIZE:
            self._trim_cache()

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

    def add_file(self, file: str, callback: Callable = myprint) -> None:
        """Add a file and rewrite the tag_cache.
        
        Args:
            file: Path to the file to add
            callback: Callback function for progress updates
        """
        if tagging is None:
            warn_no_tags()
            return

        path = str(file)
        if callback:
            callback(path)
        self.__add_file(file)

    def _read_tags_batch(self, file_paths: List[str]) -> List[tuple]:
        """Read tags from multiple files in parallel.
        
        Returns list of (path, size, mtime, tags) tuples.
        Thread-safe implementation for I/O-bound tag reading.
        """
        if tagging is None:
            return []
        
        results = []
        
        def read_single_file(path):
            try:
                stat = os.stat(path)
                size, mtime = stat.st_size, int(stat.st_mtime)
                tags = tagging.read(path)
                if tags is None:
                    return (path, None, None, None)
                return (path, size, mtime, tags)
            except Exception:
                return (path, None, None, None)
        
        # Use ThreadPoolExecutor for I/O-bound tag reading
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(read_single_file, path): path 
                      for path in file_paths}
            
            for future in as_completed(futures):
                result = future.result()
                if result[1] is not None:  # Valid result
                    results.append(result)
        
        return results

    def add_files(self, files: List[str], callback: Callable = myprint) -> None:
        """Add a list of files.  Rewrite the tag_cache at the end.
        
        Args:
            files: List of file paths to add
            callback: Callback function for progress updates
        """
        if tagging is None:
            warn_no_tags()
            return

        # Batch progress updates to reduce callback overhead
        batch_size = 100  # Update every 100 files
        for i, file in enumerate(files, 1):
            file = str(file)
            if callback and i % batch_size == 0:
                callback(f"Processing files... {i}/{len(files)}")
            self.__add_file(file)
        
        # Final update
        if callback and len(files) % batch_size != 0:
            callback(f"Processing files... {len(files)}/{len(files)}")

    def add_dir(self, path: str, recursive: bool = True,
                dircallback: Optional[Callable] = myprint, 
                filecallback: Optional[Callable] = None, 
                estimatecallback: Optional[Callable] = None,
                parallel: Optional[bool] = None) -> None:
        """Add a directory (recursively by default) with optional parallel processing.
        
        Args:
            path: Directory path to scan
            recursive: Whether to scan recursively (default: True)
            dircallback: Callback function called for each directory
            filecallback: Callback function called for each file
            estimatecallback: Callback function for progress estimation
            parallel: Override parallel processing (default: uses self.use_parallel)
        """

        if tagging is None:
            warn_no_tags()
            return
        
        use_parallel = parallel if parallel is not None else self.use_parallel

        def blank(*args: Any, **kwargs: Any) -> None:
            pass
        
        if not dircallback:
            dircallback = blank
        if not filecallback:
            filecallback = blank

        original_root = str(path)
        batch_size = 100  # Process files in batches
        
        # Collect all files first for parallel processing
        all_files = []
        for root, dirs, files in os.walk(original_root):
            dircallback(root)
            for file in files:
                file_path = os.path.join(root, file)
                all_files.append(file_path)
            if not recursive:
                break
        
        total_files = len(all_files)
        
        if estimatecallback:
            estimatecallback(total_files)
        
        # Process files
        if use_parallel and total_files > batch_size:
            # Parallel processing for large datasets
            file_count = 0
            for i in range(0, total_files, batch_size):
                batch = all_files[i:i + batch_size]
                results = self._read_tags_batch(batch)
                
                # Add results to cache with thread-safe operations
                with self._lock:
                    for path, size, mtime, tags in results:
                        if tags is not None:
                            self.__add_file(path, size, mtime, tags)
                            file_count += 1
                        else:
                            self.failed.append(path)
                
                processed = min(i + batch_size, total_files)
                if filecallback:
                    filecallback(f"Processing files... {processed}/{total_files}")
        else:
            # Sequential processing for small file counts
            file_count = 0
            for file_path in all_files:
                self.__add_file(file_path)
                file_count += 1
                
                if filecallback and file_count % batch_size == 0:
                    filecallback(f"Processing files... {file_count}/{total_files}")

    #---------------------------------------------------------------------------
    # Database generation
    #---------------------------------------------------------------------------
    def generate_database(self, callback=myprint, parallel: Optional[bool] = None):
        """Generate the database from files or dirs that have been added.

        This creates an IndexFile and TagFiles for each formatted field.
        Use write() to write the database to files.
        
        Args:
            callback: Progress callback function
            parallel: Override parallel processing (default: uses self.use_parallel)

        """
        use_parallel = parallel if parallel is not None else self.use_parallel

        self.clear()

        # Pre-compile ALL format strings once for maximum efficiency
        # This prevents repeated compilation for every file processed
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

        # Standard formats (compiled once and reused for all files)
        formats['date']        = titleformat.compile('$if2(%date%,0)')
        formats['discnumber']  = titleformat.compile('$if2(%discnumber%,0)')
        formats['tracknumber'] = titleformat.compile('$if2(%tracknumber%,0)')
        formats['bitrate']     = titleformat.compile('$if2(%bitrate%,0)')

        # Batch progress updates to reduce callback overhead
        batch_size = 100  # Update every 100 paths
        total_paths = len(self.paths)
        sorted_paths = sorted(self.paths)
        
        # Choose processing strategy based on dataset size and parallel flag
        if use_parallel and total_paths > 1000:
            self._generate_database_parallel(sorted_paths, formats, callback, batch_size)
        else:
            self._generate_database_sequential(sorted_paths, formats, callback, batch_size)
        
        # Final progress update
        if callback and total_paths % batch_size != 0:
            callback(f"Generating database... {total_paths}/{total_paths}")
        
        for field in FILE_TAGS:
            self[field].sort()
        
        # Clean up cache after generation to free memory
        # Keep only paths still referenced by this database instance
        self.cleanup_cache(keep_paths=self.paths)

        # Force garbage collection to free memory immediately
        gc.collect()
    
    def _generate_database_sequential(self, sorted_paths, formats, callback, batch_size):
        """Sequential database generation (original optimized logic)."""
        total_paths = len(sorted_paths)
        
        for i, path in enumerate(sorted_paths, 1):
            (size, mtime), tags = self.tag_cache[path]
            # Remove drive letter and convert to Unix-style path for Rockbox
            # (Rockbox expects forward slashes on all platforms)
            path = os.path.splitdrive(tags['path'][0])[1]
            path = path.replace(os.sep, '/')

            if callback and i % batch_size == 0:
                callback(f"Generating database... {i}/{total_paths}")

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
                    # Handle TagTrue/TagFalse which may not convert properly
                    # Strip any whitespace that might interfere
                    formatted_value = formatted_value.strip()
                    # Try to convert to int, default to 0 if it fails
                    if formatted_value and formatted_value not in ('True', 'False', '<Untagged>'):
                        entry[field] = int(formatted_value)
                    else:
                        entry[field] = 0
                except (KeyError, ValueError, AttributeError):
                    # KeyError: field not found in formats
                    # ValueError: cannot convert formatted string to int
                    # AttributeError: formatted value has unexpected type
                    entry[field] = 0

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
    
    def _generate_database_parallel(self, sorted_paths, formats, callback, batch_size):
        """Parallel database generation using thread pool for I/O operations.
        
        Note: Due to titleformat objects and GIL, we use threading to process
        batches in parallel while maintaining thread-safe access to shared data.
        """
        total_paths = len(sorted_paths)
        processed = 0
        
        def process_batch(paths_batch):
            """Process a batch of paths and return intermediate results."""
            batch_results = []
            for path in paths_batch:
                try:
                    (size, mtime), tags = self.tag_cache[path]
                    clean_path = os.path.splitdrive(tags['path'][0])[1]
                    clean_path = clean_path.replace(os.sep, '/')
                    
                    # Create entry data (formats are shared, protected by GIL)
                    entry_data = {
                        'path': clean_path,
                        'size': size,
                        'mtime': mtime,
                        'tags': tags
                    }
                    batch_results.append(entry_data)
                except Exception:
                    # Skip problematic entries
                    pass
            return batch_results
        
        # Split into batches for parallel processing
        batches = [sorted_paths[i:i + batch_size] 
                  for i in range(0, total_paths, batch_size)]
        
        # Process batches with thread pool
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(process_batch, batch): batch 
                      for batch in batches}
            
            for future in as_completed(futures):
                batch_results = future.result()
                
                # Process results sequentially to maintain data structure integrity
                with self._lock:
                    for entry_data in batch_results:
                        self._process_entry(entry_data, formats)
                        processed += 1
                
                if callback:
                    callback(f"Generating database... {processed}/{total_paths}")
    
    def _process_entry(self, entry_data, formats):
        """Process a single entry for database generation."""
        path = entry_data['path']
        mtime = entry_data['mtime']
        tags = entry_data['tags']
        
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
                formatted_value = formatted_value.strip()
                if formatted_value and formatted_value not in ('True', 'False', '<Untagged>'):
                    entry[field] = int(formatted_value)
                else:
                    entry[field] = 0
            except (KeyError, ValueError, AttributeError):
                entry[field] = 0

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
                try:
                    tagentry = self[field][value.key]
                except KeyError:
                    tagentry = value
                    self[field].append(tagentry)
                index_entry[field] = tagentry
            self.index.append(index_entry)

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
        # Write the tag files with optimized buffering
        BUFFER_SIZE = 8192  # 8KB buffer for efficient I/O
        for i, field in enumerate(FILE_TAGS):
            filename = os.path.join(out_dir, f'database_{i}.tcd')
            callback(f'Writing {filename} . . .', end='')
            self[field].write(filename, buffer_size=BUFFER_SIZE)
            callback('done')

        # Write the index file with optimized buffering
        filename = os.path.join(out_dir, 'database_idx.tcd')
        callback(f'Writing {filename} . . .', end='')
        self.index.write(filename, buffer_size=BUFFER_SIZE)
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
