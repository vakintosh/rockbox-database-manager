"""Audio file format definitions and reading functions."""

from typing import Optional
import mutagen
from mutagen.asf import ASF
from mutagen.apev2 import APEv2File as APE
from mutagen.flac import FLAC
from mutagen.easyid3 import EasyID3FileType as ID3
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

from .core import Tag


formats = [
    ASF, APE, FLAC, ID3, MP3, Vorbis, Opus, OggFLAC, Speex,
    TrueAudio, AIFF, WAVE, WavPack, MP4, Musepack
]

SUPPORTED_EXTENSIONS = {
    '.asf', '.wma', '.mp3', '.flac', '.ogg', '.opus', '.spx', 
    '.tta', '.aiff', '.aif', '.wav', '.wv', '.mp4', '.m4a', 
    '.m4b', '.mpc'
}


def read(filename: str, force_string: bool = False) -> Optional[Tag]:
    """
    Read audio file tags and return a Tag object.
    
    Args:
        filename: Path to the audio file
        force_string: If True, all fields will be returned as string lists
        
    Returns:
        Tag object if file has valid tags, None otherwise
    """
    tags = mutagen.File(filename, options=formats)
    if tags:
        return Tag(tags, force_string)
    else:
        return None


# Alias for backward compatibility
File = read
