import statement
from tagbool import TagFalse

def parse(format):
    """Parse a conditional titleformat statement.
    
    Return a tuple: (Conditional, length of string parsed)

    The string should have the following format:
        '[' statement ']'
    
    """
    assert format.startswith('['), 'Missing starting square bracket'
    tf,length = statement.parse(format[1:], end_chars = ']')
    return Conditional(tf), length + 2 # two []

class Conditional(statement.Statement):

    """A titleformat object representing a conditional statement."""

    def format(self, tags):
        ret = statement.Statement.format(self, tags)
        if isinstance(ret, list):
            return [r if r else TagFalse() for r in ret]
        else:
            return ret if ret else TagFalse()

    def __repr__(self):
        return 'Conditional(%s)' % ', '.join(repr(part) for part in self)

    def to_string(self):
        return '[' + statement.Statement.to_string(self) + ']'
