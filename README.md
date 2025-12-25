# Rockbox Database Manager

A Python 3 application for managing Rockbox database files with a wxPython GUI.

## Features

- Generate Rockbox database files from audio file metadata
- Support for multiple audio formats (MP3, FLAC, MP4, Ogg Vorbis, etc.)
- Customizable titleformat strings for organizing music
- Cross-platform support (macOS, Linux, Windows)
- Modern wxPython Phoenix GUI

## Requirements

- Python 3.11 or higher
- wxPython 4.2.4 or higher (requires framework-enabled Python on macOS)
- mutagen 1.47.0 or higher

## Installation

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

## Usage

Run the GUI application:

```bash
# Using uv
uv run rockbox-db-manager

# Or directly after installation
rockbox-db-manager-gui
```

## Development

This project uses `uv` for package management. To set up a development environment:

```bash
# Clone and enter the repository
cd rockbox-db-manager

# Sync dependencies (creates venv automatically)
uv sync

# Run the application
uv run rockbox-db-manager
```

## Platform Notes

See [PLATFORM_NOTES.md](PLATFORM_NOTES.md) for platform-specific setup instructions, especially for macOS which requires framework-enabled Python for wxPython GUI support.

## License

GPL v2 or later
