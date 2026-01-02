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

MAGIC = 1413695501

ENCODING = 'utf-8'
