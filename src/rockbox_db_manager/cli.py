"""Command-line interface for Rockbox Database Manager (rdbm)."""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List

from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.console import Console
from rich.table import Table

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
        raise ValueError(f"Invalid log level: {level}")

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def log_callback(message, **kwargs):
    """Callback function for database operations that logs instead of printing."""
    if isinstance(message, int):
        # Progress indicator (number of items)
        logging.info(f"Processing {message} items...")
    else:
        # Ignore 'end' parameter - logging handles line endings
        logging.debug(str(message))


class ProgressCallback:
    """Callback that updates a rich progress bar."""

    def __init__(self, progress, task_id):
        self.progress = progress
        self.task_id = task_id
        self.count = 0
        self.last_dir = None

    def __call__(self, message):
        if isinstance(message, str):
            if os.path.isdir(message):
                self.last_dir = os.path.basename(message)
                self.count = 0
                self.progress.update(self.task_id, description=f"[cyan]Scanning: {self.last_dir}...")
            else:
                self.count += 1
                self.progress.advance(self.task_id, 1)
        elif isinstance(message, int):
            # Update total for progress bar
            self.progress.update(self.task_id, total=message)


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
    
    # Configure parallelization
    if hasattr(args, 'no_parallel') and args.no_parallel:
        db.use_parallel = False
        logging.info("Parallel processing disabled")
    
    if hasattr(args, 'workers') and args.workers:
        db.max_workers = args.workers
        logging.info(f"Using {args.workers} worker threads")

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
        for field in [
            "artist",
            "album",
            "genre",
            "title",
            "composer",
            "comment",
            "albumartist",
            "grouping",
        ]:
            try:
                format_str = config.get(f"database.{field}_format")
                sort_str = config.get(f"database.{field}_sort")
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

    # Set up callback and progress bar based on logging level
    console = Console()
    
    if logging.getLogger().level <= logging.INFO:
        # Use progress bar for info level and above
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[cyan]{task.completed} files"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            # Scanning task
            scan_task = progress.add_task("[cyan]Scanning music directory...", total=None)
            callback = ProgressCallback(progress, scan_task)
            
            parallel_flag = not (hasattr(args, 'no_parallel') and args.no_parallel)
            db.add_dir(str(music_path), 
                      dircallback=callback, 
                      filecallback=callback,
                      parallel=parallel_flag)
            
            progress.update(scan_task, total=callback.count, completed=callback.count)
    else:
        # Use silent callback for debug level
        callback = log_callback if logging.getLogger().level <= logging.DEBUG else SilentCallback()
        parallel_flag = not (hasattr(args, 'no_parallel') and args.no_parallel)
        db.add_dir(str(music_path), 
                  dircallback=callback, 
                  filecallback=callback,
                  parallel=parallel_flag)

    total_files = len(db.paths)
    failed_files = len(db.failed)
    console.print(f"\n[green]✓[/green] Scanned {total_files} files ({failed_files} failed)")

    if failed_files > 0:
        logging.warning(f"Failed to read {failed_files} files:")
        for failed in db.failed[:10]:  # Show first 10
            logging.warning(f"  - {failed}")
        if failed_files > 10:
            logging.warning(f"  ... and {failed_files - 10} more")

    # Save tags to cache if requested
    if args.save_tags:
        tags_path = Path(args.save_tags)
        with Progress(
            SpinnerColumn(),
            TextColumn("[cyan]Saving tags cache..."),
            console=console,
        ) as progress:
            progress.add_task("save", total=None)
            db.save_tags(str(tags_path), callback=log_callback)
        console.print(f"[green]✓[/green] Saved {len(db.paths)} tags to cache: {tags_path}")

    # Generate database
    with Progress(
        SpinnerColumn(),
        TextColumn("[cyan]Generating database entries..."),
        BarColumn(),
        TextColumn("[progress.percentage]{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        gen_task = progress.add_task("generate", total=total_files)
        
        def gen_callback(msg):
            if logging.getLogger().level <= logging.DEBUG:
                log_callback(msg)
            progress.advance(gen_task, 1)
        
        parallel_flag = not (hasattr(args, 'no_parallel') and args.no_parallel)
        db.generate_database(
            callback=gen_callback if logging.getLogger().level <= logging.INFO else None,
            parallel=parallel_flag
        )

    console.print(f"[green]✓[/green] Generated {db.index.count} database entries")

    # Write database to output directory
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = music_path / ".rockbox"

    output_path.mkdir(parents=True, exist_ok=True)

    with Progress(
        SpinnerColumn(),
        TextColumn("[cyan]Writing database files..."),
        BarColumn(),
        TextColumn("{task.completed}/{task.total} files"),
        console=console,
    ) as progress:
        write_task = progress.add_task("write", total=10)  # 9 tag files + 1 index
        
        def write_callback(msg, **kwargs):
            if 'done' in str(msg):
                progress.advance(write_task, 1)
            elif logging.getLogger().level <= logging.DEBUG:
                log_callback(msg, **kwargs)
        
        db.write(str(output_path), callback=write_callback)

    console.print("[green]✓[/green] Database generation complete")

    # Print summary table
    table = Table(title="\nDatabase Summary")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="magenta")
    
    table.add_row("Input", str(music_path))
    table.add_row("Output", str(output_path))
    table.add_row("Files", str(total_files))
    table.add_row("Entries", str(db.index.count))
    table.add_row("Failed", str(failed_files))
    
    console.print(table)


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
    from .defs import FILE_TAGS

    print("\nTag Files:")
    for field in FILE_TAGS:
        count = len(db.tagfiles[field].entries)
        print(f"  {field:12s}: {count:6d} entries")

    # If verbose, show sample entries
    if logging.getLogger().level <= logging.DEBUG:
        print("\nSample Entries (first 10):")
        for i, entry in enumerate(db.index.entries[:10]):
            print(f"  {i + 1}. {entry.path.data}")


def cmd_validate(args: argparse.Namespace) -> None:
    """Validate database integrity.

    Args:
        args: Parsed command-line arguments
    """
    db_path = Path(args.database_path)
    console = Console()

    if not db_path.exists():
        logging.error(f"Database path does not exist: {db_path}")
        sys.exit(1)

    if not db_path.is_dir():
        logging.error(f"Database path is not a directory: {db_path}")
        sys.exit(1)

    console.print(f"\n[cyan]Validating database:[/cyan] {db_path}\n")

    issues: List[str] = []
    warnings: List[str] = []

    # Check if all required files exist
    from .defs import FILE_TAGS
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[cyan]{task.description}"),
        console=console,
    ) as progress:
        check_task = progress.add_task("Checking database files...", total=None)
        
        required_files = [f"database_{i}.tcd" for i in range(len(FILE_TAGS))]
        required_files.append("database_idx.tcd")
        
        missing_files = []
        for filename in required_files:
            filepath = db_path / filename
            if not filepath.exists():
                missing_files.append(filename)
        
        if missing_files:
            issues.append(f"Missing {len(missing_files)} required database files: {', '.join(missing_files)}")
            progress.update(check_task, description="[red]✗ Missing database files")
        else:
            progress.update(check_task, description="[green]✓ All database files present")

    # Try to read the database
    if not missing_files:
        with Progress(
            SpinnerColumn(),
            TextColumn("[cyan]{task.description}"),
            console=console,
        ) as progress:
            read_task = progress.add_task("Loading database...", total=None)
            
            try:
                db = Database.read(str(db_path), callback=lambda msg, **kwargs: None)
                progress.update(read_task, description="[green]✓ Database loaded successfully")
                
                # Validate database structure
                validation_task = progress.add_task("Validating structure...", total=None)
                
                # Check index entries
                if db.index.count == 0:
                    warnings.append("Database has no entries (empty database)")
                
                # Check for orphaned references
                orphaned_count = 0
                NULL_INDEX = 4294967295  # -1 in uint32, indicates no value
                for i, entry in enumerate(db.index.entries):
                    # Check if all tag references are valid
                    for field in FILE_TAGS:
                        tag_entry = getattr(entry, field, None)
                        if tag_entry and hasattr(tag_entry, 'index'):
                            tag_index = tag_entry.index
                            # Skip NULL_INDEX as it's valid (means no value)
                            if tag_index != NULL_INDEX and tag_index >= len(db.tagfiles[field].entries):
                                orphaned_count += 1
                                if orphaned_count <= 5:  # Show first 5
                                    issues.append(f"Entry {i}: Invalid {field} reference (index {tag_index})")
                
                if orphaned_count > 5:
                    issues.append(f"... and {orphaned_count - 5} more orphaned references")
                
                if orphaned_count == 0:
                    progress.update(validation_task, description="[green]✓ No orphaned references found")
                else:
                    progress.update(validation_task, description=f"[red]✗ Found {orphaned_count} orphaned references")
                
                # Check for duplicate entries
                paths = [entry.path.data for entry in db.index.entries if hasattr(entry, 'path') and hasattr(entry.path, 'data')]
                duplicates = len(paths) - len(set(paths))
                if duplicates > 0:
                    warnings.append(f"Found {duplicates} duplicate file paths in index")
                
            except Exception as e:
                progress.update(read_task, description="[red]✗ Failed to load database")
                issues.append(f"Failed to read database: {str(e)}")

    # Print results
    console.print()
    
    if issues:
        console.print("[red bold]✗ Validation Failed[/red bold]\n")
        console.print("[red]Issues found:[/red]")
        for issue in issues:
            console.print(f"  [red]•[/red] {issue}")
    else:
        console.print("[green bold]✓ Validation Passed[/green bold]\n")
    
    if warnings:
        console.print("\n[yellow]Warnings:[/yellow]")
        for warning in warnings:
            console.print(f"  [yellow]•[/yellow] {warning}")
    
    # Print statistics if database loaded successfully
    if not missing_files and 'db' in locals():
        console.print()
        table = Table(title="Database Statistics")
        table.add_column("Tag File", style="cyan")
        table.add_column("Entries", justify="right", style="magenta")
        
        for field in FILE_TAGS:
            count = len(db.tagfiles[field].entries)
            table.add_row(field, str(count))
        
        table.add_row("[bold]index[/bold]", f"[bold]{db.index.count}[/bold]")
        console.print(table)
    
    console.print()
    
    # Exit with error code if issues found
    if issues:
        sys.exit(1)


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


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="rdbm",
        description="Rockbox Database Manager - Generate and manage Rockbox database files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
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

  # Run with verbose logging
  rdbm generate /path/to/music --log-level debug

For GUI mode, use: rockbox-db-manager-gui
        """,
    )

    parser.add_argument(
        "--version", "-v", action="version", version=f"%(prog)s {__version__}"
    )

    parser.add_argument(
        "--log-level",
        "-l",
        choices=["debug", "info", "warning", "error"],
        default="info",
        help="Set logging level (default: info)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Generate command
    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate Rockbox database from music folder",
        description="Scan music folder and generate Rockbox database files",
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
    )
    load_parser.add_argument("database_path", help="Path to database directory")
    load_parser.set_defaults(func=cmd_load)

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate database integrity",
        description="Check database files for corruption and structural issues",
    )
    validate_parser.add_argument("database_path", help="Path to database directory")
    validate_parser.set_defaults(func=cmd_validate)

    # Write command
    write_parser = subparsers.add_parser(
        "write",
        help="Copy database to new location",
        description="Load database and write to a different location",
    )
    write_parser.add_argument("database_path", help="Path to source database directory")
    write_parser.add_argument("output_path", help="Path to destination directory")
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
        logging.error(f"Error: {e}", exc_info=args.log_level == "debug")
        sys.exit(1)


if __name__ == "__main__":
    main()
