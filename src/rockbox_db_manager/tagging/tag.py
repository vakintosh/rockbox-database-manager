# All the files we can read
import os
from warnings import warn
import mutagen
from mutagen.asf import ASF
from mutagen.apev2 import APEv2File as APE
from mutagen.flac import FLAC
from mutagen.easyid3 import EasyID3FileType as ID3, EasyID3
from mutagen.mp3 import EasyMP3 as MP3
from mutagen.oggvorbis import OggVorbis as Vorbis
from mutagen.oggopus import OggOpus as Opus
from mutagen.oggflac import OggFLAC
from mutagen.oggspeex import OggSpeex as Speex
from mutagen.trueaudio import TrueAudio
from mutagen.aiff import AIFF
from mutagen.wave import WAVE
from mutagen.wavpack import WavPack
from mutagen.mp4 import MP4
from mutagen.musepack import Musepack

formats = [ ASF, APE, FLAC, ID3, MP3, Vorbis, Opus, OggFLAC, Speex, TrueAudio, AIFF, WAVE, WavPack, MP4, Musepack ]

def read(filename, force_string = False):
    tags = mutagen.File(filename, options = formats)
    if tags:
        return Tag(tags, force_string)
    else:
        return None
File = read

class Tag:
    """
    Encapsulates a mutagen tag object so that property access is simillar across
    formats. (what a chore!)
    The actual object can be accessed through self.tags.

    Available properties (a la foobar2000):
        album artist
        artist
        composer
        performer
        album
        discnumber
        totaldiscs
        title
        tracknumber
        totaltracks
        bitrate (bps)
        channels (1 or 2)
        samplerate (Hz)
        codec
        length (seconds, hopefullly floating-point)
        replaygain_album_gain
        replaygain_album_peak
        replaygain_track_gain
        replaygain_track_peak
        path
        filesize (bytes)
        last_modified
    """
    def __init__(self, tags, force_string = False):
        self.tags = tags
        self.force_string = force_string

    def __get_tags(self):
        return self.__tags
    def __set_tags(self, tags):
        self.__tags = tags
        self.update_mapping()
    tags = property(__get_tags, __set_tags)

    def update_mapping(self):
        """
        Updates self.tag_mapping to reflect the type of tags in self.tags
        """
        self.tag_mapping = self.field_map['default'].copy()
        try:
            self.tag_mapping.update(self.field_map[type(self.tags)])
        except KeyError:
            pass

    def __get_force_string(self):
        return self.__force_string
    def __set_force_string(self, force):
        self.__force_string = force
        if force:
            self.__getitem_func = self.get_string
        else:
            self.__getitem_func = self.get
        self.update_mapping()
    force_string = property(__get_force_string, __set_force_string)


    # __getitem__() is adaptable based on self.force_string
    # get() can be used to force the default conversion
    # get_string() can be used to force conversion to a list of strings

    def get(self, name):
        try:
            return self.tag_mapping[name]['convert'](
                self.tag_mapping[name]['getter'](self.tags)
            )
        except KeyError:
            return self.tag_mapping['user_field']['convert'](
                self.tag_mapping['user_field']['getter'](self.tags, name)
            )

    def get_string(self, name):
        """Convert the items to a string list before returning."""
        return self.conv_string_list(self.get(name))

    def __getitem__(self, name):
        return self.__getitem_func(name)

    def __setitem__(self, name, value):
        try:
            self.tag_mapping[name]['setter'](self.tags, value)
        except KeyError:
            self.tag_mapping['user_field']['setter'](self.tags, name, value)

    def __delitem__(self, name):
        try:
            self.tag_mapping[name]['deleter'](self.tags)
        except KeyError:
            self.tag_mapping['user_field']['deleter'](self.tags, name)

    field_map = {}

    @classmethod
    def conv_string(cls, value):
        if not isinstance(value, (list, tuple)):
            value = [value]
        return ', '.join(str(v) for v in value)

    @classmethod
    def conv_number(cls, value):
        if isinstance(value, (int, float)):
            return value
        value = cls.conv_string(value)

        def find_first_not_of(str, chars):
            for i, c in enumerate(str):
                if c not in chars:
                    return i

        # Chop to the last non-numeric value
        value = value.strip()
        sign = ''
        if value.startswith('-') or value.startswith('+'):
            sign = value[0]
            value = value[1:]
        i = find_first_not_of(value, '1234567890.')
        value = sign + value[:i]

        # Convert
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return 0

    @classmethod
    def conv_string_list(cls, value):
        if not isinstance(value, (list, tuple)):
            value = [value]
        return [cls.conv_string(v) for v in value]

    @classmethod
    def conv_number_list(cls, value):
        if not isinstance(value, (list, tuple)):
            value = [value]
        return [cls.conv_number(v) for v in value]

    @classmethod
    def conv_default(cls, value):
        if isinstance(value, (int, float)):
            return value
        return cls.conv_string(value)

    @classmethod
    def RegisterKey(cls, name, type='default',
                    getter=None, setter=None, deleter=None,
                    convert=None):
        if type not in cls.field_map:
            cls.field_map[type] = {}

        # Figure out the conversion function
        if type == 'default':
            if not convert:
                pass
        else:
            if not convert:
                try:
                    convert = cls.field_map['default'][name]['convert']
                except KeyError:
                    warning_text = \
                        f'No conversion is defined for field "{name}".  ' + \
                        f'Default conversion will be used for {repr(type)}'
                    warn(warning_text)
                    convert = cls.conv_default

        cls.field_map[type][name] = {
            'getter': getter, 'setter':setter, 'deleter': deleter,
            'convert': convert
        }

    @classmethod
    def RegisterInfoKey(cls, key, name, type='default', convert=None):
        def getter(tags):
            return tags.info.__dict__[name]
        getter.__name__ = 'info_getter(' + name + ')'
        cls.RegisterKey(key, type, getter, convert=convert)

    @classmethod
    def RegisterBasicKey(cls, key, name, type='default', convert=None):
        def getter(tags):
            return tags[name]
        getter.__name__ = 'field_getter(' + name + ')'
        def setter(tags, value):
            tags[name] = value
        setter.__name__ = 'field_setter(' + name + ')'
        def deleter(tags):
            del tags[name]
        deleter.__name__ = 'field_deleter(' + name + ')'
        cls.RegisterKey(key, type, getter, setter, deleter, convert)

    @classmethod
    def RegisterUserKey(cls, name_func, type='default'):
        """
        Register a default handler for unknown keys.
        Note that these functions take both a <tags> and a <name> argument
        instead of just the <tags> argument.
        <name_func> is a function that generates the propert key given a custom
        field name.
        """
        def user_field_getter(tags, name):
            return tags[name_func(name)]
        def user_field_setter(tags, value):
            tags[name_func(name)] = value
        def user_field_deleter(tags):
            del tags[name_func(name)]
        cls.RegisterKey('user_field', type, user_field_getter,
                        user_field_setter, user_field_deleter, cls.conv_string_list)

    def pprint(self):
        offset = max(len(key) for key in self.tag_mapping)
        for key in self.tag_mapping:
            if key == 'user_field':
                continue
            try:
                value = self[key]
                print(key.ljust(offset), type(value), value)
            except KeyError:
                print(key, '<NONE>')

    #---------------------------------------------------------------------------
    # Pickling functions
    #---------------------------------------------------------------------------
    def __getstate__(self):
        import copy

        if isinstance(self.tags, MP3):
            # Methods of an instance (such as our own '__getattr_func') can't
            # be pickled, so we need to remove them.  MP3 files have a few.
            tags_copy = copy.copy(self.tags)
            for func in ['load', 'save', 'delete']:
                try:
                    # First we have to get rid of the reference that tags_copy is
                    # holding.
                    setattr(tags_copy.tags, func, None)
                    # Now we can delete it safely
                    delattr(tags_copy.tags, func)
                except (AttributeError, TypeError):
                    # In newer versions of mutagen, these might be properties
                    # that can't be deleted. Just skip them.
                    pass
            return tags_copy, self.force_string

        elif isinstance(self.tags, APE):
            # The APE info class is defined *inside* another class, and pickle
            # only works on objects that are defined at the top level of the
            # class. (sigh)  We'll pickle the info as a dictionary.
            tags_copy = copy.copy(self.tags)
            tags_copy.info = copy.copy(self.tags.info.__dict__)
            return tags_copy, self.force_string

        elif isinstance(self.tags, FLAC) and \
                self.tags.seektable is not None and \
                self.tags.seektable.seekpoints is not None:
            # FLAC files have a table of seekpoints (tuples), which don't
            # unpickle very well.  We'll pickle the seekpoints as actual
            # tuples.
            tags_copy = copy.copy(self.tags)
            tags_copy.seektable.seekpoints = \
                [tuple(pt) for pt in tags_copy.seektable.seekpoints ]
            return tags_copy, self.force_string

        else:
            return self.tags, self.force_string


    def __setstate__(self, state):
        self.tags, self.force_string = state

        # The info is pickled as a dictionary for APE tags
        if isinstance(self.tags, APE):
            from mutagen.apev2 import APEv2File
            info = self.tags.info
            self.tags.info = object.__new__(APEv2File._Info)
            self.tags.info.__dict__.update(info)

        # The seektable.seekpoints are pickled as tuples for FLAC tags
        elif isinstance(self.tags, FLAC) and \
                self.tags.seektable is not None and \
                self.tags.seektable.seekpoints is not None:
            from mutagen.flac import SeekPoint
            self.tags.seektable.seekpoints = \
                [SeekPoint(*pt) for pt in self.tags.seektable.seekpoints ]

        elif isinstance(self.tags, MP3):
            for func in ['load', 'save', 'delete']:
                try:
                    # Try to restore the methods if they were removed
                    if not hasattr(self.tags.tags, func) or getattr(self.tags.tags, func) is None:
                        setattr(self.tags.tags, func,
                                getattr(self.tags.tags._EasyID3__id3, func))
                except (AttributeError, TypeError):
                    # In newer versions of mutagen, these might be properties
                    # that don't need restoration. Just skip them.
                    pass

#-------------------------------------------------------------------------------
# Tag field setup
#-------------------------------------------------------------------------------
# All ID3 / MP3 customization is at the end of this file.
# The customization required to correctly map foobar's tags to ID3 frames is
# complicated enough that it warrants its own section.

# File information
#-----------------
def get_path(tags):
    return tags.filename
def get_filesize(tags):
    return os.stat(get_path(tags)).st_size
def get_modified(tags):
    return os.stat(get_path(tags)).st_mtime
def get_codec(tags):
    return tags.mime

Tag.RegisterKey('path',          getter = get_path,     convert = Tag.conv_string_list)
Tag.RegisterKey('filesize',      getter = get_filesize, convert = Tag.conv_number_list)
Tag.RegisterKey('last_modified', getter = get_modified, convert = Tag.conv_number_list)
Tag.RegisterKey('codec',         getter = get_codec,    convert = Tag.conv_string_list)


# Default mapping
#----------------

# The defaults need to go in before everything else so their conversion
# functions are used as default.  Individual codecs *can* override these
# conversions, but I can't see why.
# All fields will return a list of either numbers or strings

for key, value in {
        'bitrate':  'bitrate',
        'channels': 'channels',
        'length':   'length',
        'samplerate': 'sample_rate',
    }.items():
    Tag.RegisterInfoKey(key, value, convert = Tag.conv_number_list)

for name, conv in {
        'artist':                Tag.conv_string_list,
        'album artist':          Tag.conv_string_list,
        'album':                 Tag.conv_string_list,
        'date':                  Tag.conv_string_list,
        'discnumber':            Tag.conv_number_list,
        'totaldiscs':            Tag.conv_number_list,
        'title':                 Tag.conv_string_list,
        'tracknumber':           Tag.conv_number_list,
        'totaltracks':           Tag.conv_number_list,
        'genre':                 Tag.conv_string_list,
        'composer':              Tag.conv_string_list,
        'performer':             Tag.conv_string_list,
        'comment':               Tag.conv_string_list,
        'replaygain_album_gain': Tag.conv_number_list,
        'replaygain_album_peak': Tag.conv_number_list,
        'replaygain_track_gain': Tag.conv_number_list,
        'replaygain_track_peak': Tag.conv_number_list,
    }.items():
    Tag.RegisterBasicKey(name, name, convert = conv)


# Info Fields
#------------

for tag_type, tag_dict in {
        Musepack: {
            'replaygain_album_gain': 'album_gain',
            'replaygain_album_peak': 'album_peak',
            'replaygain_track_gain': 'title_gain',
            'replaygain_track_peak': 'title_peak',
        },
    }.items():
        for key, value in tag_dict.items():
            Tag.RegisterInfoKey(key, value, tag_type)


# Standard Fields
#----------------
for tag_type, tag_dict in {
        ASF: {
            'artist':        'Author',
            'album artist':  'WM/AlbumArtist',
            'album':         'WM/AlbumTitle',
            'date':          'WM/Year',
            'discnumber':    'WM/PartOfSet',
            'totaldiscs':    'foobar2000/TOTALDISCS',
            'title':         'Title',
            'tracknumber':   'WM/TrackNumber',
            'totaltracks':   'TotalTracks',
            'genre':         'WM/Genre',
            'composer':      'WM/Composer',
            'performer':     'foobar2000/PERFORMER',
            'comment':       'Description',
        },
        MP4: {
            'artist':                '\xa9ART',
            'album artist':          'aART',
            'album':                 '\xa9alb',
            'date':                  '\xa9day',
            'title':                 '\xa9nam',
            'genre':                 '\xa9gen',
            'composer':              '\xa9wrt',
            'performer':             '----:com.apple.iTunes:PERFORMER',
            'comment':               '\xa9cmt',
            'replaygain_album_gain': '----:com.apple.iTunes:replaygain_album_gain',
            'replaygain_album_peak': '----:com.apple.iTunes:replaygain_album_peak',
            'replaygain_track_gain': '----:com.apple.iTunes:replaygain_track_gain',
            'replaygain_track_peak': '----:com.apple.iTunes:replaygain_track_peak',
        },
        APE: {
            'date': 'Year',
        },
        Musepack: {
            'date': 'Year',
        },
        WavPack: {
            'date': 'Year',
        },
    }.items():
    for key, value in tag_dict.items():
        Tag.RegisterBasicKey(key, value, tag_type)


# Discnumber / tracknumber splitting
#-----------------------------------
def from_tuple(key, index, default = 0):    
    def getter(tags):
        val = tags[key][0][index]
        if val == default:
            raise KeyError(key)
        return val
    def setter(tags, value):
        tags[key] = [tags[key][0][:index] + (value,) + tags[key][0][index+1:]]
    def deleter(tags):
        setter(tags, default)
    return getter, setter, deleter

def split_string(key, sep, index):
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

for tag_type, tag_dict in {
        MP4: {
            'disc':  'disk',
            'track': 'trkn',
        }
    }.items():
    for key, value in tag_dict.items():
        Tag.RegisterKey(key + 'number',      tag_type, *from_tuple(value, 0))
        Tag.RegisterKey('total' + key + 's', tag_type, *from_tuple(value, 1))

for tag_type, tag_dict in {
        APE: {
            'disc':  'Disc',
            'track': 'Track',
            },
        Musepack: {
            'disc':  'Disc',
            'track':  'Track',
            },
        WavPack: {
            'disc':  'Disc',
            'track':  'Track'
        }
    }.items():
    for key, value in tag_dict.items():
        Tag.RegisterKey(key + 'number',      tag_type, *split_string(value , '/', 0))
        Tag.RegisterKey('total' + key + 's', tag_type, *split_string(value , '/', 1))




# Custom Fields (fallbacks)
#--------------------------
def default_custom_field(name):
    return name
def MP4_custom_field(name):
    return '----:com.apple.iTunes:' + name.upper()
def ASF_custom_field(name):
    return 'foobar2000/' + name.upper()

for tag_type, name_func in {
        'default': default_custom_field,
        MP4:       MP4_custom_field,
        ASF:       ASF_custom_field,
    }.items():
    Tag.RegisterUserKey(name_func, tag_type)



#-------------------------------------------------------------------------------
# MP3 / ID3 additions
#-------------------------------------------------------------------------------

def RegisterAdaptableKey(name, key_finder, key_setter):
    """
    Register a key given a name, a function to look up the key in the id3
    dict, and a function to set the key if it is not already in the dict.
    """
    def getter(id3, key):
        return list(id3[key_finder(id3)])

    def setter(id3, key, value):
        try:
            frame = id3[key_finder(id3)]
        except KeyError:
            key_setter(id3, value)
        else:
            frame.text = value

    def deleter(id3, key):
        del(id3[key_finder(id3)])

    EasyID3.RegisterKey(name, getter, setter, deleter)


def find_txxx_field(id3, name):
    frame = 'TXXX:' + name.upper()
    for k in id3:
        if k.upper() == frame:
            return k
    raise KeyError('TXXX:' + name)

def new_txxx_field(id3, name, value):
    enc = 0
    # Store 8859-1 if we can, per MusicBrainz spec.
    for v in value:
        if max(v) > '\x7f':
            enc = 3
    id3.add(mutagen.id3.TXXX(encoding=enc, text=value, desc=name))

def RegisterFoobarTXXXKey(name, desc):
    """Same as the normal RegisterTXXXKey, but case-insensitive."""
    def finder(id3):
        return find_txxx_field(id3, name)
    def setter(id3, value):
        return new_txxx_field(id3, name, value)
    RegisterAdaptableKey(name, finder, setter)


# Register the TXXX frames that foobar reads/writes
for name in (
        'replaygain_album_gain',
        'replaygain_album_peak',
        'replaygain_track_gain',
        'replaygain_track_peak',
        'album artist',
        'performer',
    ):
    RegisterFoobarTXXXKey(name, name)


# Register the comment field (anything that starts with COMM)
# Foobar writes comment as COMM::'eng'  Others write it as COMM
def comment_finder(id3):
    for k in id3:
        if k.startswith('COMM'):
            return k
    raise KeyError('COMM')
def comment_setter(id3, value):
    id3.add(mutagen.id3.COMM(encoding=3, text=value))

RegisterAdaptableKey('comment', comment_finder, comment_setter)

# Rename keys as foobar uses them
for key, frame in {
        'band': 'TPE2'
    }.items():
    EasyID3.RegisterTextKey(key, frame)


# foobar stores 'tracknumber' and 'totaltracks' in the tracknumber frame 'TRCK'
# as such: %tracknumber[/%totaltracks%]
# If the %tracknumber% is blank, %totaltracks% is stored under TXXX
# (what a pain in the ass)
# We need to define (extra) special behavior for this
# Note that this is also true for discnumber / totaldiscs

def RegisterNumberPair(number_name, total_name, frameid, txxxdesc):
    txxxframe = 'TXXX:' + txxxdesc

    def number_getter(id3, key):
        return [t.partition('/')[0] for t in list(id3[frameid])]

    def total_getter(id3, key):
        try:
            sep, total = list(id3[frameid])[0].partition('/')[1:]
            if sep:
                return [total]
        except KeyError:
            return list(id3[txxxframe])
        raise KeyError(txxxframe)

    def number_setter(id3, key, number):
        if isinstance(number, (list, tuple)):
            number = number[0]
        number = str(number)

        # Get total and make the number/total string
        try:
            text = number + '/' + total_getter(id3, key)[0]
            # Try to delete the TXXX:TOTALTRACKS frame if it exists
            try:
                del(id3[txxxframe])
            except KeyError:
                pass
        except KeyError:
            text = number

        try:
            frame = id3[frameid]
            frame.text = [text]
        except KeyError:
            id3.add(mutagen.id3.Frames[frameid](encoding=3, text=text))

    def total_setter(id3, key, total):
        if isinstance(total, (list, tuple)):
            total = total[0]
        total = str(total)

        try:
            number = number_getter(id3, key)[0]
            frame = id3[frameid]
            assert len(frame.text) == 1
            frame.text = [number + '/' + total]
        except KeyError:
            new_txxx_field(id3, txxxdesc, [total])

    def number_deleter(id3, key):
        try:
            total = total_getter(id3, key)
            del(id3[frameid])
            total_setter(id3, key, total)
        except KeyError:
            pass

    def total_deleter(id3, key):
        try:
            number = number_getter(id3, key)
            del(id3[frameid])
        except KeyError:
            del(id3[txxxframe])
        else:
            number_setter(id3, key, number)


    EasyID3.RegisterKey(number_name, number_getter, number_setter, number_deleter)
    EasyID3.RegisterKey(total_name,  total_getter,  total_setter,  total_deleter)

RegisterNumberPair('tracknumber', 'totaltracks', 'TRCK', 'TOTALTRACKS')
RegisterNumberPair('discnumber',  'totaldiscs',  'TPOS', 'TOTALDISCS')


# Fallback functions for EasyID3
#-------------------------------
def generic_finder(id3, key):
    field = 'TXXX:' + key.upper()
    for k in id3:
        if k.upper() == field:
            return k
    raise KeyError(field)

# I'm not sure why it wants a <self> parameter here, but it seems to.
def user_getter(self, id3, key):
    return list(id3[find_txxx_field(id3, key)])

def user_setter(self, id3, key, value):
    try:
        frame = id3[find_txxx_field(id3, key)]
    except KeyError:
        new_txxx_field(id3, key, value.upper())
    else:
        frame.text = value

def user_deleter(self, id3, key):
    del(id3[find_txxx_field(id3, key)])

EasyID3.GetFallback = user_getter
EasyID3.SetFallback = user_setter
EasyID3.DelFallback = user_deleter
