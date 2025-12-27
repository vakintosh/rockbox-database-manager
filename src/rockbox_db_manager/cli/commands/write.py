"""Write command - Copy database to new location."""

import argparse
import logging
import sys
from pathlib import Path

from ...database import Database
from ..callbacks import log_callback


def cmd_write(args: argparse.Namespace) -> None:
    """Write database to a new location.

    Args:
        args: Parsed command-line arguments
    """
    db_path = Path(args.database_path)
    output_path = Path(args.output_path)

    if not db_path.exists():
        logging.error(f"Database path does not exist: {db_path}")
        sys.exit(1)

    logging.info(f"Loading database from: {db_path}")
    db = Database.read(
        str(db_path),
        callback=log_callback if logging.getLogger().level <= logging.INFO else None,
    )

    output_path.mkdir(parents=True, exist_ok=True)

    logging.info(f"Writing database to: {output_path}")
    db.write(
        str(output_path),
        callback=log_callback if logging.getLogger().level <= logging.INFO else None,
    )

    logging.info("✓ Database written successfully")
    print("\nDatabase copied:")
    print(f"  From: {db_path}")
    print(f"  To:   {output_path}")
