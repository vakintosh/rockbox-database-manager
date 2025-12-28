"""Inspect command - Display raw database file structure."""

import argparse
import logging
import sys
import traceback

from pathlib import Path

from rich.console import Console
from rich.table import Table

from ...constants import FILE_TAGS
from ...indexfile import IndexFile
from ...tagging.tag.tagfile import TagFile


def cmd_inspect(args: argparse.Namespace) -> None:
    """Inspect raw database file structure.

    Args:
        args: Parsed command-line arguments
    """
    console = Console()
    
    # Determine which file to read
    if args.file_number is not None:
        if args.file_number < 0 or args.file_number > 8:
            console.print("[red]Error: File number must be between 0 and 8[/red]")
            sys.exit(1)
        
        filename = f"database_{args.file_number}.tcd"
        file_type = FILE_TAGS[args.file_number]
    else:
        filename = "database_idx.tcd"
        file_type = "index"
    
    file_path = Path(args.database_path) / filename
    
    if not file_path.exists():
        console.print(f"[red]Error: File not found: {file_path}[/red]")
        sys.exit(1)
    
    console.print(f"[cyan]Reading database file: {file_path}[/cyan]")
    console.print(f"[cyan]File type: {file_type}[/cyan]")
    console.print(f"[cyan]File size: {file_path.stat().st_size:,} bytes[/cyan]\n")
    
    try:
        # Parse the file
        if file_type == "index":
            # Need to load tag files first to properly read the index
            tagfiles = {}
            db_dir = Path(args.database_path)
            
            # Load all tag files for proper index entry parsing
            for i, tag_name in enumerate(FILE_TAGS):
                tag_path = db_dir / f"database_{i}.tcd"
                if tag_path.exists():
                    tagfiles[tag_name] = TagFile.read(str(tag_path))
                else:
                    # Create empty tag file if missing
                    tagfiles[tag_name] = TagFile()
            
            # Now read the index file
            result = IndexFile.read(str(file_path), tagfiles)
            
            # Display header information
            table = Table(title="Index File Header", show_header=False)
            table.add_column("Field", style="cyan", width=15)
            table.add_column("Value", style="magenta")
            
            table.add_row("Magic", f"0x{result.magic:08x}")
            table.add_row("Data Size", f"{result.size:,} bytes")
            table.add_row("Entry Count", str(result.count))
            table.add_row("Serial", str(result.serial))
            table.add_row("Commit ID", str(result.commitid))
            table.add_row("Dirty", "Yes" if result.dirty else "No")
            
            console.print(table)
            console.print()
            
            # Show sample entries if not in quiet mode
            if not args.quiet:
                if result.count > 0:
                    console.print(f"[cyan]First {min(5, result.count)} entries:[/cyan]\n")
                    for i, entry in enumerate(result.entries[:5]):
                        console.print(f"[yellow]Entry {i}:[/yellow]")
                        # Display file tags
                        console.print("  File Tags:")
                        for tag in FILE_TAGS:
                            tag_entry = entry[tag]
                            console.print(f"    {tag}: {tag_entry.data if tag_entry else '<None>'}")
                        # Display some embedded tags
                        console.print(f"  Embedded Tags:")
                        console.print(f"    date: {entry.date}")
                        console.print(f"    tracknumber: {entry.tracknumber}")
                        console.print(f"    length: {entry.length}")
                        console.print()
                    
                    if result.count > 5:
                        console.print(f"[dim]... and {result.count - 5} more entries[/dim]\n")
        else:
            try:
                result = TagFile.read(str(file_path))
            except ValueError as e:
                # Handle empty or minimal test files gracefully
                if "Size mismatch" in str(e) and "0 bytes" in str(e):
                    console.print("[yellow]Warning: Empty tag file (no entries)[/yellow]\n")
                    # Create minimal display for empty file
                    with open(file_path, 'rb') as f:
                        import struct
                        magic, size, count = struct.unpack('III', f.read(12))
                        
                    table = Table(title=f"Tag File Header ({file_type})", show_header=False)
                    table.add_column("Field", style="cyan", width=15)
                    table.add_column("Value", style="magenta")
                    
                    table.add_row("Magic", f"0x{magic:08x}")
                    table.add_row("Data Size", f"{size:,} bytes")
                    table.add_row("Entry Count", str(count))
                    
                    console.print(table)
                    return
                else:
                    raise
            
            # Display header information
            table = Table(title=f"Tag File Header ({file_type})", show_header=False)
            table.add_column("Field", style="cyan", width=15)
            table.add_column("Value", style="magenta")
            
            table.add_row("Magic", f"0x{result.magic:08x}")
            table.add_row("Data Size", f"{result.size:,} bytes")
            table.add_row("Entry Count", str(result.count))
            
            console.print(table)
            console.print()
            
            # Show sample entries if not in quiet mode
            if not args.quiet:
                if result.count > 0:
                    console.print(f"[cyan]First {min(10, result.count)} entries:[/cyan]\n")
                    entries_table = Table()
                    entries_table.add_column("Index", style="cyan", justify="right")
                    entries_table.add_column("Offset", style="yellow", justify="right")
                    entries_table.add_column("Length", style="green", justify="right")
                    entries_table.add_column("Data", style="magenta")
                    
                    for i, entry in enumerate(result.entries[:10]):
                        # Truncate long data for display
                        data_str = entry.data
                        if len(data_str) > 50:
                            data_str = data_str[:47] + "..."
                        
                        entries_table.add_row(
                            str(i),
                            f"0x{entry.offset:x}" if entry.offset else "N/A",
                            str(entry.length),
                            data_str
                        )
                    
                    console.print(entries_table)
                    console.print()
                    
                    if result.count > 10:
                        console.print(f"[dim]... and {result.count - 10} more entries[/dim]\n")
        
        # # Print full output if verbose mode
        # if args.verbose:
        #     console.print("[cyan]Full raw output:[/cyan]\n")
        #     console.print(str(result))
        
    except Exception as e:
        console.print(f"[red]Error parsing file: {e}[/red]")
        if logging.getLogger().level <= logging.DEBUG:
            console.print(traceback.format_exc())
        sys.exit(1)
