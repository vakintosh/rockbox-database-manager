import os

from tagbool import TagTrue, TagFalse

def parse(string):
    """Parse a titleformat field.
    
    Return a tuple: (Field, length of string parsed)

    The string should have the following format:
         '%' any+ '%' |
        '%<' any+ '>%'
    
    """
    assert string.startswith("%"), 'Missing starting "%"'
    string = string[1:string.index('%',1)]
    if string.startswith('<'):
        assert string.endswith('>'), 'Missing closing ">"'
        string = string[1:-1]
        return Field(string, multiple = True), len(string) + 4 # two %, two <>
    return Field(string), len(string) + 2 # two %


class Field(object):

    """A titleformat object that references a tag field."""

    def __init__(self, name, multiple = False):
        self.name = name
        self.multiple = multiple

    @property
    def is_multiple(self):
        return self.multiple

    # The "format" function will adapt based on what "name" is set to
    def get_name(self):
        return self.__name
    def set_name(self, name):
        self.__name = name
        try:
            self.function = self.func_map[name]
        except:
            def user_field(tags):
                return tags.get_string(name)
            self.function = user_field
    name = property(get_name, set_name)

    def format(self, tags):
        try:
            if self.multiple:
                return map(TagTrue, self.function(tags))
            else:
                return TagTrue(u', '.join(self.function(tags)))
        except KeyError:
            return TagFalse(u'?')


    def __repr__(self):
        if self.multiple:
            return 'Field(%s, multiple=True)' % repr(self.name)
        else:
            return 'Field(%s)' % repr(self.name)

    def to_string(self):
        if self.multiple:
            return '%<' + self.name + '>%'
        else:
            return '%' + self.name + '%'

    func_map = {}

    @classmethod
    def RegisterField(cls, name, function):
        cls.func_map[name] = function

    @classmethod
    def RegisterSimpleField(cls, name):
        def getter(tags):
            return tags.get_string(name)
        getter.__name__ = 'get_%s' % name
        cls.RegisterField(name, getter)

    @classmethod
    def RegisterMappedField(cls, name, mappings):
        def getter(tags):
            for field in mappings:
                try:
                    return tags.get_string(field)
                except KeyError:
                    pass
            raise KeyError(name)
        getter.__name__ = 'get_mapped_%s' % name
        cls.RegisterField(name, getter)

#---------------------------------------------------------------------------
# Standard foobar fields
#---------------------------------------------------------------------------

for name in (
        'album',
        'date',
        'discnumber',
        'totaldiscs',
        'title',
        'totaltracks',
        'genre',
        'replaygain_track_gain',
        'replaygain_album_gain',
        'replaygain_track_peak',
        'replaygain_album_peak',
        'samplerate',
        'path',
        'filesize',
        'last_modified',
    ):
    Field.RegisterSimpleField(name)

for name, fields in {
        'artist':       ['artist', 'album artist', 'composer', 'performer'],
        'album artist': ['album artist', 'artist', 'composer', 'performer'],
    }.iteritems():
    Field.RegisterMappedField(name, fields)

def get_tracknumber(tags):
    return [tags.get_string('tracknumber')[0].zfill(2)]
Field.RegisterField('tracknumber', get_tracknumber)

def get_bitrate(tags):
    return [str( int(tags.get_string('bitrate')[0]) / 1000 )]
Field.RegisterField('bitrate', get_bitrate)

def _get_length(tags):
    return float(tags.get_string('length')[0])
def get_length_seconds_fp(tags):
    return [str(_get_length(tags))]
def get_length_seconds(tags):
    return [str(int(_get_length(tags)))]
def get_length(tags):
    seconds = _get_length(tags)
    minutes, seconds      = divmod(seconds, 60)
    return [u'%d:%02d' % (minutes, seconds)]
def get_length_ex(tags):
    seconds = _get_length(tags)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes   = divmod(minutes, 60)
    ret = ''
    if hours:
        ret += str(int(hours)) + ':'
    return [ret + u'%02d:%06.3f' % (minutes, seconds)]

Field.RegisterField('length',            get_length)
Field.RegisterField('length_seconds',    get_length_seconds)
Field.RegisterField('length_seconds_fp', get_length_seconds_fp)
Field.RegisterField('length_ex',         get_length_ex)

def get_track_artist(tags):
    try:
        artist = Field.func_map['artist'](tags)
    except KeyError:
        raise KeyError('track artist')

    try:
        album_artist = Field.func_map['album artist'](tags)
    except KeyError:
        return artist

    if artist != album_artist:
        return artist
    else:
        raise KeyError('track artist')

Field.RegisterField('track artist', get_track_artist)


def _get_path(tags):
    return tags.get_string('path')[0]
def get_filename_ext(tags):
    return [os.path.split(_get_path(tags))[1]]
def get_filename(tags):
    return [os.path.splitext(get_filename_ext(tags))[0]]
def get_directoryname(tags):
    return [os.path.basename(os.path.dirname(_get_path(tags)))]

Field.RegisterField('filename_ext',  get_filename_ext)
Field.RegisterField('filename',      get_filename)
Field.RegisterField('directoryname', get_directoryname)
