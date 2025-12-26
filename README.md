# Rockbox Database Manager

A Python 3 application for managing Rockbox database files with a wxPython GUI.

## Status

⚠️ **Work in Progress** - This project is currently under active development.

**Testing**: This application has been tested on:
- macOS Sonoma 14.8.3 (23J220) - Intel Mac

Testing on other platforms (Linux, Windows, Apple Silicon Macs) is in progress.

**Test Coverage**: 29% baseline established with 30/30 tests passing. See [tests/TEST_STATUS.md](tests/TEST_STATUS.md) for details.

## Features

- Generate Rockbox database files from audio file metadata
- Support for multiple audio formats (MP3, FLAC, MP4, Ogg Vorbis, etc.)
- Customizable titleformat strings for organizing music
- Cross-platform support (macOS, Linux, Windows)
- Modern wxPython Phoenix GUI
- Comprehensive test suite with pytest

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

# Run tests
uv run pytest -v

# Run tests with coverage
uv run pytest --cov=src/rockbox_db_manager --cov-report=html -v

# View coverage report
open htmlcov/index.html
```

## Testing

The project includes a comprehensive test suite:

- **30 unit tests** covering core functionality
- **29% code coverage** (baseline established)
- Tests for database operations, tag files, index files, and utilities
- Coverage reports generated in `htmlcov/`

See [tests/README.md](tests/README.md) for more details on running and writing tests.

## Project Structure

```
rockbox-db-manager/
├── src/rockbox_db_manager/    # Main application package
│   ├── gui.py                  # GUI application
│   ├── database.py             # Database operations
│   ├── indexfile.py            # Index file handling
│   ├── tagfile.py              # Tag file handling
│   ├── rbdb.py                 # Rockbox DB parsing (BSD license)
│   ├── rblib.py                # Rockbox library functions
│   └── tagging/                # Audio tag reading
├── tests/                      # Test suite
│   ├── test_database.py
│   ├── test_indexfile.py
│   ├── test_tagfile.py
│   └── test_utils.py
├── pyproject.toml              # Project configuration
└── README.md                   # This file
```

## Platform Notes

See [PLATFORM_NOTES.md](PLATFORM_NOTES.md) for platform-specific setup instructions, especially for macOS which requires framework-enabled Python for wxPython GUI support.

## Credits & History

This is a modernized Python 3.11+ version of the **Rockbox Database Manager**, originally created by **Mike Richards** (mrichards24@gmx.com) in 2009. The original project provided a GUI tool for manipulating Rockbox databases with custom tag mapping and sorting capabilities.

### Original Project

The original Rockbox Database Manager (version dated 12/10/09) was written for Python 2.5/2.6 and included:
- User-defined database tag mapping using foobar2000 titleformat syntax
- Multiple value tag support
- wxPython GUI for database management
- Full documentation available in [README.txt](README.txt) and [README_src.txt](README_src.txt)

### This Version (2025)

This repository represents a complete migration and modernization effort:
- **Python 3.11+** compatibility (from Python 2.5/2.6)
- **wxPython Phoenix** (4.x) migration (from wxPython Classic)
- **UV project structure** with proper packaging
- **Framework-enabled Python** support for macOS
- Updated dependencies (mutagen 1.47+, wxPython 4.2.4+)
- Cross-platform path handling improvements
- Comprehensive test suite with pytest
- Type hints and modern Python practices

### Third-Party Components

The [`rbdb.py`](src/rockbox_db_manager/rbdb.py) module is Copyright 2008, **Aren Olson** (reacocard@gmail.com), distributed under a BSD-style license (see file header for details).

## Contributing

Contributions are welcome! Please ensure:
- All tests pass (`uv run pytest`)
- New features include tests
- Code follows existing style conventions
- Coverage remains at or above baseline (29%)

## License

- Main project: GPL v2 or later
- `rbdb.py`: BSD-style license (see file header for details)

See [LICENSE](LICENSE) for full license text.
