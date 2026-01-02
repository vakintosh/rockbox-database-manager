====================================
Rockbox Database Manager  (12/10/09)
====================================

Mike Richards <mrichards24@gmx.com>

--------
Overview
--------
Rockbox Database Manager is a program designed to manipulate and examine
the rockbox database.  It is intended to add several features to the rockbox
database that the rockbox firmware does not currently implement.


--------
Features
--------
User-defined database tag mapping and sorting.

    The user can specify a custom tag format for each of 7 database fields
    (artist, albumartist, album, genre, comment, composer, and grouping).
    Additionally, a sorting format for each field can be specified.

    Formats are given in foobar2000 titleformat syntax.  An overview can be
    found here:
        http://wiki.hydrogenaudio.org/index.php?title=Foobar2000:Titleformat_Reference

    NB: The titleformat implementation of this program considers all white
    space significant.  Also, literal single quote characters (') are escaped
    using \' instead of two single quotes.

    For example, in order to change the sort order of artists so that a leading
    "The" is not considered (e.g. sort "The Beatles" as "Beatles, The"), use
    the following string in the sort format column:
        $swapprefix(%artist%,The)


Multiple value tags

    If a song contains tags with multiple values (e.g. multiple artists,
    multiple genres), the database manager can split those into multiple
    entries in the rockbox database.  The titleformat syntax to use for
    multiple fields that should be split is as follows:
        %<field name>%
    So, to split multiple artists, use
        %<artist>%
    All functions can be used with multiple value fields.  The syntax is the
    same.  To sort multiple artists without a leading "The", use
        $swapprefix(%<artist>%,The)

    If you wish to use this feature, your tagnavi file will have to be
    updated to reflect the changes.  In order to support multiple fields,
    the database manager creates a single dummy value of "<BLANK>" for each
    field that is split.

    All filter fields will have to have the following section added:
        field != "<BLANK>" (if the field is used in the filter)
    or
        field == "<BLANK>" (if the field is not used in the filter)

    Example:
        Assume that the user would like artist and genre fields to be split
        in the database.  The formats should look something like this:
            %<artist>%
        and
            %<genre>%

        One filter string in the tagnavi file filtered by genre, then artist,
        then album.
            "Genre" -> genre -> artist -> album -> title = "fmt_title"

        In order to use multiple fields with this string, change it to this:
            "Genre" -> genre ? genre != "<BLANK>" artist != "<BLANK>"
                    -> artist -> album -> title = "fmt_title"

        Ugly, yes, but I couldn't think of a better way to do it.

        Continuing with the example, a tagnavi line such as this:
            "Artist" -> artist -> album -> title = "fmt_title"

        would have to be changed to this:
            "Artist" -> artist ? genre == "<BLANK>" artist != "<BLANK>"
                     -> album -> title = "fmt_title"


-----------
General Use
-----------
The Manage tab contains a list of actions (blank at first), and buttons.

    Add Directory
        Add a directory to the database (recursively).  This may take some
        time if you are adding files from your DAP.  Note that all file paths
        will be stored in the database without a volume
        (e.g. D:\Music\The Beatles\... is stored as /Music/The Beatles/...)
        If your music has exactly the same directory structure on your computer
        and on your DAP, it will be significantly faster to create the database
        using files on your computer.

    Generate Database
        Create the database using format strings specified under the Formats
        tab.  Once the database has been generated, you can look at it under
        the View tab.  If more files are added to the database, it needs to
        be regenereated before the View tab reflects changes (and before
        writing the database).

    Write Database
        Write the database in rockbox format.

    Load Database
        Read a database in rockbox format.  The database can be examined in
        the View tab.  However, regenerating the database will not include
        files loaded this way.

    Save Tags
        Save all tags loaded using Add Directory (or Load Tags).  This is used
        to "save a session" using the database builder.  It has nothing to do
        with the rockbox database itself.  Tags are saved with all information
        needed to reload them for later use by the database builder.

    Load Tags
        Load tags saved to a file using Save Tags.


The Formats tab is for specifying tag mapping and sorting.  It uses Foobar2000
titleformat syntax.  Note that these formats are not saved when you exit the
database builder.  You'll have to retype them when you open the database
builder.  I'll have saving the formats working soonish.

The View tab is where you can examine the contents of the rockbox database.
The first three panes allow you to select the field you'd like to view (the
last pane is always set on "title").  At the bottom is a display showing what
the tanavi syntax for the displayed database view would be.
