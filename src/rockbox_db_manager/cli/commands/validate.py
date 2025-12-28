"""Validate command - Check database integrity."""

import argparse
import logging
import sys
from pathlib import Path
from typing import List

from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.console import Console
from rich.table import Table

from ...database import Database
from ...constants import FILE_TAGS


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
