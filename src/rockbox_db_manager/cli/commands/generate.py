"""Generate command - Create Rockbox database from music folder."""

import argparse
import logging
import sys
from pathlib import Path

from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
)
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
        logging.error("Music path does not exist: %s", music_path)
        sys.exit(1)

    if not music_path.is_dir():
        logging.error("Music path is not a directory: %s", music_path)
        sys.exit(1)

    logging.info("Generating database from: %s", music_path)

    # Create database instance
    db = Database()

    # Configure parallelization
    if hasattr(args, "no_parallel") and args.no_parallel:
        db.use_parallel = False
        logging.info("Parallel processing disabled")

    if hasattr(args, "workers") and args.workers:
        db.max_workers = args.workers
        logging.info("Using %s worker threads", args.workers)

    # Load configuration if provided
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            logging.error("Config file does not exist: %s", config_path)
            sys.exit(1)

        logging.info("Loading configuration from: %s", config_path)
        config = Config()
        config.load()

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
                format_str = config.get_format(field)
                sort_str = config.get_sort_format(field)
                if format_str:
                    db.set_format(field, format_str, sort_str)
                    logging.debug("Set format for %s: %s", field, format_str)
            except KeyError:
                pass

    # Load tags from cache if provided
    if args.load_tags:
        tags_path = Path(args.load_tags)
        # Try with .gz extension if file doesn't exist
        if not tags_path.exists() and not str(tags_path).endswith(".gz"):
            tags_path_gz = Path(str(tags_path) + ".gz")
            if tags_path_gz.exists():
                tags_path = tags_path_gz
                logging.debug("Using compressed cache file: %s", tags_path)

        if not tags_path.exists():
            logging.warning("Tags file does not exist: %s", tags_path)
        else:
            logging.info("Loading tags from: %s", tags_path)
            db.load_tags(str(tags_path), callback=log_callback)
            tag_cache = TagCache.get_cache()
            logging.info("Loaded %s cached tags", len(tag_cache))
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

        parallel_flag = not (hasattr(args, "no_parallel") and args.no_parallel)
        db.add_dir(
            str(music_path),
            dircallback=callback,
            filecallback=callback,
            parallel=parallel_flag,
        )

        progress.update(scan_task, total=callback.count, completed=callback.count)

    total_files = len(db.paths)
    failed_files = len(db.failed)
    console.print(
        f"\n[green]✓[/green] Scanned {total_files} files ({failed_files} failed)"
    )

    if failed_files > 0:
        logging.warning("Failed to read %s files:", failed_files)
        for failed in db.failed[:10]:  # Show first 10
            logging.warning("  - %s", failed)
        if failed_files > 10:
            logging.warning("  ... and %s more", failed_files - 10)

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

            actual_path, saved_count = db.save_tags(
                str(tags_path), callback=save_callback
            )
        console.print(
            f"[green]✓[/green] Saved {saved_count} tags to cache: {actual_path}"
        )

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

        parallel_flag = not (hasattr(args, "no_parallel") and args.no_parallel)
        db.generate_database(callback=gen_callback, parallel=parallel_flag)

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
            if "done" in str(msg):
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
        logging.warning("Failed to read tags from %s files", len(db.failed))
        if logging.getLogger().level <= logging.DEBUG:
            for failed_file in db.failed[:10]:  # Show first 10
                logging.debug("  Failed: %s", failed_file)

    console.print(table)
