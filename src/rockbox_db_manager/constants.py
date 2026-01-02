FILE_TAGS = [
    "artist",
    "album",
    "genre",
    "title",
    "path",
    "composer",
    "comment",
    "album artist",
    "grouping",
]

EMBEDDED_TAGS = [
    "date",
    "discnumber",
    "tracknumber",
    "bitrate",
    "length",
    "playcount",
    "rating",
    "playtime",
    "lastplayed",
    "commitid",
    "mtime",
    "flag",
    "reserved1",  # Reserved field for future Rockbox features
    "reserved2",  # Reserved field for future Rockbox features
    "reserved3",  # Reserved field for future Rockbox features
]

FORMATTED_TAGS = FILE_TAGS[:3] + FILE_TAGS[5:]

TAGS = FILE_TAGS + EMBEDDED_TAGS

# Rockbox database format magic numbers (version identifier)
# Format: 'TCH' + version byte (TagCache Header)
# 1413695501 = 0x5443480D = TCH version 13 (0x0D) - 21 fields (84 bytes per entry)
# 1413695504 = 0x54434810 = TCH version 16 (0x10) - 24 fields (96 bytes per entry)
# Note: Version 16 added 3 reserved fields for future expansion
# Note: Default version is now configured via .rdbm_config.toml [database] section
MAGIC = 1413695504  # Fallback default (version 16)
SUPPORTED_VERSIONS = [1413695501, 1413695504]  # Versions 13 and 16

ENCODING = "utf-8"
