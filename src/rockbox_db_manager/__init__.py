"""Rockbox Database Manager.

A Python application for managing Rockbox database files with a wxPython GUI
and command-line interface. Supports reading audio file tags and generating
database files for Rockbox firmware.

Main modules:
    cli: Command-line interface (rdbm command)
    database: Database generation and management
    gui: wxPython GUI application
    tagging: Audio file tag reading and titleformat parsing
    
Core modules:
    config: Configuration management
    constants: Constants and definitions
    indexfile: Index file handling
    utils: Utility functions
"""

__version__ = "0.3.0"

__all__ = [
    # Sub-packages
    "cli",
    "database",
    "gui",
    "tagging",
    # Core modules
    "config",
    "constants",
    "indexfile",
    "utils",
]
