"""Format-specific tag field mappings (ASF, MP4, APE, Musepack, WavPack)."""

from mutagen.asf import ASF
from mutagen.mp4 import MP4
from mutagen.apev2 import APEv2File as APE
from mutagen.musepack import Musepack
from mutagen.wavpack import WavPack

from ..core import Tag


def setup_format_specific_mappings():
    """Register format-specific field mappings."""

    # Info Fields (specific to certain formats)
    # ------------------------------------------
    for tag_type, tag_dict in {
        Musepack: {
            "replaygain_album_gain": "album_gain",
            "replaygain_album_peak": "album_peak",
            "replaygain_track_gain": "title_gain",
            "replaygain_track_peak": "title_peak",
        },
    }.items():
        for key, value in tag_dict.items():
            Tag.RegisterInfoKey(key, value, tag_type)

    # Standard Fields (format-specific mappings)
    # -------------------------------------------
    for tag_type, tag_dict in {
        ASF: {
            "artist": "Author",
            "album artist": "WM/AlbumArtist",
            "album": "WM/AlbumTitle",
            "date": "WM/Year",
            "discnumber": "WM/PartOfSet",
            "totaldiscs": "foobar2000/TOTALDISCS",
            "title": "Title",
            "tracknumber": "WM/TrackNumber",
            "totaltracks": "TotalTracks",
            "genre": "WM/Genre",
            "composer": "WM/Composer",
            "performer": "foobar2000/PERFORMER",
            "comment": "Description",
        },
        MP4: {
            "artist": "\xa9ART",
            "album artist": "aART",
            "album": "\xa9alb",
            "date": "\xa9day",
            "title": "\xa9nam",
            "genre": "\xa9gen",
            "composer": "\xa9wrt",
            "performer": "----:com.apple.iTunes:PERFORMER",
            "comment": "\xa9cmt",
            "replaygain_album_gain": "----:com.apple.iTunes:replaygain_album_gain",
            "replaygain_album_peak": "----:com.apple.iTunes:replaygain_album_peak",
            "replaygain_track_gain": "----:com.apple.iTunes:replaygain_track_gain",
            "replaygain_track_peak": "----:com.apple.iTunes:replaygain_track_peak",
        },
        APE: {
            "date": "Year",
        },
        Musepack: {
            "date": "Year",
        },
        WavPack: {
            "date": "Year",
        },
    }.items():
        for key, value in tag_dict.items():
            Tag.RegisterBasicKey(key, value, tag_type)

    # Discnumber / tracknumber splitting
    # -----------------------------------
    def from_tuple(key, index, default=0):
        """Helper to extract values from tuple fields."""

        def getter(tags):
            val = tags[key][0][index]
            if val == default:
                raise KeyError(key)
            return val

        def setter(tags, value):
            tags[key] = [tags[key][0][:index] + (value,) + tags[key][0][index + 1 :]]

        def deleter(tags):
            setter(tags, default)

        return getter, setter, deleter

    def split_string(key, sep, index):
        """Helper to split string fields."""
        # Index needs to be either 0 or 2 because we're using str.partition
        index = index if index == 0 else 2

        def getter(tags):
            val = str(tags[key]).partition(sep)[index]
            if val:
                return val
            else:
                raise KeyError

        def setter(tags, value):
            value = str(value)
            try:
                vals = list(str(tags[key]).partition(sep))
                vals[index] = value
                tags[key] = vals[0] + sep + vals[2]
            except KeyError:
                if index == 0:
                    tags[key] = value

        def deleter(tags):
            if index == 0:
                del tags[key]
            else:
                tags[key] = str(tags[key]).partition(sep)[0]

        return getter, setter, deleter

    # MP4 tuple-based disc/track fields
    for tag_type, tag_dict in {
        MP4: {
            "disc": "disk",
            "track": "trkn",
        }
    }.items():
        for key, value in tag_dict.items():
            Tag.RegisterKey(key + "number", tag_type, *from_tuple(value, 0))
            Tag.RegisterKey("total" + key + "s", tag_type, *from_tuple(value, 1))

    # String-split based disc/track fields
    for tag_type, tag_dict in {
        APE: {
            "disc": "Disc",
            "track": "Track",
        },
        Musepack: {
            "disc": "Disc",
            "track": "Track",
        },
        WavPack: {"disc": "Disc", "track": "Track"},
    }.items():
        for key, value in tag_dict.items():
            Tag.RegisterKey(key + "number", tag_type, *split_string(value, "/", 0))
            Tag.RegisterKey("total" + key + "s", tag_type, *split_string(value, "/", 1))

    # Custom Fields (format-specific fallbacks)
    # -----------------------------------------
    def MP4_custom_field(name):
        return "----:com.apple.iTunes:" + name.upper()

    def ASF_custom_field(name):
        return "foobar2000/" + name.upper()

    Tag.RegisterUserKey(MP4_custom_field, MP4)
    Tag.RegisterUserKey(ASF_custom_field, ASF)
