# Rockbox Database Manager

A Python 3 application for managing Rockbox database files with a wxPython GUI.

## Status

⚠️ **Work in Progress** - This project is currently under active development.

**Testing**: This application has been tested on:
- macOS Sonoma 14.8.3 (23J220) - Intel Mac

Testing on other platforms (Linux, Windows, Apple Silicon Macs) is in progress.

**Test Coverage**: 23% with 38 tests passing (includes comprehensive CLI testing). See [tests/TEST_STATUS.md](tests/TEST_STATUS.md) for details.

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

### GUI Application

Run the graphical user interface:

```bash
# Using uv
uv run rockbox-db-manager-gui

# Or directly after installation
rockbox-db-manager-gui
```

### Command-Line Interface (`rdbm`)

The CLI provides silent mode operation without launching the GUI, perfect for automation and scripting.

#### Generate Database

```bash
# Generate database from music folder
rdbm generate /path/to/music

# Specify custom output location
rdbm generate /path/to/music -o /Volumes/IPOD/.rockbox

# Use configuration file (see Configuration section for details)
rdbm generate /path/to/music -c ~/.rdbm/.rdbm_config.toml

# Use tag cache for faster regeneration
rdbm generate /path/to/music --load-tags tags.cache --save-tags tags.cache

# Combine configuration and tag cache
rdbm generate /path/to/music -c ~/.rdbm/.rdbm_config.toml --load-tags ~/.rockbox_tags.cache
```

#### Load and Inspect Database

```bash
# Load existing database and show information
rdbm load /Volumes/IPOD/.rockbox

# With debug logging to see all entries
rdbm load /Volumes/IPOD/.rockbox --log-level debug
```

#### Copy Database

```bash
# Copy database to new location
rdbm write /Volumes/IPOD/.rockbox /backup/.rockbox
```

#### Inspect Database Files (Low-Level)

The `inspect` command provides low-level inspection of raw Rockbox database file structures. This is useful for debugging, understanding database internals, or verifying file integrity.

```bash
# Inspect index file (main database index)
rdbm inspect /Volumes/IPOD/.rockbox

# Inspect specific tag file by number (0-8)
rdbm inspect /Volumes/IPOD/.rockbox 0    # Artist database
rdbm inspect /Volumes/IPOD/.rockbox 3    # Title database
rdbm inspect /Volumes/IPOD/.rockbox 4    # Filename database

# Show only header information (no entries)
rdbm inspect /Volumes/IPOD/.rockbox 0 --quiet

# Show complete raw output with all details
rdbm inspect /Volumes/IPOD/.rockbox 3 --verbose

# With debug logging
rdbm inspect /Volumes/IPOD/.rockbox --log-level debug
```

**Database File Numbers:**
- `0` = artist
- `1` = album
- `2` = genre
- `3` = title
- `4` = filename
- `5` = composer
- `6` = comment
- `7` = albumartist
- `8` = grouping
- *(no number)* = index file

**Inspect Options:**
- `file_number`: Optional database file number (0-8). Omit to inspect the index file.
- `--quiet, -q`: Show only header information, suppress entry listing
- `--verbose, -v`: Show complete raw output including all internal data structures

This replaces the standalone `rbdb.py` script with an integrated CLI command that provides better formatting and error handling.

#### Validate Database

```bash
# Check database integrity and structure
rdbm validate /Volumes/IPOD/.rockbox
```

#### CLI Options

- `--version, -v`: Show version and exit
- `--log-level, -l`: Set logging level (debug, info, warning, error)
- `--help, -h`: Show help information

**Command-specific options:**

*Generate command:*
- `music_path`: Path to music folder (required)
- `-o, --output`: Output directory (default: music_path/.rockbox)
- `-c, --config`: Configuration file path
- `--load-tags`: Load tag cache file
- `--save-tags`: Save tag cache file

*Inspect command:*
- `database_path`: Path to database directory (required)
- `file_number`: Database file number 0-8 (optional, defaults to index file)
- `-q, --quiet`: Show only header, no entries
- `-v, --verbose`: Show complete raw output

*Validate command:*
- `database_path`: Path to database directory (required)

*Load/Write commands:*
- `database_path`: Path to database directory (required)
- `output_path`: Output directory (write command only)

**Examples:**

```bash
# Generate with verbose logging
rdbm generate /path/to/music --log-level debug

# Generate and save tags for next time
rdbm generate /path/to/music --save-tags ~/.rockbox_tags.cache

# Quick regeneration using cached tags
rdbm generate /path/to/music --load-tags ~/.rockbox_tags.cache

# Silent mode (errors only)
rdbm generate /path/to/music --log-level error

# Show version
rdbm --version

# Show help for all commands
rdbm --help
rdbm generate --help
rdbm inspect --help
rdbm validate --help

# Inspect database files for debugging
rdbm inspect /Volumes/IPOD/.rockbox           # Index file
rdbm inspect /Volumes/IPOD/.rockbox 0 -q      # Artist database (quiet mode)
rdbm inspect /Volumes/IPOD/.rockbox 3 -v      # Title database (verbose)

# Validate database integrity
rdbm validate /Volumes/IPOD/.rockbox
```

## Configuration

The Rockbox Database Manager supports customization through TOML configuration files. A comprehensive example configuration file is provided: [.rdbm_config_example.toml](.rdbm_config_example.toml)

### Quick Start

```bash
# Copy the example configuration
cp .rdbm_config_example.toml ~/.rdbm/.rdbm_config.toml

# Edit to customize for your needs
# Then use it with generate command
rdbm generate /path/to/music -c ~/.rdbm/.rdbm_config.toml
```

### Configuration Options

The configuration file supports:

- **Format Strings**: Customize how metadata is mapped to Rockbox database fields using foobar2000 titleformat syntax
- **Sort Formats**: Define custom sort orders (e.g., ignore "The" prefix in artist names)
- **Multiple-Value Tags**: Split multi-value tags (artists, genres) into separate database entries
- **Window Settings**: GUI window size and position (GUI only)
- **Path Settings**: Remember recently used directories

### Titleformat Syntax

Format strings use foobar2000 titleformat syntax for powerful tag manipulation:

```toml
[formats]
# Simple field reference
artist = "%artist%"

# Multiple-value tag (creates separate entries for each value)
genre = "%<genre>%"

# Conditional with fallback
artist = "$if2(%artist%,%composer%)"

# Include year in album name
album = "$if(%date%,%date% - ,)%album%"

[sort_formats]
# Remove leading "The", "A", "An" for sorting
artist = "$swapprefix(%artist%,The,A,An)"
```

### Example Configurations

The [.rdbm_config_example.toml](.rdbm_config_example.toml) file includes six complete examples:

1. **Classical Music** - Composer-focused with proper work grouping
2. **Multi-Genre Rock/Metal** - Multiple genres with name normalization
3. **Compilations & Soundtracks** - "Various Artists" handling
4. **Minimal/Clean** - Simple setup with article removal
5. **DJ/Electronic Music** - Emphasize remixers and labels
6. **Maximum Compatibility** - Safe defaults for all collections

### Important Notes

- **Multiple-value tags** (`%<field>%`) create combinatorial entries. A song with 2 artists and 2 genres = 4 index entries.
- **Test first**: Test format strings on a small music subset before processing your full collection.
- **Regenerate required**: After changing formats, delete and regenerate the database.
- **Tag cache**: Use `--save-tags` and `--load-tags` for faster regeneration on large collections.

For complete titleformat documentation, see: [Foobar2000 Titleformat Reference](http://wiki.hydrogenaudio.org/index.php?title=Foobar2000:Titleformat_Reference)

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

- **38 unit tests** covering core functionality (30 baseline + 8 new CLI tests)
- **23% code coverage** maintained
- Tests for database operations, tag files, index files, CLI commands, and utilities
- Coverage reports generated in `htmlcov/`

**Run tests:**
```bash
# All tests
uv run pytest -v

# Specific test file
uv run pytest tests/test_cli.py -v

# With coverage report
uv run pytest --cov=src/rockbox_db_manager --cov-report=html -v

# Code quality checks
uv run ruff check src/ tests/
```

See [tests/README.md](tests/README.md) for more details on running and writing tests.

## Project Structure

```
rockbox-db-manager/
├── src/rockbox_db_manager/    # Main application package
│   ├── cli.py                  # Command-line interface (rdbm)
│   ├── gui.py                  # GUI application
│   ├── database.py             # Database operations
│   ├── indexfile.py            # Index file handling
│   ├── tagfile.py              # Tag file handling
│   ├── rbdb.py                 # Rockbox DB parsing (BSD license)
│   ├── rblib.py                # Rockbox library functions
│   ├── config.py               # Configuration management
│   └── tagging/                # Audio tag reading
├── tests/                      # Test suite
│   ├── test_cli.py             # CLI command tests
│   ├── test_database.py        # Database operation tests
│   ├── test_indexfile.py       # Index file tests
│   ├── test_tagfile.py         # Tag file tests
│   └── test_utils.py           # Utility function tests
├── .rdbm_config_example.toml   # Example configuration file
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
- **Modern CLI** with rich formatting and comprehensive commands
- **UV project structure** with proper packaging
- **Framework-enabled Python** support for macOS
- Updated dependencies (mutagen 1.47+, wxPython 4.2.4+, rich for CLI output)
- Cross-platform path handling improvements
- Comprehensive test suite with pytest (38 tests)
- Type hints and modern Python practices
- Memory leak fixes and proper resource management
- Code quality enforcement with ruff

### Third-Party Components

The [`rbdb.py`](src/rockbox_db_manager/rbdb.py) module is Copyright 2008, **Aren Olson** (reacocard@gmail.com), distributed under a BSD-style license (see file header for details). This module is now integrated into the CLI via the `rdbm inspect` command, providing better formatting and error handling than the standalone script.

## Contributing

Contributions are welcome! Please ensure:
- All tests pass (`uv run pytest`)
- Code passes linting (`uv run ruff check src/ tests/`)
- New features include tests
- Code follows existing style conventions
- Coverage remains at or above baseline (23%)

## License

- Main project: GPL v2 or later
- `rbdb.py`: BSD-style license (see file header for details)

See [LICENSE](LICENSE) for full license text.
