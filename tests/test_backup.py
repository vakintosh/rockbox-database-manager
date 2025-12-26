"""Tests for backup functionality."""

import tarfile
from pathlib import Path

import pytest

from rockbox_db_manager.backup import BackupManager, create_backup


@pytest.fixture
def temp_music_dir(tmp_path):
    """Create a temporary music directory with test files."""
    music_dir = tmp_path / "music"
    music_dir.mkdir()

    # Create some test files
    (music_dir / "song1.mp3").write_text("fake mp3 data 1")
    (music_dir / "song2.mp3").write_text("fake mp3 data 2")

    # Create subdirectory with files
    subdir = music_dir / "album"
    subdir.mkdir()
    (subdir / "track1.mp3").write_text("fake track 1")
    (subdir / "track2.mp3").write_text("fake track 2")

    return music_dir


@pytest.fixture
def temp_backup_dir(tmp_path):
    """Create a temporary backup directory."""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    return backup_dir


class TestBackupManager:
    """Test BackupManager class."""

    def test_create_backup_success(self, temp_music_dir, temp_backup_dir):
        """Test successful backup creation."""
        manager = BackupManager(str(temp_backup_dir))

        backup_path = manager.create_backup(str(temp_music_dir))

        assert backup_path is not None
        assert Path(backup_path).exists()
        assert Path(backup_path).suffix == ".xz"
        assert "rockbox_backup_" in Path(backup_path).name

    def test_create_backup_with_callback(self, temp_music_dir, temp_backup_dir):
        """Test backup creation with callback."""
        manager = BackupManager(str(temp_backup_dir))
        messages = []

        def callback(msg):
            messages.append(msg)

        backup_path = manager.create_backup(
            str(temp_music_dir), callback=callback, max_backups=3
        )

        assert backup_path is not None
        assert len(messages) > 0
        assert any("Backing up" in str(msg) for msg in messages)

    def test_create_backup_nonexistent_path(self, temp_backup_dir):
        """Test backup creation with nonexistent music path."""
        manager = BackupManager(str(temp_backup_dir))

        backup_path = manager.create_backup("/nonexistent/path")

        assert backup_path is None

    def test_create_backup_file_not_dir(self, tmp_path, temp_backup_dir):
        """Test backup creation when path is a file, not directory."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        manager = BackupManager(str(temp_backup_dir))
        backup_path = manager.create_backup(str(test_file))

        assert backup_path is None

    def test_backup_contains_files(self, temp_music_dir, temp_backup_dir):
        """Test that backup archive contains the expected files."""
        manager = BackupManager(str(temp_backup_dir))

        backup_path = manager.create_backup(str(temp_music_dir))
        assert backup_path is not None

        # Verify archive contents
        with tarfile.open(backup_path, "r:xz") as tar:
            names = tar.getnames()
            assert any("song1.mp3" in name for name in names)
            assert any("song2.mp3" in name for name in names)
            assert any("track1.mp3" in name for name in names)

    def test_cleanup_old_backups(self, temp_music_dir, temp_backup_dir):
        """Test that old backups are cleaned up."""
        import time

        manager = BackupManager(str(temp_backup_dir))

        # Create multiple backups
        backups = []
        for i in range(7):
            backup_path = manager.create_backup(
                str(temp_music_dir), max_backups=3, skip_window_minutes=0
            )
            if backup_path:
                backups.append(Path(backup_path))
            # Small delay to ensure different timestamps
            time.sleep(0.1)

        # Should only have 3 backups
        remaining = list(temp_backup_dir.glob("rockbox_backup_*.tar.xz"))
        assert len(remaining) == 3

    def test_list_backups(self, temp_music_dir, temp_backup_dir):
        """Test listing available backups."""
        import time

        manager = BackupManager(str(temp_backup_dir))

        # Create a few backups (skip_window_minutes=0 to disable skipping)
        manager.create_backup(
            str(temp_music_dir), max_backups=10, skip_window_minutes=0
        )
        time.sleep(0.1)  # Ensure different timestamps
        manager.create_backup(
            str(temp_music_dir), max_backups=10, skip_window_minutes=0
        )

        backups = manager.list_backups(str(temp_backup_dir))

        assert len(backups) >= 2
        assert all("path" in b for b in backups)
        assert all("timestamp" in b for b in backups)
        assert all("size" in b for b in backups)

    def test_restore_backup(self, temp_music_dir, temp_backup_dir, tmp_path):
        """Test restoring a backup."""
        manager = BackupManager(str(temp_backup_dir))

        # Create backup
        backup_path = manager.create_backup(str(temp_music_dir))
        assert backup_path is not None

        # Restore to new location
        restore_dir = tmp_path / "restored"
        success = manager.restore_backup(backup_path, str(restore_dir))

        assert success is True
        assert restore_dir.exists()

        # Check that files were restored
        music_name = temp_music_dir.name
        restored_music = restore_dir / music_name
        assert (restored_music / "song1.mp3").exists()
        assert (restored_music / "album" / "track1.mp3").exists()

    def test_restore_nonexistent_backup(self, temp_backup_dir, tmp_path):
        """Test restoring a nonexistent backup."""
        manager = BackupManager(str(temp_backup_dir))

        restore_dir = tmp_path / "restored"
        success = manager.restore_backup("/nonexistent/backup.tar.xz", str(restore_dir))

        assert success is False

    def test_default_backup_dir(self, temp_music_dir):
        """Test backup with default directory."""
        manager = BackupManager()  # No backup_dir specified

        backup_path = manager.create_backup(str(temp_music_dir))

        assert backup_path is not None
        # Default location should be in parent of music folder
        expected_dir = temp_music_dir.parent / ".rockbox_backups"
        assert expected_dir.exists()
        assert str(expected_dir) in backup_path


class TestConvenienceFunction:
    """Test convenience function."""

    def test_create_backup_function(self, temp_music_dir, temp_backup_dir):
        """Test the convenience create_backup function."""
        backup_path = create_backup(
            str(temp_music_dir), backup_dir=str(temp_backup_dir), max_backups=5
        )

        assert backup_path is not None
        assert Path(backup_path).exists()
