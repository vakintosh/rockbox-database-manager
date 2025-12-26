"""Pytest configuration and fixtures."""

import sys
import os
import pytest

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def temp_music_dir(tmp_path):
    """Create a temporary directory with sample music files."""
    music_dir = tmp_path / "music"
    music_dir.mkdir()
    
    # Create subdirectories
    (music_dir / "Artist1" / "Album1").mkdir(parents=True)
    (music_dir / "Artist2" / "Album2").mkdir(parents=True)
    
    return music_dir


@pytest.fixture
def sample_tagfile():
    """Create a sample TagFile for testing."""
    from rockbox_db_manager.tagfile import TagFile, TagEntry
    
    tagfile = TagFile()
    tagfile.append(TagEntry("Artist 1"))
    tagfile.append(TagEntry("Artist 2"))
    tagfile.append(TagEntry("Artist 3"))
    
    return tagfile


@pytest.fixture
def sample_database():
    """Create a sample Database for testing."""
    from rockbox_db_manager.database import Database
    
    return Database()
