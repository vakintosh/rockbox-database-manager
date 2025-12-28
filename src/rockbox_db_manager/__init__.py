"""Rockbox Database Manager.

A Python application for managing Rockbox database files with a wxPython GUI
and command-line interface. Supports reading audio file tags and generating
database files for Rockbox firmware.

Main modules:
    cli: Command-line interface (rdbm command)
    database: Database generation and management (refactored into sub-package)
    gui: wxPython GUI application (refactored into sub-package)
    tagging: Audio file tag reading (refactored into sub-package)
    
Core modules:
    defs: Constants and definitions
    indexfile: Index file handling
    tagfile: Tag file handling
    rbdb: Database format specifications
    rblib: Rockbox library utilities
    utils: Utility functions
    config: Configuration management
    progress: Progress tracking
"""

__version__ = "0.1.0"

__all__ = [
    # Sub-packages
    "cli",
    "database",
    "gui",
    "tagging",
    # Core modules
    "defs",
    "indexfile",
    "tagfile",
    "rbdb",
    "rblib",
    "utils",
    "config",
    "progress",
]
