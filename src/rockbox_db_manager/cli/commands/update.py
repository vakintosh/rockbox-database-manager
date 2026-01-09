"""Update command - Incrementally update database with new/deleted files."""

import argparse
import logging
import sys
import time
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
from ..callbacks import ProgressCallback, log_callback
from ..utils import ExitCode, json_output
from ..schemas import ErrorResponse, UpdateSuccessResponse


def cmd_update(args: argparse.Namespace) -> None:
    """Update database with new and deleted files (delta update).

    This command performs an incremental update that:
    - Scans for new files not in the database
    - Marks missing files as deleted (preserves statistics)
    - Is faster than full rebuild
    - Preserves playcount, rating, lastplayed, and other stats

    Args:
        args: Parsed command-line arguments

    Exit Codes:
        0: Success
        10: Invalid input (directory doesn't exist)
        20: Data error (failed to load database)
        30: Update failed
    """
    db_path = Path(args.db_dir).resolve()
    music_path = Path(args.music_dir).resolve()
    output_path = Path(args.output) if args.output else db_path
    output_path = output_path.resolve()
    use_json = getattr(args, "json", False)

    # In JSON mode, suppress INFO/DEBUG logs to keep output clean for parsing
    if use_json and logging.getLogger().level < logging.WARNING:
        logging.getLogger().setLevel(logging.WARNING)

    console = Console(quiet=use_json)

    # Validate database directory
    if not db_path.exists():
        if use_json:
            json_output(
                ErrorResponse(
                    error="invalid_input",
                    message=f"Database path does not exist: {db_path}",
                ),
                ExitCode.INVALID_INPUT,
            )
        logging.error("Database path does not exist: %s", db_path)
        sys.exit(ExitCode.INVALID_INPUT)

    if not db_path.is_dir():
        if use_json:
            json_output(
                ErrorResponse(
                    error="invalid_input",
                    message=f"Database path is not a directory: {db_path}",
                ),
                ExitCode.INVALID_INPUT,
            )
        logging.error("Database path is not a directory: %s", db_path)
        sys.exit(ExitCode.INVALID_INPUT)

    # Validate music directory
    if not music_path.exists():
        if use_json:
            json_output(
                ErrorResponse(
                    error="invalid_input",
                    message=f"Music path does not exist: {music_path}",
                ),
                ExitCode.INVALID_INPUT,
            )
        logging.error("Music path does not exist: %s", music_path)
        sys.exit(ExitCode.INVALID_INPUT)

    if not music_path.is_dir():
        if use_json:
            json_output(
                ErrorResponse(
                    error="invalid_input",
                    message=f"Music path is not a directory: {music_path}",
                ),
                ExitCode.INVALID_INPUT,
            )
        logging.error("Music path is not a directory: %s", music_path)
        sys.exit(ExitCode.INVALID_INPUT)

    start_time = time.time()

    # Load existing database
    console.print(f"\n[cyan]Loading existing database from:[/cyan] {db_path}")
    try:
        callback = (
            log_callback
            if logging.getLogger().level <= logging.INFO
            else lambda msg, **kwargs: None
        )
        db = Database.read(str(db_path), callback=callback)
    except Exception as e:
        if use_json:
            json_output(
                ErrorResponse(
                    error="data_error", message=f"Failed to load database: {e}"
                ),
                ExitCode.DATA_ERROR,
            )
        logging.error("Failed to load database: %s", e)
        sys.exit(ExitCode.DATA_ERROR)

    original_count = db.index.count
    console.print(f"[green]✓[/green] Loaded database with {original_count:,} entries\n")

    # Update database
    console.print(f"[cyan]Updating database from:[/cyan] {music_path}\n")

    try:
        if not use_json:
            callback = ProgressCallback()
            with Progress(
                SpinnerColumn(),
                TextColumn("[cyan]{task.description}"),
                BarColumn(),
                TextColumn("{task.completed}/{task.total}"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Scanning...", total=None)

                def update_callback(current, total, status="Scanning..."):
                    if total and task.total is None:
                        progress.update(task, total=total)
                    progress.update(task, completed=current, description=status)

                stats = db.update_database(str(music_path), callback=update_callback)
        else:
            stats = db.update_database(
                str(music_path), callback=lambda *args, **kwargs: None
            )
    except Exception as e:
        if use_json:
            json_output(
                ErrorResponse(error="update_failed", message=f"Update failed: {e}"),
                ExitCode.GENERATION_FAILED,
            )
        logging.error("Update failed: %s", e)
        sys.exit(ExitCode.GENERATION_FAILED)

    new_count = db.index.count
    console.print(f"\n[green]✓[/green] Update complete: {new_count:,} total entries")

    # Write updated database
    if output_path != db_path or args.output:
        console.print(f"\n[cyan]Writing updated database to:[/cyan] {output_path}")
        try:
            callback = (
                log_callback
                if logging.getLogger().level <= logging.INFO
                else lambda msg, **kwargs: None
            )
            db.write(str(output_path), callback=callback)
        except Exception as e:
            if use_json:
                json_output(
                    ErrorResponse(
                        error="write_failed", message=f"Failed to write database: {e}"
                    ),
                    ExitCode.WRITE_FAILED,
                )
            logging.error("Failed to write database: %s", e)
            sys.exit(ExitCode.WRITE_FAILED)
        console.print("[green]✓[/green] Database written successfully")
    else:
        console.print(f"\n[cyan]Writing changes back to:[/cyan] {db_path}")
        try:
            callback = (
                log_callback
                if logging.getLogger().level <= logging.INFO
                else lambda msg, **kwargs: None
            )
            db.write(str(db_path), callback=callback)
        except Exception as e:
            if use_json:
                json_output(
                    ErrorResponse(
                        error="write_failed", message=f"Failed to write database: {e}"
                    ),
                    ExitCode.WRITE_FAILED,
                )
            logging.error("Failed to write database: %s", e)
            sys.exit(ExitCode.WRITE_FAILED)
        console.print("[green]✓[/green] Database updated successfully")

    duration_ms = int((time.time() - start_time) * 1000)

    # Prepare summary
    added = stats.get("added", 0)
    deleted = stats.get("deleted", 0)
    unchanged = stats.get("unchanged", 0)
    failed = stats.get("failed", 0)

    # JSON output
    if use_json:
        json_output(
            UpdateSuccessResponse(
                db_path=str(db_path),
                music_dir=str(music_path),
                output_dir=str(output_path),
                original_entries=original_count,
                final_entries=new_count,
                added=added,
                deleted=deleted,
                unchanged=unchanged,
                failed=failed,
                duration_ms=duration_ms,
            ),
            ExitCode.SUCCESS,
        )
        sys.exit(ExitCode.SUCCESS)

    # Print summary table (normal mode)
    console.print()
    table = Table(title="Update Summary")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row("Database", str(db_path))
    table.add_row("Music Directory", str(music_path))
    table.add_row("Output", str(output_path))
    table.add_row("Original Entries", f"{original_count:,}")
    table.add_row("Final Entries", f"{new_count:,}")
    table.add_row("Added", f"{added:,}")
    table.add_row("Deleted", f"{deleted:,}")
    table.add_row("Unchanged", f"{unchanged:,}")
    if failed > 0:
        table.add_row("Failed", f"{failed:,}", style="yellow")
    table.add_row("Duration", f"{duration_ms:,} ms")

    console.print(table)
    console.print()

    sys.exit(ExitCode.SUCCESS)
