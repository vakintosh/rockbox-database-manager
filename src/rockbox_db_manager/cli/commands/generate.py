"""Generate command - Create Rockbox database from music folder."""

import argparse
import logging
import sys
from pathlib import Path

from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.console import Console
from rich.table import Table

from ...database import Database
from ...database.cache import TagCache
from ...config import Config
from ..callbacks import ProgressCallback, log_callback


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
            tag_cache = TagCache.get_cache()
            logging.info(f"Loaded {len(tag_cache)} cached tags")
    else:
        # Clear any stale cache from previous operations
        TagCache.clear()
        logging.debug("Cleared stale tag cache")

    # Set up callback and progress bar
    console = Console()
    
    # Always show progress bar with message and timer
    with Progress(
        TextColumn("[cyan]Scanning music directory..."),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        # Scanning task - message and timer only
        scan_task = progress.add_task("", total=None)
        callback = ProgressCallback(progress, scan_task)
        
        parallel_flag = not (hasattr(args, 'no_parallel') and args.no_parallel)
        db.add_dir(str(music_path), 
                  dircallback=callback, 
                  filecallback=callback,
                  parallel=parallel_flag)
        
        progress.update(scan_task, total=callback.count, completed=callback.count)

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
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            console=console,
        ) as progress:
            save_task = progress.add_task("save", total=len(db.paths))
            
            def save_callback(msg):
                if isinstance(msg, int):
                    # Initial count
                    progress.update(save_task, total=msg)
                elif isinstance(msg, str):
                    # Each file saved
                    progress.advance(save_task, 1)
            
            actual_path, saved_count = db.save_tags(str(tags_path), callback=save_callback)
        console.print(f"[green]✓[/green] Saved {saved_count} tags to cache: {actual_path}")

    # Generate database
    with Progress(
        SpinnerColumn(),
        TextColumn("[cyan]Generating database entries..."),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        gen_task = progress.add_task("generate", total=total_files)
        
        def gen_callback(current_count, total_count):
            progress.update(gen_task, completed=current_count)
        
        parallel_flag = not (hasattr(args, 'no_parallel') and args.no_parallel)
        db.generate_database(
            callback=gen_callback,
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
    
    # Log failed files if any
    if db.failed:
        logging.warning(f"Failed to read tags from {len(db.failed)} files")
        if logging.getLogger().level <= logging.DEBUG:
            for failed_file in db.failed[:10]:  # Show first 10
                logging.debug(f"  Failed: {failed_file}")
    
    console.print(table)
