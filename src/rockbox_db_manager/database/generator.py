"""Database generation logic for Rockbox Database Manager.

This module handles generating the Rockbox database structure from cached
music file tags with support for parallel processing.
"""

import os
import gc
from itertools import product
from typing import Optional, Callable, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

try:
    from ..tagging import titleformat
except ImportError:
    titleformat = None

from ..defs import FILE_TAGS, EMBEDDED_TAGS
from ..utils import mtime_to_fat
from ..tagfile import TagEntry
from ..indexfile import IndexEntry
from .cache import TagCache


def myprint(*args, **kwargs):
    """Simple print wrapper for generator callback functions."""
    sep = kwargs.get('sep', ' ')
    end = kwargs.get('end', '\n')
    
    import sys
    sys.stdout.write(sep.join(str(a) for a in args) + end)

class DatabaseGenerator:
    """Handles database generation from cached tags with parallel processing."""
    
    def __init__(self, max_workers: int = 8):
        """Initialize the database generator.
        
        Args:
            max_workers: Maximum number of parallel workers
        """
        self.max_workers = max_workers
        self._lock = Lock()
    
    def generate(self, paths: set, formats: Dict[str, Tuple], tagfiles: dict,
                 index, use_parallel: bool = True,
                 callback: Optional[Callable] = myprint) -> Dict[str, TagEntry]:
        """Generate the database from cached tags.
        
        Args:
            paths: Set of file paths to process
            formats: Dictionary of format strings for each field
            tagfiles: Dictionary of TagFile objects
            index: IndexFile object to populate
            use_parallel: Whether to use parallel processing
            callback: Progress callback function
            
        Returns:
            Dictionary of multiple_fields with blank TagEntry values
        """
        if titleformat is None:
            return {}
        
        # Pre-compile ALL format strings once for maximum efficiency
        compiled_formats = {}
        multiple_fields = {}
        
        for field, (format, sort) in formats.items():
            if format.is_multiple:
                multiple_fields[field] = TagEntry('<BLANK>')
            format = titleformat.compile(
                f"$if2({format.to_string()},'<Untagged>')"
            )
            if sort is not None:
                sort = titleformat.compile(
                    f"$if2({sort.to_string()},{format.to_string()})"
                )
            compiled_formats[field] = (format, sort)

        # Standard formats (compiled once and reused for all files)
        compiled_formats['date']        = titleformat.compile('$if2(%date%,0)')
        compiled_formats['discnumber']  = titleformat.compile('$if2(%discnumber%,0)')
        compiled_formats['tracknumber'] = titleformat.compile('$if2(%tracknumber%,0)')
        compiled_formats['bitrate']     = titleformat.compile('$if2(%bitrate%,0)')

        # Batch progress updates to reduce callback overhead
        batch_size = 100  # Update every 100 paths
        total_paths = len(paths)
        sorted_paths = sorted(paths)
        
        # Choose processing strategy based on dataset size and parallel flag
        if use_parallel and total_paths > 1000:
            self._generate_parallel(sorted_paths, compiled_formats, tagfiles, 
                                   index, multiple_fields, callback, batch_size)
        else:
            self._generate_sequential(sorted_paths, compiled_formats, tagfiles,
                                     index, multiple_fields, callback, batch_size)
        
        # Final progress update
        if callback:
            callback(total_paths, total_paths)
        
        for field in FILE_TAGS:
            tagfiles[field].sort()
        
        # Clean up cache after generation to free memory
        TagCache.cleanup(keep_paths=paths)

        # Force garbage collection to free memory immediately
        gc.collect()
        
        return multiple_fields
    
    def _generate_sequential(self, sorted_paths, formats, tagfiles, 
                            index, multiple_fields, callback, batch_size):
        """Sequential database generation (optimized logic)."""
        total_paths = len(sorted_paths)
        cache = TagCache.get_cache()
        
        for i, path in enumerate(sorted_paths, 1):
            (size, mtime), tags = cache[path]


            # Remove drive letter and convert to Unix-style path for Rockbox
            clean_path = os.path.splitdrive(path)[1]
            clean_path = clean_path.replace(os.sep, '/')

            if callback and i % batch_size == 0:
                callback(i, total_paths)

            self._process_entry({'path': clean_path, 'mtime': mtime, 'tags': tags}, 
                               formats, tagfiles, index, multiple_fields)
    
    def _generate_parallel(self, sorted_paths, formats, tagfiles,
                          index, multiple_fields, callback, batch_size):
        """Parallel database generation using thread pool.
        
        Note: Due to titleformat objects and GIL, we use threading to process
        batches in parallel while maintaining thread-safe access to shared data.
        """
        total_paths = len(sorted_paths)
        processed = 0
        cache = TagCache.get_cache()
        
        def process_batch(paths_batch):
            """Process a batch of paths and return intermediate results."""
            batch_results = []
            for path in paths_batch:
                try:
                    (size, mtime), tags = cache[path]
                except KeyError:
                    # File not in cache - skip it (should not happen if cache is up to date)
                    # This occurs when scanning a folder that wasn't included in the tag cache
                    import logging
                    logging.warning(f"File not in cache, skipping: {path}")
                    continue

                try:
                    clean_path = os.path.splitdrive(path)[1]
                    clean_path = clean_path.replace(os.sep, '/')
                    
                    # Create entry data
                    entry_data = {
                        'path': clean_path,
                        'mtime': mtime,
                        'tags': tags
                    }
                    batch_results.append(entry_data)
                except Exception as e:
                    # Skip problematic entries but log the error
                    import logging
                    logging.debug(f"Skipped entry {path} due to processing error: {e}")
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
                        self._process_entry(entry_data, formats, tagfiles, 
                                          index, multiple_fields)
                        processed += 1
                
                if callback:
                    callback(processed, total_paths)
    
    def _process_entry(self, entry_data: dict, formats: dict, tagfiles: dict,
                      index, multiple_fields: dict) -> None:
        """Process a single entry for database generation.
        
        Args:
            entry_data: Dictionary with 'path', 'mtime', and 'tags'
            formats: Compiled format strings
            tagfiles: TagFile objects
            index: IndexFile object
            multiple_fields: Dictionary of fields with multiple values
        """
        path = entry_data['path']
        mtime = entry_data['mtime']
        tags = entry_data['tags']
        
        entry = IndexEntry()

        entry.path = TagEntry(path, is_path=True)
        entry.path.index = index.count
        tagfiles['path'].append(entry.path)

        try:
            entry.title = TagEntry(tags['title'][0])
        except KeyError:
            entry.title = TagEntry('<Untagged>')
        entry.title.index = index.count
        tagfiles['title'].append(entry.title)

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
        for field, blank_tag in multiple_fields.items():
            multiple_tags[field] = [blank_tag]

        for field in FILE_TAGS:
            try:
                fmt, sort = formats[field]
            except KeyError:
                continue

            if field not in multiple_tags:
                value = fmt.format(tags)
                try:
                    tagentry = tagfiles[field][value]
                except KeyError:
                    tagentry = TagEntry(value)
                    if sort is not None:
                        tagentry.sort = sort.format(tags)
                    tagfiles[field].append(tagentry)
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
                    multiple_tags[field].append(TagEntry(v, s))

        # Make all combinations of the IndexEntry
        combinations = []
        for field, tagentries in multiple_tags.items():
            combinations.append([(field, tagentry) for tagentry in tagentries])

        for fields in product(*combinations):
            index_entry = entry.copy()
            for field, value in fields:
                # Make sure the TagEntry is present in the TagFile
                try:
                    tagentry = tagfiles[field][value.key]
                except KeyError:
                    tagentry = value
                    tagfiles[field].append(tagentry)
                index_entry[field] = tagentry
            index.append(index_entry)
