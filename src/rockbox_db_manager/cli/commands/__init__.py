"""CLI command implementations.

Each module in this package implements a specific rdbm subcommand:
    generate.py: Generate database from music directory
    load.py: Load and display existing database
    validate.py: Validate database integrity
    write.py: Write database files to disk
    inspect.py: Inspect individual database files
    watch.py: Watch directory for changes and auto-regenerate
"""

from .generate import cmd_generate
from .load import cmd_load
from .validate import cmd_validate
from .write import cmd_write
from .inspect import cmd_inspect
# from .watch import cmd_watch

__all__ = [
    "cmd_generate",
    "cmd_load",
    "cmd_validate",
    "cmd_write",
    "cmd_inspect",
    # "cmd_watch",
]
