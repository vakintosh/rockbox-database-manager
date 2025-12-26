"""Tests for the CLI module."""

import pytest
from unittest.mock import patch

from rockbox_db_manager.cli import main, __version__, setup_logging


def test_version_output(capsys):
    """Test that --version flag displays version correctly."""
    with pytest.raises(SystemExit) as exc_info:
        with patch('sys.argv', ['rdbm', '--version']):
            main()
    
    # argparse exits with 0 for --version
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert __version__ in captured.out


def test_help_output(capsys):
    """Test that --help flag displays help information."""
    with pytest.raises(SystemExit) as exc_info:
        with patch('sys.argv', ['rdbm', '--help']):
            main()
    
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert 'Rockbox Database Manager' in captured.out
    assert 'generate' in captured.out
    assert 'load' in captured.out
    assert 'write' in captured.out


def test_no_command_shows_help(capsys):
    """Test that running without a command shows help."""
    with pytest.raises(SystemExit) as exc_info:
        with patch('sys.argv', ['rdbm']):
            main()
    
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert 'Rockbox Database Manager' in captured.out


def test_generate_help(capsys):
    """Test that generate command help works."""
    with pytest.raises(SystemExit) as exc_info:
        with patch('sys.argv', ['rdbm', 'generate', '--help']):
            main()
    
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert 'music_path' in captured.out
    assert '--output' in captured.out
    assert '--config' in captured.out
    assert '--load-tags' in captured.out
    assert '--save-tags' in captured.out


def test_load_help(capsys):
    """Test that load command help works."""
    with pytest.raises(SystemExit) as exc_info:
        with patch('sys.argv', ['rdbm', 'load', '--help']):
            main()
    
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert 'database_path' in captured.out


def test_write_help(capsys):
    """Test that write command help works."""
    with pytest.raises(SystemExit) as exc_info:
        with patch('sys.argv', ['rdbm', 'write', '--help']):
            main()
    
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert 'database_path' in captured.out
    assert 'output_path' in captured.out


def test_setup_logging_debug():
    """Test logging setup with debug level."""
    import logging
    # Reset logging to avoid interference from previous tests
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    setup_logging('debug')
    assert logging.getLogger().level == logging.DEBUG


def test_setup_logging_info():
    """Test logging setup with info level."""
    import logging
    # Reset logging to avoid interference from previous tests
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    setup_logging('info')
    assert logging.getLogger().level == logging.INFO


def test_setup_logging_warning():
    """Test logging setup with warning level."""
    import logging
    # Reset logging to avoid interference from previous tests
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    setup_logging('warning')
    assert logging.getLogger().level == logging.WARNING


def test_setup_logging_error():
    """Test logging setup with error level."""
    import logging
    # Reset logging to avoid interference from previous tests
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    setup_logging('error')
    assert logging.getLogger().level == logging.ERROR


def test_setup_logging_invalid():
    """Test that invalid log level raises ValueError."""
    with pytest.raises(ValueError):
        setup_logging('invalid')


def test_generate_missing_path(capsys):
    """Test generate command with non-existent path."""
    with pytest.raises(SystemExit) as exc_info:
        with patch('sys.argv', ['rdbm', 'generate', '/nonexistent/path']):
            main()
    
    assert exc_info.value.code == 1


def test_load_missing_path(capsys):
    """Test load command with non-existent path."""
    with pytest.raises(SystemExit) as exc_info:
        with patch('sys.argv', ['rdbm', 'load', '/nonexistent/path']):
            main()
    
    assert exc_info.value.code == 1


def test_inspect_help(capsys):
    """Test that inspect command help works."""
    with pytest.raises(SystemExit) as exc_info:
        with patch('sys.argv', ['rdbm', 'inspect', '--help']):
            main()
    
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert 'database_path' in captured.out
    assert 'file_number' in captured.out
    assert '--quiet' in captured.out
    assert '--verbose' in captured.out
    assert 'artist' in captured.out
    assert 'album' in captured.out


def test_inspect_missing_path(capsys):
    """Test inspect command with non-existent path."""
    with pytest.raises(SystemExit) as exc_info:
        with patch('sys.argv', ['rdbm', 'inspect', '/nonexistent/path']):
            main()
    
    assert exc_info.value.code == 1


def test_inspect_invalid_file_number(capsys, tmp_path):
    """Test inspect command with invalid file number."""
    # Create a temporary directory
    db_dir = tmp_path / "db"
    db_dir.mkdir()
    
    # Test with invalid file number (too high)
    with pytest.raises(SystemExit) as exc_info:
        with patch('sys.argv', ['rdbm', 'inspect', str(db_dir), '9']):
            main()
    
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert 'must be between 0 and 8' in captured.out or 'must be between 0 and 8' in captured.err


def test_inspect_missing_database_file(capsys, tmp_path):
    """Test inspect command when database file doesn't exist."""
    # Create a temporary directory without database files
    db_dir = tmp_path / "db"
    db_dir.mkdir()
    
    with pytest.raises(SystemExit) as exc_info:
        with patch('sys.argv', ['rdbm', 'inspect', str(db_dir)]):
            main()
    
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert 'not found' in output.lower() or 'does not exist' in output.lower()


def test_inspect_with_mock_database(tmp_path):
    """Test inspect command with a mock database file."""
    from rockbox_db_manager import rbdb
    import struct
    
    # Create a temporary database directory
    db_dir = tmp_path / "db"
    db_dir.mkdir()
    
    # Create a simple mock index file
    index_file = db_dir / "database_idx.tcd"
    with open(index_file, "wb") as f:
        # Write header: magic, datasize, entry_count, serial, commitid, dirty
        magic = rbdb.MAGIC
        datasize = 24  # Header size only
        entry_count = 0
        serial = 0
        commitid = 1
        dirty = 0
        f.write(struct.pack('IIIIII', magic, datasize, entry_count, serial, commitid, dirty))
    
    # Test inspect without error
    with patch('sys.argv', ['rdbm', 'inspect', str(db_dir)]):
        # Should not raise SystemExit for valid file
        try:
            main()
        except SystemExit as e:
            # Expect success (code 0) or no exit at all
            if e.code not in (0, None):
                pytest.fail(f"inspect command failed with exit code {e.code}")


def test_inspect_quiet_mode(tmp_path):
    """Test inspect command with --quiet flag."""
    from rockbox_db_manager import rbdb
    import struct
    
    db_dir = tmp_path / "db"
    db_dir.mkdir()
    
    # Create a mock tag file
    tag_file = db_dir / "database_0.tcd"
    with open(tag_file, "wb") as f:
        magic = rbdb.MAGIC
        datasize = 12  # Header only
        entry_count = 0
        f.write(struct.pack('III', magic, datasize, entry_count))
    
    # Test with quiet mode
    with patch('sys.argv', ['rdbm', 'inspect', str(db_dir), '0', '--quiet']):
        try:
            main()
        except SystemExit as e:
            if e.code not in (0, None):
                pytest.fail(f"inspect command with --quiet failed with exit code {e.code}")


def test_inspect_verbose_mode(tmp_path):
    """Test inspect command with --verbose flag."""
    from rockbox_db_manager import rbdb
    import struct
    
    db_dir = tmp_path / "db"
    db_dir.mkdir()
    
    # Create a mock tag file
    tag_file = db_dir / "database_0.tcd"
    with open(tag_file, "wb") as f:
        magic = rbdb.MAGIC
        datasize = 12  # Header only
        entry_count = 0
        f.write(struct.pack('III', magic, datasize, entry_count))
    
    # Test with verbose mode
    with patch('sys.argv', ['rdbm', 'inspect', str(db_dir), '0', '--verbose']):
        try:
            main()
        except SystemExit as e:
            if e.code not in (0, None):
                pytest.fail(f"inspect command with --verbose failed with exit code {e.code}")


def test_inspect_all_file_numbers(tmp_path):
    """Test inspect command with all valid file numbers (0-8)."""
    from rockbox_db_manager import rbdb
    import struct
    
    db_dir = tmp_path / "db"
    db_dir.mkdir()
    
    # Create mock database files for all 9 tag files
    for i in range(9):
        tag_file = db_dir / f"database_{i}.tcd"
        with open(tag_file, "wb") as f:
            magic = rbdb.MAGIC
            datasize = 12  # Header only
            entry_count = 0
            f.write(struct.pack('III', magic, datasize, entry_count))
    
    # Test each file number
    for i in range(9):
        with patch('sys.argv', ['rdbm', 'inspect', str(db_dir), str(i), '--quiet']):
            try:
                main()
            except SystemExit as e:
                if e.code not in (0, None):
                    pytest.fail(f"inspect command for file {i} failed with exit code {e.code}")
