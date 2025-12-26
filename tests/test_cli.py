"""Tests for the CLI module."""

import sys
from io import StringIO
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

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
