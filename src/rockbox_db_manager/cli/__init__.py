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

from .utils import setup_logging
from .commands import (
    cmd_generate,
    cmd_load,
    cmd_validate,
    cmd_write,
    cmd_inspect,
    cmd_watch,
)

# Version - should match pyproject.toml
__version__ = "0.1.0"

__all__ = [
    "main",
    "cmd_generate",
    "cmd_load",
    "cmd_validate",
    "cmd_write",
    "cmd_inspect",
    "cmd_watch",
    "setup_logging",
]


def main() -> None:
    """Main CLI entry point."""
    # Create parent parser for common arguments
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "--log-level",
        "-l",
        choices=["debug", "info", "warning", "error"],
        default=None,
        help="Set logging level (disabled by default)",
    )
    
    parser = argparse.ArgumentParser(
        prog="rdbm",
        description="Rockbox Database Manager - Generate and manage Rockbox database files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[parent_parser],
        epilog="""
Examples:
  # Generate database from music folder (with parallel processing)
  rdbm generate /path/to/music

  # Generate with custom output location
  rdbm generate /path/to/music -o /Volumes/IPOD/.rockbox

  # Generate with configuration file
  rdbm generate /path/to/music -c ~/.rdbm/.rdbm_config.toml

  # Disable parallel processing for small datasets or debugging
  rdbm generate /path/to/music --no-parallel
  
  # Specify number of worker threads (4 workers)
  rdbm generate /path/to/music --workers 4

  # Use tag cache to speed up generation
  rdbm generate /path/to/music --load-tags tags.cache --save-tags tags.cache

  # Load and inspect existing database
  rdbm load /Volumes/IPOD/.rockbox

  # Validate database integrity
  rdbm validate /Volumes/IPOD/.rockbox

  # Copy database to new location
  rdbm write /Volumes/IPOD/.rockbox /backup/.rockbox

  # Inspect raw database file structure (index file)
  rdbm inspect /Volumes/IPOD/.rockbox

  # Inspect specific tag file (e.g., artist database)
  rdbm inspect /Volumes/IPOD/.rockbox 0

  # Inspect title database with verbose output
  rdbm inspect /Volumes/IPOD/.rockbox 3 --verbose

  # Watch music directory for changes and auto-regenerate
  rdbm watch /path/to/music --output /Volumes/IPOD/.rockbox

  # Run with verbose logging
  rdbm generate /path/to/music --log-level debug

For GUI mode, use: rockbox-db-manager-gui
        """,
    )

    parser.add_argument(
        "--version", "-v", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Generate command
    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate Rockbox database from music folder",
        description="Scan music folder and generate Rockbox database files",
        parents=[parent_parser],
    )
    generate_parser.add_argument("music_path", help="Path to music folder to scan")
    generate_parser.add_argument(
        "-o",
        "--output",
        help="Output directory for database files (default: music_path/.rockbox)",
    )
    generate_parser.add_argument("-c", "--config", help="Path to configuration file")
    generate_parser.add_argument(
        "--load-tags", help="Load tags from cache file (speeds up regeneration)"
    )
    generate_parser.add_argument(
        "--save-tags", help="Save tags to cache file for future use"
    )
    generate_parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Disable parallel processing (useful for debugging or small datasets)"
    )
    generate_parser.add_argument(
        "--workers",
        type=int,
        metavar="N",
        help="Number of worker threads for parallel processing (default: CPU count, max 8)"
    )
    generate_parser.set_defaults(func=cmd_generate)

    # Load command
    load_parser = subparsers.add_parser(
        "load",
        help="Load and display database information",
        description="Read existing Rockbox database and show information",
        parents=[parent_parser],
    )
    load_parser.add_argument("database_path", help="Path to database directory")
    load_parser.set_defaults(func=cmd_load)

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate database integrity",
        description="Check database files for corruption and structural issues",
        parents=[parent_parser],
    )
    validate_parser.add_argument("database_path", help="Path to database directory")
    validate_parser.set_defaults(func=cmd_validate)

    # Write command
    write_parser = subparsers.add_parser(
        "write",
        help="Copy database to new location",
        description="Load database and write to a different location",
        parents=[parent_parser],
    )
    write_parser.add_argument("database_path", help="Path to source database directory")
    write_parser.add_argument("output_path", help="Path to destination directory")
    write_parser.set_defaults(func=cmd_write)

    # Inspect command
    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Inspect raw database file structure",
        description="Parse and display raw Rockbox database file contents (low-level inspection)",
        parents=[parent_parser],
    )
    inspect_parser.add_argument("database_path", help="Path to database directory")
    inspect_parser.add_argument(
        "file_number",
        type=int,
        nargs="?",
        help="Database file number (0-8): 0=artist, 1=album, 2=genre, 3=title, 4=filename, "
             "5=composer, 6=comment, 7=albumartist, 8=grouping. Omit for index file."
    )
    inspect_parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Show only header information, not entries"
    )
    inspect_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show complete raw output"
    )
    inspect_parser.set_defaults(func=cmd_inspect)

    # Watch command
    watch_parser = subparsers.add_parser(
        "watch",
        help="Watch music directory for changes and auto-regenerate database",
        description="Monitor music directory for file changes and automatically regenerate the database",
        parents=[parent_parser],
    )
    watch_parser.add_argument("music_path", help="Path to music folder to watch")
    watch_parser.add_argument(
        "-o",
        "--output",
        help="Output directory for database files (default: music_path/.rockbox)",
    )
    watch_parser.add_argument("-c", "--config", help="Path to configuration file")
    watch_parser.add_argument(
        "--load-tags", help="Load tags from cache file (speeds up regeneration)"
    )
    watch_parser.add_argument(
        "--save-tags", help="Save tags to cache file for future use"
    )
    watch_parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Disable parallel processing (useful for debugging or small datasets)"
    )
    watch_parser.add_argument(
        "--workers",
        type=int,
        metavar="N",
        help="Number of worker threads for parallel processing (default: CPU count, max 8)"
    )
    watch_parser.set_defaults(func=cmd_watch)

    # Parse arguments
    args = parser.parse_args()

    # Set up logging - use WARNING as default to suppress INFO messages
    # but still allow the logging module to function for level checks
    if args.log_level:
        setup_logging(args.log_level)
    else:
        # Set to CRITICAL to suppress all standard log output
        setup_logging('critical')

    # Show help if no command provided
    if not args.command:
        parser.print_help()
        sys.exit(1)

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
