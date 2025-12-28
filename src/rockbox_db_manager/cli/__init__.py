"""Command-line interface for Rockbox Database Manager (rdbm).

This package provides the 'rdbm' command-line tool with various subcommands:
    generate: Generate Rockbox database from music directory
    load: Load and display existing database files
    validate: Validate database file integrity
    inspect: Inspect individual database files
    watch: Watch directory for changes and auto-regenerate

Modules:
    commands/: Command implementations (generate, load, validate, etc.)
    callbacks.py: Common callback functions
    utils.py: CLI utility functions
"""

import argparse
import logging
import sys

from rich_argparse import RichHelpFormatter

from .utils import setup_logging
from .commands import (
    cmd_generate,
    cmd_load,
    cmd_validate,
    cmd_write,
    cmd_inspect,
    # cmd_watch,
)

# Version - should match pyproject.toml
__version__ = "0.2.0"

__all__ = [
    "main",
    "cmd_generate",
    "cmd_load",
    "cmd_validate",
    "cmd_write",
    "cmd_inspect",
    # "cmd_watch",
    "setup_logging",
]

class RichRawHelpFormatter(RichHelpFormatter, argparse.RawDescriptionHelpFormatter):
    """Combines Rich formatting with the ability to keep line breaks (Raw)."""
    pass

def main() -> None:
    """Main CLI entry point."""

    # Parent parser for shared options
    parent_parser = argparse.ArgumentParser(add_help=False)

    parent_parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parent_parser.add_argument(
        "-l",
        "--log-level",
        # choices=["debug", "info", "warning", "error"],
        default=None,
        help="Set logging level (disabled by default)",
    )

    parser = argparse.ArgumentParser(
        prog="rdbm",
        usage="rdbm <command> [options]",
        description="Rockbox Database Manager - Generate and manage Rockbox database files",
        formatter_class=RichRawHelpFormatter,  # Use the hybrid class here
        parents=[parent_parser],
    )

    # Subcommands
    subparsers = parser.add_subparsers(
        title="Commands",
        dest="command",
        metavar="",
    )

    # # Global options
    # parser.add_argument(
    #     "-v",
    #     "--version",
    #     action="version",
    #     version=f"%(prog)s {__version__}",
    # )

    # ──────────────────────────────
    # generate
    # ──────────────────────────────
    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate Rockbox database from music folder",
        usage="rdbm generate <music_path> [options]",
        description="Scan music folder and generate Rockbox database files",
        parents=[parent_parser],
        formatter_class=RichHelpFormatter,
    )
    generate_parser.add_argument("music_path", help="Path to music folder to scan")
    generate_parser.add_argument(
        "-o",
        "--output",
        help="Output directory for database files (default: music_path/.rockbox)",
    )
    generate_parser.add_argument("-c", "--config", help="Path to configuration file")
    generate_parser.add_argument(
        "--load-tags",
        help="Load tags from cache file (speeds up regeneration)",
    )
    generate_parser.add_argument(
        "--save-tags",
        help="Save tags to cache file for future use",
    )
    generate_parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Disable parallel processing (useful for debugging or small datasets)",
    )
    generate_parser.add_argument(
        "--workers",
        type=int,
        metavar="N",
        help="Number of worker threads for parallel processing (default: CPU count, max 8)",
    )
    generate_parser.set_defaults(func=cmd_generate)

    # ──────────────────────────────
    # load
    # ──────────────────────────────
    load_parser = subparsers.add_parser(
        "load",
        help="Load and display database information",
        usage="rdbm load <database_path>",
        description="Read existing Rockbox database and show information",
        parents=[parent_parser],
        formatter_class=RichHelpFormatter,
    )
    load_parser.add_argument("database_path", help="Path to database directory")
    load_parser.set_defaults(func=cmd_load)

    # ──────────────────────────────
    # validate
    # ──────────────────────────────
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate database integrity",
        usage="rdbm validate <database_path>",
        description="Check database files for corruption and structural issues",
        parents=[parent_parser],
        formatter_class=RichHelpFormatter,
    )
    validate_parser.add_argument("database_path", help="Path to database directory")
    validate_parser.set_defaults(func=cmd_validate)

    # ──────────────────────────────
    # write
    # ──────────────────────────────
    write_parser = subparsers.add_parser(
        "write",
        help="Copy database to new location",
        usage="rdbm write <database_path> <output_path>",
        description="Load database and write to a different location",
        parents=[parent_parser],
        formatter_class=RichHelpFormatter,
    )
    write_parser.add_argument("database_path", help="Path to source database directory")
    write_parser.add_argument("output_path", help="Path to destination directory")
    write_parser.set_defaults(func=cmd_write)

    # ──────────────────────────────
    # inspect
    # ──────────────────────────────
    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Inspect raw database file structure",
        usage="rdbm inspect <database_path> [file_number] [options]",
        description=(
            "Parse and display raw Rockbox database file contents "
            "(low-level inspection)"
        ),
        parents=[parent_parser],
        formatter_class=RichHelpFormatter,
    )
    inspect_parser.add_argument("database_path", help="Path to database directory")
    inspect_parser.add_argument(
        "file_number",
        type=int,
        nargs="?",
        help=(
            "Database file number (0-8): "
            "0=artist, 1=album, 2=genre, 3=title, 4=filename, "
            "5=composer, 6=comment, 7=albumartist, 8=grouping. "
            "Omit for index file."
        ),
    )
    inspect_parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Show only header information, not entries",
    )
    # inspect_parser.add_argument(
    #     "-v",
    #     "--verbose",
    #     action="store_true",
    #     help="Show complete raw output",
    # )
    inspect_parser.set_defaults(func=cmd_inspect)

    # # ──────────────────────────────
    # # watch
    # # ──────────────────────────────
    # watch_parser = subparsers.add_parser(
    #     "watch",
    #     help="Watch music directory for changes and auto-regenerate database",
    #     usage="rdbm watch <music_path> [options]",
    #     description=(
    #         "Monitor music directory for file changes and "
    #         "automatically regenerate the database"
    #     ),
    #     parents=[parent_parser],
    #     formatter_class=RichHelpFormatter,
    # )
    # watch_parser.add_argument("music_path", help="Path to music folder to watch")
    # watch_parser.add_argument(
    #     "-o",
    #     "--output",
    #     help="Output directory for database files (default: music_path/.rockbox)",
    # )
    # watch_parser.add_argument("-c", "--config", help="Path to configuration file")
    # watch_parser.add_argument(
    #     "--load-tags",
    #     help="Load tags from cache file (speeds up regeneration)",
    # )
    # watch_parser.add_argument(
    #     "--save-tags",
    #     help="Save tags to cache file for future use",
    # )
    # watch_parser.add_argument(
    #     "--no-parallel",
    #     action="store_true",
    #     help="Disable parallel processing (useful for debugging or small datasets)",
    # )
    # watch_parser.add_argument(
    #     "--workers",
    #     type=int,
    #     metavar="N",
    #     help="Number of worker threads for parallel processing (default: CPU count, max 8)",
    # )
    # watch_parser.set_defaults(func=cmd_watch)

    # Parse args
    args = parser.parse_args()

    # Show help if no command is provided
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Logging setup
    if args.log_level:
        setup_logging(args.log_level)
    else:
        setup_logging("critical")

    # Execute command
    try:
        args.func(args)
    except KeyboardInterrupt:
        logging.info("\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logging.error(f"Error: {e}", exc_info=args.log_level == "debug")
        sys.exit(1)


if __name__ == "__main__":
    main()
