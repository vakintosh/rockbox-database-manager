"""Tag cache management for the Rockbox Database Manager.

This module handles efficient caching of music file tags to speed up
database generation by avoiding repeated file reads.
"""

import pickle
import gzip
import gc
from collections import OrderedDict
from typing import Optional, Callable, Any


class SimpleTag(dict):
    """Lightweight dict-like wrapper for tag data that supports item access and get_string method.
    
    This class is used to restore minimal tag dictionaries to a format compatible with
    database generation code, which expects tag objects with item access and get_string() method.
    """
    
    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            # Match mutagen behavior - raise KeyError for missing fields
            raise KeyError(key)
    
    def get_string(self, key):
        """Get field value as a string list for titleformat compatibility."""
        try:
            value = self[key]
            # Convert value to list of strings
            if isinstance(value, (list, tuple)):
                return [str(v) for v in value]
            elif value is None:
                return []
            else:
                return [str(value)]
        except KeyError:
            raise KeyError(key)


class TagCache:
    """Manages a shared cache of music file tags with LRU eviction.
    
    The tag cache is shared between Database instances and uses an
    OrderedDict for efficient LRU (Least Recently Used) cache eviction.
    Supports compressed pickle storage with minimal memory footprint.
    """
    
    # Shared cache across all instances
    _cache = OrderedDict()
    MAX_CACHE_SIZE = 50000  # Maximum number of entries to keep in cache
    _auto_trim = True  # Control automatic trimming during adds
    
    @classmethod
    def get_cache(cls):
        """Get the shared cache instance."""
        return cls._cache
    
    @classmethod
    def clear(cls):
        """Clear all entries from the cache."""
        cls._cache.clear()
        gc.collect()  # Free memory
    
    @classmethod
    def set_auto_trim(cls, enabled: bool) -> None:
        """Enable or disable automatic cache trimming.
        
        Args:
            enabled: True to enable auto-trim, False to disable
        """
        cls._auto_trim = enabled
    
    @staticmethod
    def extract_essential_tags(tag_obj: Any) -> Optional[dict]:
        """Extract only essential fields from a Tag object to minimize cache size.
        
        Returns a lightweight dictionary instead of the full mutagen object.
        This reduces pickle size dramatically (from ~117KB to ~1KB per file).
        
        Args:
            tag_obj: Tag object (typically from mutagen)
            
        Returns:
            Dictionary with essential tag fields, or None if tag_obj is None
        """
        if tag_obj is None:
            return None
        
        # Fields needed for rockbox database generation
        essential_fields = [
            'artist', 'album', 'genre', 'title', 'composer', 
            'comment', 'album artist', 'grouping', 'date',
            'discnumber', 'tracknumber', 'bitrate', 'length', 'path'
        ]
        
        result = {}
        for field in essential_fields:
            try:
                result[field] = tag_obj[field]
            except (KeyError, AttributeError):
                pass
        
        return result
    
    @staticmethod
    def restore_tag_dict(tag_dict: Optional[dict]) -> Optional[dict]:
        """Convert minimal tag dictionary back to a format compatible with database generation.
        
        The database generation code expects tag objects, but we can provide
        a lightweight dict-like wrapper instead of the full mutagen object.
        
        Args:
            tag_dict: Minimal tag dictionary
            
        Returns:
            Simple dict that supports item access, or None if tag_dict is None
        """
        if tag_dict is None:
            return None
        
        # Return a SimpleTag instance that supports item access and get_string method
        return SimpleTag(tag_dict)
    
    @classmethod
    def load(cls, path: str, paths_set: set, callback: Optional[Callable] = None) -> None:
        """Load tags from a pickled file into the cache.
        
        Loads tags efficiently with error handling for corrupted files.
        Supports both compressed (.gz) and uncompressed formats.
        Restores minimal tag dictionaries to memory-efficient format.
        
        Args:
            path: Path to the pickle file to load
            paths_set: Set to update with loaded file paths
            callback: Optional callback for progress updates
        """
        try:
            # Detect if file is gzip compressed
            opener = gzip.open if path.endswith('.gz') else open
            open_mode = 'rb'
            
            with opener(path, open_mode) as f:
                nItems = pickle.load(f)
                assert isinstance(nItems, int)
                if callback:
                    callback(nItems)
                
                # Bulk load optimization: bypass individual checks and load directly
                for i in range(nItems):
                    try:
                        file_path, ((size, mtime), tags) = pickle.load(f)
                    except EOFError:
                        break
                    except (pickle.UnpicklingError, ValueError) as e:
                        # Skip corrupted entries
                        if callback:
                            callback(f"Warning: Skipped corrupted entry {i+1}/{nItems}: {e}")
                        continue
                    else:
                        if callback:
                            callback(file_path)
                        
                        # Restore tags to usable format and cache
                        lowerpath = file_path.lower()
                        restored_tags = cls.restore_tag_dict(tags) if isinstance(tags, dict) else tags
                        cls._cache[lowerpath] = ((size, mtime), restored_tags)
                        paths_set.add(lowerpath)
                
                # Trim cache once at the end if needed, not on every file
                if len(cls._cache) > cls.MAX_CACHE_SIZE:
                    cls.trim()
        except (OSError, IOError):
            pass
    
    @classmethod
    def save(cls, path: str, paths_set: set, callback: Optional[Callable] = None) -> tuple:
        """Save cached tags to a compressed pickled file.
        
        Args:
            path: Path to save the pickled tags file (will add .gz if not present)
            paths_set: Set of paths to save
            callback: Optional callback function for progress updates
            
        Returns:
            Tuple of (actual_path_used, number_of_entries_saved)
            
        Uses gzip compression and pickle protocol 5 for efficient storage.
        Stores only essential tag fields to minimize file size.
        """
        # Add .gz extension if not present
        if not path.endswith('.gz'):
            path = path + '.gz'
            
        with gzip.open(path, 'wb', compresslevel=6) as f:
            # Only save paths that exist in tag_cache (some may have been trimmed)
            valid_paths = [p for p in paths_set if p in cls._cache]
            missing_count = len(paths_set) - len(valid_paths)
            if missing_count > 0:
                import logging
                logging.warning(
                    f"Cache trimmed during scan: {missing_count} files not in cache. "
                    f"Consider increasing MAX_CACHE_SIZE (current: {cls.MAX_CACHE_SIZE}) "
                    f"or disabling auto-trim during scan."
                )
            if callback:
                callback(len(valid_paths))
            # Use pickle protocol 5 (Python 3.8+) for better efficiency
            pickle.dump(len(valid_paths), f, pickle.HIGHEST_PROTOCOL)
            for path_entry in sorted(valid_paths):
                if callback:
                    callback(path_entry)
                # Extract essential tags only before pickling
                size_mtime, tags = cls._cache[path_entry]
                essential_tags = cls.extract_essential_tags(tags) if not isinstance(tags, dict) else tags
                pickle.dump((path_entry, (size_mtime, essential_tags)), f, pickle.HIGHEST_PROTOCOL)
        
        return (path, len(valid_paths))
    
    @classmethod
    def cleanup(cls, keep_paths: Optional[set] = None) -> None:
        """Remove unused entries from the shared tag_cache to free memory.
        
        Args:
            keep_paths: Optional set of paths to keep. If None, keeps all paths
                       from all Database instances currently in use.
        """
        if keep_paths is not None:
            # Remove entries not in keep_paths
            keys_to_remove = [k for k in cls._cache if k not in keep_paths]
            for key in keys_to_remove:
                del cls._cache[key]
            
            # Force garbage collection to free memory immediately
            if keys_to_remove:
                gc.collect()
    
    @classmethod
    def trim(cls) -> None:
        """Trim cache to 80% of MAX_CACHE_SIZE by removing least recently used 20% of entries.
        
        This is called when cache exceeds MAX_CACHE_SIZE to prevent unbounded growth.
        Uses LRU (Least Recently Used) eviction strategy with OrderedDict.
        """
        if len(cls._cache) > cls.MAX_CACHE_SIZE:
            remove_count = len(cls._cache) // 5  # Remove 20%
            # Remove oldest entries (LRU) - first items in OrderedDict
            for _ in range(remove_count):
                cls._cache.popitem(last=False)  # Remove from beginning (oldest)
            gc.collect()
    
    @classmethod
    def get(cls, key: str, default=None):
        """Get a value from the cache and mark it as recently used.
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        if key in cls._cache:
            # Move to end for LRU (mark as recently used)
            cls._cache.move_to_end(key)
            return cls._cache[key]
        return default
    
    @classmethod
    def set(cls, key: str, value: Any) -> None:
        """Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache (tuple of (size, mtime), tags)
        """
        # If value is a tuple with tags, wrap the tags in SimpleTag
        if isinstance(value, tuple) and len(value) == 2:
            metadata, tags = value
            if isinstance(tags, dict) and not hasattr(tags, 'get_string'):
                # Wrap plain dict tags in SimpleTag for titleformat compatibility
                tags = cls.restore_tag_dict(tags)
                value = (metadata, tags)
        
        cls._cache[key] = value
        # Check cache size and trim if needed (only if auto_trim is enabled)
        if cls._auto_trim and len(cls._cache) > cls.MAX_CACHE_SIZE:
            cls.trim()
    
    @classmethod
    def contains(cls, key: str) -> bool:
        """Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists, False otherwise
        """
        return key in cls._cache
    
    @classmethod
    def move_to_end(cls, key: str) -> None:
        """Mark a key as recently used by moving it to the end.
        
        Args:
            key: Cache key
        """
        if key in cls._cache:
            cls._cache.move_to_end(key)
