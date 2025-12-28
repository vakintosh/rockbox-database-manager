"""Watch command - Monitor music directory and auto-regenerate database."""

import argparse
import logging
import sys
import time
from pathlib import Path

from rich.console import Console
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from .generate import cmd_generate


class MusicDirectoryEventHandler(FileSystemEventHandler):
    """Event handler for music directory changes."""

    def __init__(self, music_path: Path, args: argparse.Namespace, console: Console):
        super().__init__()
        self.music_path = music_path
        self.args = args
        self.console = console
        self.pending_regeneration = False
        self.last_event_time: float = 0
        self.debounce_seconds = (
            2  # Wait 2 seconds after last change before regenerating
        )

    def should_process_file(self, path: str) -> bool:
        """Check if file is a music file that should trigger regeneration."""
        music_extensions = {
            ".mp3",
            ".flac",
            ".ogg",
            ".m4a",
            ".mp4",
            ".wma",
            ".wav",
            ".aac",
            ".opus",
        }
        path_obj = Path(path)
        return path_obj.suffix.lower() in music_extensions

    def on_any_event(self, event: FileSystemEvent) -> None:
        """Handle any file system event."""
        # Ignore directory events and non-music files
        if event.is_directory:
            return

        if not self.should_process_file(str(event.src_path)):
            return

        # Mark that we need to regenerate and update timestamp
        self.pending_regeneration = True
        self.last_event_time = time.time()

        event_type = event.event_type
        src_path_obj = Path(str(event.src_path))
        file_path = (
            src_path_obj.relative_to(self.music_path)
            if self.music_path in src_path_obj.parents
            else src_path_obj.name
        )

        if event_type == "created":
            self.console.print(f"[green]➕ File added:[/green] {file_path}")
        elif event_type == "modified":
            self.console.print(f"[yellow]📝 File modified:[/yellow] {file_path}")
        elif event_type == "deleted":
            self.console.print(f"[red]🗑️  File deleted:[/red] {file_path}")
        elif event_type == "moved":
            self.console.print(f"[blue]📦 File moved:[/blue] {file_path}")

    def should_regenerate(self) -> bool:
        """Check if enough time has passed since last event to trigger regeneration."""
        if not self.pending_regeneration:
            return False

        time_since_last_event = time.time() - self.last_event_time
        return time_since_last_event >= self.debounce_seconds


def cmd_watch(args: argparse.Namespace) -> None:
    """Watch music directory for changes and auto-regenerate database.

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

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = music_path / ".rockbox"

    console = Console()
    console.print("\n[bold cyan]🎵 Rockbox Database Manager - Watch Mode[/bold cyan]\n")
    console.print(f"[cyan]Watching:[/cyan] {music_path}")
    console.print(f"[cyan]Output:[/cyan] {output_path}")
    console.print("[dim]Press Ctrl+C to stop watching...[/dim]\n")

    # Perform initial database generation
    console.print(
        "[bold yellow]Performing initial database generation...[/bold yellow]\n"
    )

    # Temporarily modify args to pass to generate logic
    generate_args = argparse.Namespace(**vars(args))
    generate_args.music_path = str(music_path)
    generate_args.output = str(output_path)

    try:
        cmd_generate(generate_args)
        console.print("\n[green]✓[/green] Initial database generation complete\n")
        console.print("[bold cyan]👀 Now watching for changes...[/bold cyan]\n")
    except Exception as e:
        logging.error("Failed to generate initial database: %s", e)
        sys.exit(1)

    # Set up file system watcher
    event_handler = MusicDirectoryEventHandler(music_path, args, console)
    observer = Observer()
    observer.schedule(event_handler, str(music_path), recursive=True)
    observer.start()

    try:
        # Main watch loop
        while True:
            time.sleep(1)

            # Check if we should regenerate
            if event_handler.should_regenerate():
                event_handler.pending_regeneration = False
                console.print(
                    "\n[bold yellow]🔄 Changes detected, regenerating database...[/bold yellow]\n"
                )

                try:
                    cmd_generate(generate_args)
                    console.print(
                        "\n[green]✓[/green] Database regenerated successfully"
                    )
                    console.print(
                        "[bold cyan]👀 Continuing to watch for changes...[/bold cyan]\n"
                    )
                except Exception as e:
                    console.print(f"[red]✗ Error regenerating database: {e}[/red]")
                    logging.error("Database regeneration failed: %s", e, exc_info=True)
                    console.print(
                        "[bold cyan]👀 Continuing to watch for changes...[/bold cyan]\n"
                    )

    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping watch mode...[/yellow]")
        observer.stop()

    observer.join()
    console.print("[green]✓[/green] Watch mode stopped")
