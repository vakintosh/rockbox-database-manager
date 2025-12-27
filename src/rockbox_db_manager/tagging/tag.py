"""
Backward compatibility module for tag functionality.

This module maintains backward compatibility by importing from the tag subpackage.
The original large tag.py file has been refactored into smaller, focused modules:

- tag/core.py: Core Tag class
- tag/formats.py: Audio format definitions and read functions
- tag/utils.py: Conversion utility functions
- tag/mappings/default.py: Default field mappings
- tag/mappings/format_specific.py: Format-specific mappings (ASF, MP4, APE, etc.)
- tag/mappings/id3.py: ID3/MP3 specific handling
"""

# Import all public APIs from the tag subpackage
from .tag import Tag, read, File, formats

# For backward compatibility, also expose the formats list at module level
__all__ = ['Tag', 'read', 'File', 'formats']
