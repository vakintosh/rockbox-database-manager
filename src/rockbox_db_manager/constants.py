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
# 1413695504 = 0x54434810 = TCH version 16 (0x10) - 24 fields (96 bytes per entry)
# Note: Default version is now configured via .rdbm_config.toml [database] section
MAGIC = 1413695504  # Version 16
SUPPORTED_VERSIONS = [1413695504]  # Version 16 only

ENCODING = "utf-8"
