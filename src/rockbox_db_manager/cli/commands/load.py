"""Load command - Display database information."""

import argparse
import logging
import sys
from pathlib import Path

from ...database import Database
from ..callbacks import log_callback


def cmd_load(args: argparse.Namespace) -> None:
    """Load and display database information.

    Args:
        args: Parsed command-line arguments
    """
    db_path = Path(args.database_path)

    if not db_path.exists():
        logging.error(f"Database path does not exist: {db_path}")
        sys.exit(1)

    if not db_path.is_dir():
        logging.error(f"Database path is not a directory: {db_path}")
        sys.exit(1)

    logging.info(f"Loading database from: {db_path}")

    # Load database
    db = Database.read(
        str(db_path),
        callback=log_callback if logging.getLogger().level <= logging.INFO else None,
    )

    logging.info("✓ Database loaded successfully")

    # Print database information
    print("\nDatabase Information:")
    print(f"  Location: {db_path}")
    print(f"  Entries:  {db.index.count}")

    # Show tag file counts
    from ...defs import FILE_TAGS

    print("\nTag Files:")
    for field in FILE_TAGS:
        count = len(db.tagfiles[field].entries)
        print(f"  {field:12s}: {count:6d} entries")

    # If verbose, show sample entries
    if logging.getLogger().level <= logging.DEBUG:
        print("\nSample Entries (first 10):")
        for i, entry in enumerate(db.index.entries[:10]):
            print(f"  {i + 1}. {entry.path.data}")
