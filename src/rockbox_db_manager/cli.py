"""Command-line interface for Rockbox Database Manager (rdbm)."""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from .database import Database
from .config import Config

# Version - should match pyproject.toml
__version__ = "0.1.0"


def setup_logging(level: str) -> None:
    """Configure logging based on user-specified level.
    
    Args:
        level: Logging level (debug, info, warning, error)
    """
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {level}')
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def log_callback(message, **kwargs):
    """Callback function for database operations that logs instead of printing."""
    if isinstance(message, int):
        # Progress indicator (number of items)
        logging.info(f"Processing {message} items...")
    else:
        # Ignore 'end' parameter - logging handles line endings
        logging.debug(str(message))


class SilentCallback:
    """Callback that counts operations without printing."""
    def __init__(self):
        self.count = 0
        self.last_dir = None
    
    def __call__(self, message):
        if isinstance(message, str):
            if os.path.isdir(message):
                self.last_dir = message
                self.count = 0
            else:
                self.count += 1
                if self.count % 100 == 0:
                    logging.info(f"Processed {self.count} files from {self.last_dir}")


def cmd_generate(args: argparse.Namespace) -> None:
    """Generate database from music folder.
    
    Args:
        args: Parsed command-line arguments
    """
    music_path = Path(args.music_path)
    
    if not music_path.exists():
        logging.error(f"Music path does not exist: {music_path}")
        sys.exit(1)
    
    if not music_path.is_dir():
        logging.error(f"Music path is not a directory: {music_path}")
        sys.exit(1)
    
    logging.info(f"Generating database from: {music_path}")
    
    # Create database instance
    db = Database()
    
    # Load configuration if provided
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            logging.error(f"Config file does not exist: {config_path}")
            sys.exit(1)
        
        logging.info(f"Loading configuration from: {config_path}")
        config = Config()
        config.load_config(str(config_path))
        
        # Apply format settings from config
        for field in ['artist', 'album', 'genre', 'title', 'composer', 
                      'comment', 'albumartist', 'grouping']:
            try:
                format_str = config.get(f'database.{field}_format')
                sort_str = config.get(f'database.{field}_sort')
                if format_str:
                    db.set_format(field, format_str, sort_str)
                    logging.debug(f"Set format for {field}: {format_str}")
            except KeyError:
                pass
    
    # Load tags from cache if provided
    if args.load_tags:
        tags_path = Path(args.load_tags)
        if not tags_path.exists():
            logging.warning(f"Tags file does not exist: {tags_path}")
        else:
            logging.info(f"Loading tags from: {tags_path}")
            db.load_tags(str(tags_path), callback=log_callback)
            logging.info(f"Loaded {len(db.tag_cache)} cached tags")
    
    # Set up callback based on logging level
    callback = log_callback if logging.getLogger().level <= logging.DEBUG else SilentCallback()
    
    # Add music directory
    logging.info("Scanning music directory...")
    db.add_dir(str(music_path), dircallback=callback, filecallback=callback)
    
    total_files = len(db.paths)
    failed_files = len(db.failed)
    logging.info(f"Scanned {total_files} files ({failed_files} failed)")
    
    if failed_files > 0:
        logging.warning(f"Failed to read {failed_files} files:")
        for failed in db.failed[:10]:  # Show first 10
            logging.warning(f"  - {failed}")
        if failed_files > 10:
            logging.warning(f"  ... and {failed_files - 10} more")
    
    # Save tags to cache if requested
    if args.save_tags:
        tags_path = Path(args.save_tags)
        logging.info(f"Saving tags cache to: {tags_path}")
        db.save_tags(str(tags_path), callback=log_callback)
        logging.info(f"Saved {len(db.paths)} tags to cache")
    
    # Generate database
    logging.info("Generating database entries...")
    db.generate_database(callback=log_callback if logging.getLogger().level <= logging.DEBUG else None)
    
    logging.info(f"Generated {db.index.count} database entries")
    
    # Write database to output directory
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = music_path / ".rockbox"
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    logging.info(f"Writing database to: {output_path}")
    db.write(str(output_path), callback=log_callback if logging.getLogger().level <= logging.INFO else None)
    
    logging.info("✓ Database generation complete")
    
    # Print summary
    print(f"\nDatabase Summary:")
    print(f"  Input:   {music_path}")
    print(f"  Output:  {output_path}")
    print(f"  Files:   {total_files}")
    print(f"  Entries: {db.index.count}")
    print(f"  Failed:  {failed_files}")


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
    db = Database.read(str(db_path), callback=log_callback if logging.getLogger().level <= logging.INFO else None)
    
    logging.info("✓ Database loaded successfully")
    
    # Print database information
    print(f"\nDatabase Information:")
    print(f"  Location: {db_path}")
    print(f"  Entries:  {db.index.count}")
    
    # Show tag file counts
    from .defs import FILE_TAGS
    print(f"\nTag Files:")
    for field in FILE_TAGS:
        count = len(db.tagfiles[field].entries)
        print(f"  {field:12s}: {count:6d} entries")
    
    # If verbose, show sample entries
    if logging.getLogger().level <= logging.DEBUG:
        print(f"\nSample Entries (first 10):")
        for i, entry in enumerate(db.index.entries[:10]):
            print(f"  {i+1}. {entry.path.data}")


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
    db = Database.read(str(db_path), callback=log_callback if logging.getLogger().level <= logging.INFO else None)
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    logging.info(f"Writing database to: {output_path}")
    db.write(str(output_path), callback=log_callback if logging.getLogger().level <= logging.INFO else None)
    
    logging.info("✓ Database written successfully")
    print(f"\nDatabase copied:")
    print(f"  From: {db_path}")
    print(f"  To:   {output_path}")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='rdbm',
        description='Rockbox Database Manager - Generate and manage Rockbox database files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate database from music folder
  rdbm generate /path/to/music

  # Generate with custom output location
  rdbm generate /path/to/music -o /Volumes/IPOD/.rockbox

  # Generate with configuration file
  rdbm generate /path/to/music -c ~/.rockbox_config.toml

  # Use tag cache to speed up generation
  rdbm generate /path/to/music --load-tags tags.cache --save-tags tags.cache

  # Load and inspect existing database
  rdbm load /Volumes/IPOD/.rockbox

  # Copy database to new location
  rdbm write /Volumes/IPOD/.rockbox /backup/.rockbox

  # Run with verbose logging
  rdbm generate /path/to/music --log-level debug

For GUI mode, use: rockbox-db-manager-gui
        """
    )
    
    parser.add_argument(
        '--version', '-v',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    
    parser.add_argument(
        '--log-level', '-l',
        choices=['debug', 'info', 'warning', 'error'],
        default='info',
        help='Set logging level (default: info)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Generate command
    generate_parser = subparsers.add_parser(
        'generate',
        help='Generate Rockbox database from music folder',
        description='Scan music folder and generate Rockbox database files'
    )
    generate_parser.add_argument(
        'music_path',
        help='Path to music folder to scan'
    )
    generate_parser.add_argument(
        '-o', '--output',
        help='Output directory for database files (default: music_path/.rockbox)'
    )
    generate_parser.add_argument(
        '-c', '--config',
        help='Path to configuration file'
    )
    generate_parser.add_argument(
        '--load-tags',
        help='Load tags from cache file (speeds up regeneration)'
    )
    generate_parser.add_argument(
        '--save-tags',
        help='Save tags to cache file for future use'
    )
    generate_parser.set_defaults(func=cmd_generate)
    
    # Load command
    load_parser = subparsers.add_parser(
        'load',
        help='Load and display database information',
        description='Read existing Rockbox database and show information'
    )
    load_parser.add_argument(
        'database_path',
        help='Path to database directory'
    )
    load_parser.set_defaults(func=cmd_load)
    
    # Write command
    write_parser = subparsers.add_parser(
        'write',
        help='Copy database to new location',
        description='Load database and write to a different location'
    )
    write_parser.add_argument(
        'database_path',
        help='Path to source database directory'
    )
    write_parser.add_argument(
        'output_path',
        help='Path to destination directory'
    )
    write_parser.set_defaults(func=cmd_write)
    
    # Parse arguments
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    
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
        logging.error(f"Error: {e}", exc_info=args.log_level == 'debug')
        sys.exit(1)


if __name__ == '__main__':
    main()
