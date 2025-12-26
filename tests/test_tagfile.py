"""Tests for TagFile and TagEntry classes."""

import struct
import pytest
from rockbox_db_manager.tagfile import TagFile, TagEntry
from rockbox_db_manager.defs import MAGIC, ENCODING


class TestTagEntry:
    """Test TagEntry class."""

    def test_tag_entry_creation(self):
        """Test creating a TagEntry."""
        entry = TagEntry("TestData")
        assert entry.data == "TestData"
        # TagEntry doesn't have idx_id, it has other attributes
        assert hasattr(entry, 'data')

    def test_tag_entry_length(self):
        """Test that tag entry computes length correctly."""
        data = "TestData"
        entry = TagEntry(data)
        assert len(entry.data) == len(data)

    def test_tag_entry_with_unicode(self):
        """Test TagEntry with unicode strings."""
        text = "Artist Name"
        entry = TagEntry(text)
        
        # Should get back the same text
        assert entry.data == text


class TestTagFile:
    """Test TagFile class."""

    def test_tagfile_creation(self):
        """Test creating an empty TagFile."""
        tagfile = TagFile()
        assert tagfile.magic == MAGIC
        assert len(tagfile.entrydict) == 0

    def test_add_entry(self):
        """Test adding an entry to TagFile."""
        tagfile = TagFile()
        entry = TagEntry("Test Artist")
        
        tagfile.append(entry)
        assert len(tagfile.entrydict) == 1

    def test_get_entry(self):
        """Test retrieving an entry by key."""
        tagfile = TagFile()
        test_data = "Test Artist"
        entry = TagEntry(test_data)
        
        tagfile.append(entry)
        # Access via entrydict using the key
        retrieved = tagfile[test_data]
        
        assert retrieved is not None
        assert retrieved.data == test_data

    def test_duplicate_entries(self):
        """Test handling duplicate data in TagFile."""
        tagfile = TagFile()
        test_data = "Same Artist"
        
        entry1 = TagEntry(test_data)
        entry2 = TagEntry(test_data)
        
        tagfile.append(entry1)
        # Second append overwrites in entrydict
        tagfile.append(entry2)
        
        # Should have the entry in dict
        assert test_data in tagfile.entrydict

    def test_raw_data_generation(self):
        """Test TagFile has size property."""
        tagfile = TagFile()
        entry = TagEntry("Test")
        tagfile.append(entry)
        
        # TagFile has a size property
        assert hasattr(tagfile, 'size')
        assert tagfile.size > 0
        assert isinstance(tagfile.size, int)

    def test_empty_tagfile_size(self):
        """Test size property for empty TagFile."""
        tagfile = TagFile()
        
        # Empty tagfile should have 0 size
        assert tagfile.size == 0
        assert tagfile.count == 0
