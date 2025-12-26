"""Backup utilities for Rockbox Database Manager.

This module provides functionality to backup the music folder before write operations
to protect against data loss.
"""

import tarfile
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, List


logger = logging.getLogger(__name__)


class BackupManager:
    """Manages backups of the music folder."""

    def __init__(self, backup_dir: Optional[str] = None):
        """Initialize backup manager.

        Args:
            backup_dir: Directory to store backups. If None, uses a default location.
        """
        self.backup_dir = backup_dir

    def create_backup(
        self,
        music_path: str,
        callback: Optional[Callable] = None,
        max_backups: int = 5,
        skip_window_minutes: int = 5,
    ) -> Optional[str]:
        """Create a compressed backup of the music folder.

        Args:
            music_path: Path to the music folder to backup
            callback: Optional callback function for progress updates
            max_backups: Maximum number of backups to keep (older ones will be deleted)
            skip_window_minutes: Skip creating backup if one exists within this many minutes (0 = always create)

        Returns:
            Path to the created backup file, or None if backup failed or was skipped
        """
        music_path = Path(music_path).resolve()

        if not music_path.exists():
            logger.error(f"Music path does not exist: {music_path}")
            return None

        if not music_path.is_dir():
            logger.error(f"Music path is not a directory: {music_path}")
            return None

        # Determine backup directory
        if self.backup_dir:
            backup_dir = Path(self.backup_dir)
        else:
            # Default: create .rockbox_backups in parent directory of music folder
            backup_dir = music_path.parent / ".rockbox_backups"

        # Create backup directory if it doesn't exist
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create backup directory: {e}")
            return None

        # Check if a recent backup exists within the skip window
        if skip_window_minutes > 0:
            existing_backups = sorted(
                backup_dir.glob("rockbox_backup_*.tar.xz"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if existing_backups:
                most_recent = existing_backups[0]
                time_since_backup = (
                    datetime.now().timestamp() - most_recent.stat().st_mtime
                )
                minutes_since_backup = time_since_backup / 60

                if minutes_since_backup < skip_window_minutes:
                    logger.info(
                        f"Skipping backup - recent backup exists from {minutes_since_backup:.1f} minutes ago: {most_recent.name}"
                    )
                    if callback:
                        callback(
                            f"Skipping backup - recent backup from {minutes_since_backup:.1f} min ago"
                        )
                    return str(most_recent)  # Return existing backup path

        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[
            :19
        ]  # Include microseconds (6 digits)
        backup_name = f"rockbox_backup_{timestamp}.tar.xz"
        backup_path = backup_dir / backup_name

        if callback:
            callback(f"Creating backup: {backup_name}")

        logger.info(f"Creating backup of {music_path} to {backup_path}")

        try:
            # Create compressed tar archive with maximum compression
            with tarfile.open(backup_path, "w:xz", preset=9) as tar:
                # Add progress callback if provided
                if callback:
                    # Count files first for progress reporting
                    file_count = sum(1 for _ in music_path.rglob("*") if _.is_file())
                    callback(f"Backing up {file_count} files...")

                    processed = 0

                    def filter_func(tarinfo):
                        nonlocal processed
                        processed += 1
                        if callback and processed % 100 == 0:
                            callback(f"Backed up {processed}/{file_count} files")
                        return tarinfo

                    tar.add(music_path, arcname=music_path.name, filter=filter_func)
                else:
                    tar.add(music_path, arcname=music_path.name)

            logger.info(f"Backup created successfully: {backup_path}")

            if callback:
                backup_size = backup_path.stat().st_size / (1024 * 1024)  # MB
                callback(f"Backup complete: {backup_name} ({backup_size:.2f} MB)")

            # Clean up old backups
            self.cleanup_old_backups(backup_dir, max_backups, callback)

            return str(backup_path)

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            if callback:
                callback(f"Backup failed: {e}")

            # Clean up partial backup file
            if backup_path.exists():
                try:
                    backup_path.unlink()
                except OSError:
                    pass

            return None

    def cleanup_old_backups(
        self, backup_dir: Path, max_backups: int, callback: Optional[Callable] = None
    ) -> None:
        """Remove old backups, keeping only the most recent ones.

        Args:
            backup_dir: Directory containing backups
            max_backups: Maximum number of backups to keep
            callback: Optional callback function for progress updates
        """
        if not backup_dir.exists():
            return

        # Find all backup files
        backups = sorted(
            backup_dir.glob("rockbox_backup_*.tar.xz"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        # Remove old backups
        if len(backups) > max_backups:
            for old_backup in backups[max_backups:]:
                logger.info(f"Removing old backup: {old_backup.name}")
                if callback:
                    callback(f"Removing old backup: {old_backup.name}")
                try:
                    old_backup.unlink()
                except Exception as e:
                    logger.warning(f"Failed to remove old backup {old_backup}: {e}")

    def list_backups(self, backup_dir: Optional[str] = None) -> List[dict]:
        """List all available backups.

        Args:
            backup_dir: Directory containing backups. If None, uses default location.

        Returns:
            List of dictionaries with backup information (path, timestamp, size)
        """
        if backup_dir:
            backup_path = Path(backup_dir)
        elif self.backup_dir:
            backup_path = Path(self.backup_dir)
        else:
            return []

        if not backup_path.exists():
            return []

        backups = []
        for backup_file in sorted(
            backup_path.glob("rockbox_backup_*.tar.xz"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ):
            stat = backup_file.stat()
            backups.append(
                {
                    "path": str(backup_file),
                    "name": backup_file.name,
                    "timestamp": datetime.fromtimestamp(stat.st_mtime),
                    "size": stat.st_size,
                    "size_mb": stat.st_size / (1024 * 1024),
                }
            )

        return backups

    def restore_backup(
        self, backup_path: str, restore_to: str, callback: Optional[Callable] = None
    ) -> bool:
        """Restore a backup to a specified location.

        Args:
            backup_path: Path to the backup file
            restore_to: Directory to restore the backup to
            callback: Optional callback function for progress updates

        Returns:
            True if restore was successful, False otherwise
        """
        backup_file = Path(backup_path)
        restore_path = Path(restore_to)

        if not backup_file.exists():
            logger.error(f"Backup file does not exist: {backup_path}")
            return False

        if callback:
            callback(f"Restoring backup from {backup_file.name}...")

        logger.info(f"Restoring backup from {backup_path} to {restore_to}")

        try:
            # Create restore directory if it doesn't exist
            restore_path.mkdir(parents=True, exist_ok=True)

            # Extract backup
            with tarfile.open(backup_file, "r:xz") as tar:
                tar.extractall(restore_path)

            logger.info(f"Backup restored successfully to {restore_to}")

            if callback:
                callback("Backup restored successfully")

            return True

        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            if callback:
                callback(f"Restore failed: {e}")
            return False


def create_backup(
    music_path: str,
    backup_dir: Optional[str] = None,
    callback: Optional[Callable] = None,
    max_backups: int = 5,
    skip_window_minutes: int = 5,
) -> Optional[str]:
    """Convenience function to create a backup.

    Args:
        music_path: Path to the music folder to backup
        backup_dir: Directory to store backups
        callback: Optional callback function for progress updates
        max_backups: Maximum number of backups to keep
        skip_window_minutes: Skip creating backup if one exists within this many minutes

    Returns:
        Path to the created backup file, or None if backup failed
    """
    manager = BackupManager(backup_dir)
    return manager.create_backup(music_path, callback, max_backups, skip_window_minutes)
