"""I/O operations for Rockbox database files.

This module handles reading and writing Rockbox database files in the
TagCache Database (.tcd) format.
"""

import os
from typing import Optional, Callable

from ..defs import FILE_TAGS
from ..tagfile import TagFile
from ..indexfile import IndexFile


def myprint(*args, **kwargs):
    """Simple print wrapper for I/O callback functions."""
    sep = kwargs.get('sep', ' ')
    end = kwargs.get('end', '\n')
    
    import sys
    sys.stdout.write(sep.join(str(a) for a in args) + end)


class DatabaseIO:
    """Handles reading and writing Rockbox database files."""
    
    # Buffer size for efficient I/O operations
    BUFFER_SIZE = 8192  # 8KB buffer
    
    @classmethod
    def write(cls, tagfiles: dict, index, out_dir: str = '',
              callback: Optional[Callable] = myprint) -> None:
        """Write the database to a directory.

        Files that will be written:
            database_0.tcd  (artist)
            database_1.tcd  (album)
            database_2.tcd  (genre)
            database_3.tcd  (title)
            database_4.tcd  (filename/path)
            database_5.tcd  (composer)
            database_6.tcd  (comment)
            database_7.tcd  (album artist)
            database_8.tcd  (grouping)
            database_idx.tcd (index)
            
        Args:
            tagfiles: Dictionary of TagFile objects
            index: IndexFile object
            out_dir: Output directory path
            callback: Progress callback function
        """
        # Write the tag files with optimized buffering
        for i, field in enumerate(FILE_TAGS):
            filename = os.path.join(out_dir, f'database_{i}.tcd')
            callback(f'Writing {filename} . . .', end='')
            tagfiles[field].write(filename, buffer_size=cls.BUFFER_SIZE)
            callback('done')

        # Write the index file with optimized buffering
        filename = os.path.join(out_dir, 'database_idx.tcd')
        callback(f'Writing {filename} . . .', end='')
        index.write(filename, buffer_size=cls.BUFFER_SIZE)
        callback('done')
    
    @classmethod
    def read(cls, in_dir: str = '', callback: Optional[Callable] = myprint) -> tuple:
        """Read the database from a directory.

        Files that will be read:
            database_0.tcd  (artist)
            database_1.tcd  (album)
            database_2.tcd  (genre)
            database_3.tcd  (title)
            database_4.tcd  (filename/path)
            database_5.tcd  (composer)
            database_6.tcd  (comment)
            database_7.tcd  (album artist)
            database_8.tcd  (grouping)
            database_idx.tcd (index)
            
        Args:
            in_dir: Input directory path
            callback: Progress callback function
            
        Returns:
            Tuple of (tagfiles_dict, index_object)
        """
        tagfiles = {}
        
        # Read the tag files
        for i, field in enumerate(FILE_TAGS):
            filename = os.path.join(in_dir, f'database_{i}.tcd')
            callback(f'Reading {filename} . . .', end='')
            tagfiles[field] = TagFile.read(filename)
            callback('done')

        # Read the index file
        filename = os.path.join(in_dir, 'database_idx.tcd')
        callback(f'Reading {filename} . . .', end='')
        index = IndexFile.read(filename, tagfiles)
        callback('done')

        return tagfiles, index
