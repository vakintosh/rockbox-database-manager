"""Configuration management for Rockbox Database Manager.

Handles saving and loading user preferences including format strings,
window positions, and last used directories.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Tuple

# Python 3.11+ has tomllib built-in, earlier versions need tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # type: ignore

try:
    import tomli_w
except ImportError:
    tomli_w = None  # type: ignore


def get_config_dir() -> Path:
    """Get the configuration directory based on platform.

    Returns:
        Path to config directory (~/.config/rockbox-db-manager on Linux/Mac,
        %APPDATA%/rockbox-db-manager on Windows)
    """
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

    config_dir = base / "rockbox-db-manager"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    """Get the full path to the config file."""
    return get_config_dir() / "config.toml"


class Config:
    """Configuration manager for application settings."""

    DEFAULT_CONFIG: Dict[str, Any] = {
        "window": {
            "width": 800,
            "height": 600,
            "x": -1,  # -1 means let system decide
            "y": -1,
        },
        "paths": {
            "last_music_dir": "",
            "last_output_dir": "",
            "last_tags_file": "",
        },
        "formats": {
            # Default format strings for each field
            "artist": "%artist%",
            "album": "%album%",
            "genre": "%genre%",
            "composer": "%composer%",
        },
        "sort_formats": {
            # Default sort format strings
            "artist": "",
            "album": "",
            "genre": "",
            "composer": "",
        },
        "backup": {
            "enabled": True,  # Enable backups before write operations
            "backup_dir": "",  # Empty means use default (.rockbox_backups in music folder parent)
            "max_backups": 5,  # Maximum number of backups to keep
            "skip_window_minutes": 5,  # Skip backup if one was created within this many minutes
        },
    }

    def __init__(self):
        """Initialize configuration manager."""
        self.config_path = get_config_path()
        self.data: Dict[str, Any] = self.DEFAULT_CONFIG.copy()
        self.load()

    def load(self) -> bool:
        """Load configuration from file.

        Returns:
            True if loaded successfully, False if file doesn't exist or error occurred
        """
        if not self.config_path.exists():
            return False

        if tomllib is None:
            print("Warning: TOML library not available, using default config")
            return False

        try:
            with open(self.config_path, "rb") as f:
                loaded_data = tomllib.load(f)
                # Merge with defaults (in case new keys were added)
                self._merge_config(self.data, loaded_data)
            return True
        except Exception as e:
            print(f"Error loading config: {e}")
            return False

    def save(self) -> bool:
        """Save configuration to file.

        Returns:
            True if saved successfully, False otherwise
        """
        if tomli_w is None:
            print("Warning: TOML writer not available, config not saved")
            return False

        try:
            with open(self.config_path, "wb") as f:
                tomli_w.dump(self.data, f)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """Recursively merge override dict into base dict."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    # Window settings
    def get_window_size(self) -> Tuple[int, int]:
        """Get saved window size."""
        return (self.data["window"]["width"], self.data["window"]["height"])

    def set_window_size(self, width: int, height: int) -> None:
        """Save window size."""
        self.data["window"]["width"] = width
        self.data["window"]["height"] = height

    def get_window_position(self) -> Tuple[int, int]:
        """Get saved window position."""
        return (self.data["window"]["x"], self.data["window"]["y"])

    def set_window_position(self, x: int, y: int) -> None:
        """Save window position."""
        self.data["window"]["x"] = x
        self.data["window"]["y"] = y

    # Path settings
    def get_last_music_dir(self) -> str:
        """Get last used music directory."""
        return self.data["paths"]["last_music_dir"]

    def set_last_music_dir(self, path: str) -> None:
        """Save last used music directory."""
        self.data["paths"]["last_music_dir"] = path

    def get_last_output_dir(self) -> str:
        """Get last used output directory."""
        return self.data["paths"]["last_output_dir"]

    def set_last_output_dir(self, path: str) -> None:
        """Save last used output directory."""
        self.data["paths"]["last_output_dir"] = path

    def get_last_tags_file(self) -> str:
        """Get last used tags file."""
        return self.data["paths"]["last_tags_file"]

    def set_last_tags_file(self, path: str) -> None:
        """Save last used tags file."""
        self.data["paths"]["last_tags_file"] = path

    # Format settings
    def get_format(self, field: str) -> str:
        """Get format string for a field."""
        return self.data["formats"].get(field, f"%{field}%")

    def set_format(self, field: str, format_str: str) -> None:
        """Save format string for a field."""
        self.data["formats"][field] = format_str

    def get_sort_format(self, field: str) -> str:
        """Get sort format string for a field."""
        return self.data["sort_formats"].get(field, "")

    def set_sort_format(self, field: str, format_str: str) -> None:
        """Save sort format string for a field."""
        self.data["sort_formats"][field] = format_str

    def get_all_formats(self) -> Dict[str, str]:
        """Get all format strings."""
        return self.data["formats"].copy()

    def get_all_sort_formats(self) -> Dict[str, str]:
        """Get all sort format strings."""
        return self.data["sort_formats"].copy()

    # Backup settings
    def is_backup_enabled(self) -> bool:
        """Check if backups are enabled."""
        return self.data.get("backup", {}).get("enabled", True)

    def set_backup_enabled(self, enabled: bool) -> None:
        """Enable or disable backups."""
        if "backup" not in self.data:
            self.data["backup"] = {}
        self.data["backup"]["enabled"] = enabled

    def get_backup_dir(self) -> str:
        """Get backup directory (empty string means use default)."""
        return self.data.get("backup", {}).get("backup_dir", "")

    def set_backup_dir(self, path: str) -> None:
        """Set backup directory."""
        if "backup" not in self.data:
            self.data["backup"] = {}
        self.data["backup"]["backup_dir"] = path

    def get_max_backups(self) -> int:
        """Get maximum number of backups to keep."""
        return self.data.get("backup", {}).get("max_backups", 5)

    def set_max_backups(self, count: int) -> None:
        """Set maximum number of backups to keep."""
        if "backup" not in self.data:
            self.data["backup"] = {}
        self.data["backup"]["max_backups"] = count

    def get_backup_skip_window_minutes(self) -> int:
        """Get the time window (in minutes) to skip duplicate backups."""
        return self.data.get("backup", {}).get("skip_window_minutes", 5)

    def set_backup_skip_window_minutes(self, minutes: int) -> None:
        """Set the time window (in minutes) to skip duplicate backups."""
        if "backup" not in self.data:
            self.data["backup"] = {}
        self.data["backup"]["skip_window_minutes"] = minutes
