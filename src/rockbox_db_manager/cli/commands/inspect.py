"""Inspect command - Display raw database file structure."""

import argparse
import logging
import sys
import traceback

from pathlib import Path

from rich.console import Console
from rich.table import Table

from ... import rbdb


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
        file_type = rbdb.TAGS[args.file_number]
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
            result = rbdb.parse_indexfile(str(file_path))
            
            # Display header information
            table = Table(title="Index File Header", show_header=False)
            table.add_column("Field", style="cyan", width=15)
            table.add_column("Value", style="magenta")
            
            table.add_row("Magic", f"0x{result.magic:08x}")
            table.add_row("Data Size", f"{result.datasize:,} bytes")
            table.add_row("Entry Count", str(result.entry_count))
            table.add_row("Serial", str(result.serial))
            table.add_row("Commit ID", str(result.commitid))
            table.add_row("Dirty", "Yes" if result.dirty else "No")
            
            console.print(table)
            console.print()
            
            # Show sample entries if not in quiet mode
            if not args.quiet:
                if result.entry_count > 0:
                    console.print(f"[cyan]First {min(5, result.entry_count)} entries:[/cyan]\n")
                    for i, entry in enumerate(result.entries[:5]):
                        console.print(f"[yellow]Entry {i}:[/yellow]")
                        console.print(f"  Flags: {entry.get_flags()}")
                        console.print(f"  Tag Seeks: {entry.tag_seek[:5]}... (showing first 5)")
                        console.print()
                    
                    if result.entry_count > 5:
                        console.print(f"[dim]... and {result.entry_count - 5} more entries[/dim]\n")
        else:
            result = rbdb.parse_tagfile(str(file_path))
            
            # Display header information
            table = Table(title=f"Tag File Header ({file_type})", show_header=False)
            table.add_column("Field", style="cyan", width=15)
            table.add_column("Value", style="magenta")
            
            table.add_row("Magic", f"0x{result.magic:08x}")
            table.add_row("Data Size", f"{result.datasize:,} bytes")
            table.add_row("Entry Count", str(result.entry_count))
            
            console.print(table)
            console.print()
            
            # Show sample entries if not in quiet mode
            if not args.quiet:
                if result.entry_count > 0:
                    console.print(f"[cyan]First {min(10, result.entry_count)} entries:[/cyan]\n")
                    entries_table = Table()
                    entries_table.add_column("Index", style="cyan", justify="right")
                    entries_table.add_column("ID", style="yellow", justify="right")
                    entries_table.add_column("Length", style="green", justify="right")
                    entries_table.add_column("Data", style="magenta")
                    
                    for i, entry in enumerate(result.entries[:10]):
                        # Decode data for display
                        try:
                            data_str = entry.data.split(b'\x00')[0].decode('utf-8', errors='replace')
                            if len(data_str) > 50:
                                data_str = data_str[:47] + "..."
                        except (AttributeError, UnicodeDecodeError, IndexError):
                            data_str = repr(entry.data[:50])
                        
                        entries_table.add_row(
                            str(i),
                            str(entry.idx_id),
                            str(entry.tag_length),
                            data_str
                        )
                    
                    console.print(entries_table)
                    console.print()
                    
                    if result.entry_count > 10:
                        console.print(f"[dim]... and {result.entry_count - 10} more entries[/dim]\n")
        
        # # Print full output if verbose mode
        # if args.verbose:
        #     console.print("[cyan]Full raw output:[/cyan]\n")
        #     console.print(str(result))
        
    except Exception as e:
        console.print(f"[red]Error parsing file: {e}[/red]")
        if logging.getLogger().level <= logging.DEBUG:
            console.print(traceback.format_exc())
        sys.exit(1)
