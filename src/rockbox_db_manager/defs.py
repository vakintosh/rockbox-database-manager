FILE_TAGS = [
    'artist',
    'album',
    'genre',
    'title',
    'path',
    'composer',
    'comment',
    'album artist',
    'grouping',
]

EMBEDDED_TAGS = [
    'date',
    'discnumber',
    'tracknumber',
    'bitrate',
    'length',
    'playcount',
    'rating',
    'playtime',
    'lastplayed',
    'commitid',
    'mtime',
    'flag',
]

FORMATTED_TAGS = FILE_TAGS[:3] + FILE_TAGS[5:]

TAGS = FILE_TAGS + EMBEDDED_TAGS

# Rockbox database format magic numbers (version identifier)
# Format: 'TCH' + version byte (TagCache Header)
# 1413695501 = 0x5443480D = TCH version 13 (0x0D)
# 1413695504 = 0x54434810 = TCH version 16 (0x10)
MAGIC = 1413695501  # Default version for writing
SUPPORTED_VERSIONS = [1413695501, 1413695504]  # Versions 13 and 16

ENCODING = 'utf-8'