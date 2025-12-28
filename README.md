Collecting workspace information# Rockbox Database Manager

A modern Python 3.11+ application for managing Rockbox database files with both GUI and CLI interfaces. Generate, inspect, validate, and manipulate Rockbox database files from your music collection.

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-GPL%20v2-blue.svg)](LICENSE)
[![Test Coverage](https://img.shields.io/badge/coverage-29%25-yellow.svg)](tests/TEST_STATUS.md)
[![Tests](https://img.shields.io/badge/tests-30%2F30%20passing-green.svg)](tests/TEST_STATUS.md)

---

## 📋 Table of Contents

- Features
- Status
- Requirements
- Installation
- Quick Start
- Usage
  - Command-Line Interface (CLI)
  - GUI Application
- Configuration
- Testing
- Project Structure
- Platform Notes
- Contributing
- Credits & History
- License

---

## ✨ Features

- **Generate Rockbox databases** from audio file metadata
- **Support for multiple formats**: MP3, FLAC, MP4, Ogg Vorbis, WMA, and more
- **Multiprocessing tag parsing** - bypasses Python GIL for true parallel execution (4-15x faster on multi-core systems)
- **Persistent thread/process pools** - reused across operations for optimal performance
- **Memory-based tag caching** with auto-detection based on available RAM
- **Customizable titleformat strings** (foobar2000 syntax) for organizing music
- **Tag caching** for faster database regeneration on large collections
- **CLI commands**:
  - `generate` - Create database from music folder
  - `load` - Display existing database information
  - `validate` - Check database integrity
  - `inspect` - Low-level file inspection using modern implementation
  - `write` - Copy database to new location
- **Modern wxPython Phoenix GUI** with intuitive interface
  - Async I/O support to prevent blocking
  - Cancellable operations
  - Real-time progress tracking

---

## Status

**Work in Progress** - Under active development

**Tested on:**
- ✅ macOS Sonoma 14.8.3 (Intel Mac)
- ✅ maOS Tahoe 26.1 (Apple Silicon Macs)
- 🔄 Linux (in progress)
- 🔄 Windows (in progress)

---

## Requirements

- **Python**: 3.11 or higher
- **wxPython**: 4.2.4 or higher (requires framework-enabled Python on macOS)
- **mutagen**: 1.47.0 or higher
- **rich**: 13.0.0 or higher (for CLI formatting)
- **watchdog**: 3.0.0 or higher (for file monitoring)

---

## Installation

### Using UV (Recommended)

```bash
# Clone the repository
git clone https://github.com/vakintosh/rockbox-db-manager.git
cd rockbox-db-manager

# Sync dependencies (creates virtual environment automatically)
uv sync

# Run the CLI
uv run rdbm --help

# Run the GUI
uv run rockbox-db-manager
```

### Using pip

```bash
# Clone the repository
git clone https://github.com/vakintosh/rockbox-db-manager.git
cd rockbox-db-manager

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Run the CLI
rdbm --help

# Run the GUI
rockbox-db-manager-gui
```

---

## Quick Start

### Generate a Database

```bash
# Basic generation
rdbm generate /path/to/music

# With custom output location
rdbm generate /path/to/music -o /Volumes/IPOD/.rockbox

# Using configuration file
rdbm generate /path/to/music -c ~/.rdbm/.rdbm_config.toml

# With tag caching for faster regeneration
rdbm generate /path/to/music --save-tags ~/.rockbox_tags.cache

# Quick regeneration using cached tags
rdbm generate /path/to/music --load-tags ~/.rockbox_tags.cache.gz
```

### Inspect a Database

```bash
# Inspect index file
rdbm inspect /Volumes/IPOD/.rockbox

# Inspect artist database (file 0)
rdbm inspect /Volumes/IPOD/.rockbox 0

# Quiet mode (header only)
rdbm inspect /Volumes/IPOD/.rockbox 1 --quiet
```

### Validate Database Integrity

```bash
rdbm validate /Volumes/IPOD/.rockbox
```

---

## Usage

### Command-Line Interface (CLI)

The `rdbm` command provides comprehensive database management:

#### 1. Generate Database

Create Rockbox database files from a music folder:

```bash
# Basic usage
rdbm generate /path/to/music

# All options
rdbm generate /path/to/music \
  --output /Volumes/IPOD/.rockbox \
  --config ~/.rdbm/.rdbm_config.toml \
  --load-tags ~/.rockbox_tags.cache \
  --save-tags ~/.rockbox_tags.cache \
  --log-level debug
```

**Options:**
- `music_path` - Path to music folder (required)
- `-o, --output` - Output directory (default: `music_path/.rockbox`)
- `-c, --config` - Configuration file path (default: `~/.rdbm/.rdbm_config.toml`)
- `--load-tags` - Load tag cache file for faster generation
- `--save-tags` - Save tag cache file for future use
- `-l, --log-level` - Logging level: debug, info, warning, error (default: info)

**Example Output:**

```
Scanning music folder...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 1234/1234 files
✓ Generated 1234 database entries

Writing database files...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10/10 files
✓ Database generation complete

      Database Summary
┏━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Field  ┃ Value                      ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Input  │ /path/to/music             │
│ Output │ /path/to/music/.rockbox    │
│ Files  │ 1234                       │
│ Entries│ 1234                       │
│ Failed │ 0                          │
└────────┴────────────────────────────┘
```

#### 2. Load and Display Database

View information about an existing database:

```bash
# Basic load
rdbm load /Volumes/IPOD/.rockbox

# With detailed logging
rdbm load /Volumes/IPOD/.rockbox --log-level debug
```

**Example Output:**

```
Database Information:
  Location: /Volumes/IPOD/.rockbox
  Entries:  1234

Tag Files:
  artist      :    456 entries
  album       :    234 entries
  genre       :     12 entries
  title       :   1234 entries
  filename    :   1234 entries
  composer    :     89 entries
  comment     :      0 entries
  albumartist :    234 entries
  grouping    :   1234 entries

Sample Entries (first 10):
  1. /Music/Artist/Album/01 Track.mp3
  2. /Music/Artist/Album/02 Track.mp3
  ...
```

#### 3. Validate Database

Check database integrity and structure:

```bash
rdbm validate /Volumes/IPOD/.rockbox
```

**Example Output:**

```
Validating database: /Volumes/IPOD/.rockbox

✓ All database files present
✓ Database loaded successfully
✓ All references valid
✓ Index entry count matches

Validation Summary
┏━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Status  ┃ Result                    ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Files   │ ✓ All present (10/10)     │
│ Loading │ ✓ Success                 │
│ Entries │ ✓ 1234 entries validated  │
│ Issues  │ None                      │
└─────────┴───────────────────────────┘
```

#### 4. Inspect Database Files (Low-Level)

Parse and display raw database file contents:

```bash
# Inspect index file
rdbm inspect /Volumes/IPOD/.rockbox

# Inspect specific tag file (0-8)
rdbm inspect /Volumes/IPOD/.rockbox 3

# Quiet mode (header only, no entries)
rdbm inspect /Volumes/IPOD/.rockbox 0 --quiet

# Verbose mode (complete raw output)
rdbm inspect /Volumes/IPOD/.rockbox 3 --verbose
```

**Database File Numbers:**
- `0` - artist
- `1` - album
- `2` - genre
- `3` - title
- `4` - filename
- `5` - composer
- `6` - comment
- `7` - albumartist
- `8` - grouping
- *(no number)* - index file

**Example Output:**

```
Reading database file: /Volumes/IPOD/.rockbox/database_0.tcd
File type: artist
File size: 12,345 bytes

   Tag File Header (artist)
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ Field       ┃ Value               ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ Magic       │ 0x52444244          │
│ Data Size   │ 12,345 bytes        │
│ Entry Count │ 456                 │
└─────────────┴─────────────────────┘

First 10 entries:
┏━━━━━━┳━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Index┃ ID   ┃ Length ┃ Data             ┃
┡━━━━━━╇━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ 0    │ 0    │ 12     │ The Beatles      │
│ 1    │ 1    │ 15     │ Led Zeppelin     │
│ 2    │ 2    │ 9      │ Pink Floyd       │
...
```

#### 5. Copy Database

Copy database files to a new location:

```bash
rdbm write /Volumes/IPOD/.rockbox /backup/.rockbox
```

#### 6. Get Help

```bash
# General help
rdbm --help

# Command-specific help
rdbm generate --help
rdbm inspect --help
rdbm validate --help

# Version information
rdbm --version
```

### GUI Application

Launch the graphical interface:

```bash
# Using UV
uv run rockbox-db-manager

# Or if installed
rockbox-db-manager
```

**GUI Features:**
- Visual music folder selection
- Progress tracking with progress bars
- Database inspection and validation
- Configuration editing
- Cross-platform file dialogs

---

## Configuration

### Configuration File

The application uses TOML configuration files for customization. A comprehensive example is provided: .rdbm_config_example.toml

**Default locations:**
- Linux/macOS: `~/.rdbm/.rdbm_config.toml`
- Windows: `%USERPROFILE%\.rdbm\.rdbm_config.toml`

**Custom location:**
```bash
rdbm generate /path/to/music -c /path/to/custom_config.toml
```

### Quick Setup

```bash
# Copy example configuration
cp .rdbm_config_example.toml ~/.rdbm/.rdbm_config.toml

# Edit for your needs
nano ~/.rdbm/.rdbm_config.toml

# Use with generate
rdbm generate /path/to/music -c ~/.rdbm/.rdbm_config.toml
```

### Configuration Options

See [.rdbm_config_example.toml](.rdbm_config_example.toml)

For complete titleformat documentation, see: [Foobar2000 Titleformat Reference](http://wiki.hydrogenaudio.org/index.php?title=Foobar2000:Titleformat_Reference)

---

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest -v

# Run with coverage report
uv run pytest --cov=src/rockbox_db_manager --cov-report=html -v

# Run specific test file
uv run pytest tests/test_cli.py -v

# Run specific test
uv run pytest tests/test_tagfile.py::TestTagFile::test_tagfile_creation -v

# View HTML coverage report
open htmlcov/index.html
```

### Code Quality

```bash
# Run linter
uv run ruff check src/ tests/

# Run type checker
uv run mypy src/

# Format code
uv run ruff format src/ tests/
```



## Contributing

Contributions are welcome! Please ensure:

1. **All tests pass:**
   ```bash
   uv run pytest
   ```

2. **Code passes linting:**
   ```bash
   uv run ruff check src/ tests/
   ```

3. **New features include tests**

4. **Code follows existing style conventions**

### Development Setup

```bash
# Clone repository
git clone https://github.com/vakintosh/rockbox-db-manager.git
cd rockbox-db-manager

# Install with dev dependencies
uv sync --group dev

# Run tests
uv run pytest -v

# Run linter
uv run ruff check src/ tests/

# Run type checker
uv run mypy src/
```

---

## License

GPL v2 or later

See LICENSE for full license text.

---

## Additional Resources

- [Rockbox Official Website](https://www.rockbox.org/)
- [Rockbox Database Format](https://www.rockbox.org/wiki/DataBase)
- [Foobar2000 Titleformat Reference](http://wiki.hydrogenaudio.org/index.php?title=Foobar2000:Titleformat_Reference)
- [mutagen Documentation](https://mutagen.readthedocs.io/)
- [wxPython Documentation](https://docs.wxpython.org/)

---

## Known Issues

- GUI testing requires manual verification (0% automated coverage)
- Some titleformat functions not yet fully implemented
- Watch command disabled pending further testing

See [GitHub Issues](https://github.com/yourusername/rockbox-db-manager/issues) for complete list and updates.

---

**Enjoy managing your Rockbox databases! 🎵**