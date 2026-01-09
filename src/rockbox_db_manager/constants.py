# Tag order matches Rockbox tagcache.h enum tag_type exactly
# tag_artist=0, tag_album=1, tag_genre=2, tag_title=3,
# tag_filename=4, tag_composer=5, tag_comment=6, tag_albumartist=7, tag_grouping=8,
# tag_year=9, tag_discnumber=10, tag_tracknumber=11,
# tag_virt_canonicalartist=12 (virtual tag stored in database)
FILE_TAGS = [
    "artist",  # 0: tag_artist
    "album",  # 1: tag_album
    "genre",  # 2: tag_genre
    "title",  # 3: tag_title
    "path",  # 4: tag_filename
    "composer",  # 5: tag_composer
    "comment",  # 6: tag_comment
    "album artist",  # 7: tag_albumartist
    "grouping",  # 8: tag_grouping
    "canonicalartist",  # 9: tag_virt_canonicalartist (artist or albumartist if artist is empty)
]

# Numeric tags stored in the index file (tag_seek array)
# Continue from tag_year=10 in Rockbox
EMBEDDED_TAGS = [
    "date",  # 10: tag_year
    "discnumber",  # 11: tag_discnumber
    "tracknumber",  # 12: tag_tracknumber
    "bitrate",  # 13: tag_bitrate
    "length",  # 14: tag_length
    "playcount",  # 15: tag_playcount
    "rating",  # 16: tag_rating
    "playtime",  # 17: tag_playtime
    "lastplayed",  # 18: tag_lastplayed
    "commitid",  # 19: tag_commitid
    "mtime",  # 20: tag_mtime
    "lastelapsed",  # 21: tag_lastelapsed (resume position in ms)
    "lastoffset",  # 22: tag_lastoffset (resume file offset)
    "flag",  # index_entry.flag (status flags)
]

FORMATTED_TAGS = FILE_TAGS[:3] + FILE_TAGS[5:]

TAGS = FILE_TAGS + EMBEDDED_TAGS

# Index Entry Flag Definitions (from tagcache.c)
FLAG_DELETED = 0x0001  # Entry has been removed from db
FLAG_DIRCACHE = 0x0002  # Filename is a dircache pointer (memory only)
FLAG_DIRTYNUM = 0x0004  # Numeric data has been modified
FLAG_TRKNUMGEN = 0x0008  # Track number has been generated
FLAG_RESURRECTED = 0x0010  # Statistics data has been resurrected

# Rockbox database format magic numbers (version identifier)
# Format: 'TCH' + version byte (TagCache Header)
# 1413695504 = 0x54434810 = TCH version 16 (0x10) - 24 fields (96 bytes per entry)
# Note: Default version is now configured via .rdbm_config.toml [database] section
MAGIC = 1413695504  # Version 16
SUPPORTED_VERSIONS = [1413695504]  # Version 16 only

ENCODING = "utf-8"
