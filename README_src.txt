====================================
Rockbox Database Manager  (12/10/09)
====================================

Mike Richards <mrichards24@gmx.com>


Rockbox Database Manager is written in python.  It has been tested with
Python 2.5 and 2.6.  The gui requires wxPython, and tagging support requires
the mutagen tagging library (http://code.google.com/p/mutagen/).  The gui
portion was designed with wxFormBuilder (http://wxformbuilder.org/).

indexfile.py and tagfile.py are an implementation of the database file format
as of this release.  The main entry point for examining the database is from
database.Database

An example:


from database import Database

# Read the database from the .rockbox folder
db = Database.read(r'path/to/DAP/.rockbox')

# List the first entry in the index (IndexEntry subclasses the builtin dict)
for k, v in db.index[0].iteritems():
    print k, v

# In order to view the contents of a tag file, use the "entries" list.
print db.artist.entries[0]

# The index file and all tag files are accessible in several ways
artist = db['artist']
artist = db.tagfiles['artist']

album_artist = db['album artist']
print album_artist.entries[0]


Have fun!
