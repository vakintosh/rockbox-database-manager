from . import utils
from .tagbool import TagFalse

def parse(format, end_chars = None):
    """Parse a titleformat statement.
    
    Return a tuple: (Statement, length of string parsed)

    The string should have the following format:
        [ string | conditional | field | function ] *

    """

    from . import string, field, function, conditional
    char_map = {
        "'": string.parse,
        "[": conditional.parse,
        "%": field.parse,
        "$": function.parse,
    }
    own_length = 0
    parts = []
    i = 0
    last_string = ''
    while i < len(format):
        c = format[i]
        if end_chars and c in end_chars:
            break
        try:
            obj, length = char_map[c](format[i:])
            if len(last_string) > 0:
                parts.append( string.String(last_string) )
                last_string = ''
            parts.append( obj )
            own_length += length
            i += length
        except KeyError:
            own_length += 1
            last_string += c
            i += 1

    if len(last_string) > 0:
        parts.append( string.String(last_string) )
    return Statement(parts), own_length

class Statement(list):

    """An object holding a list of titleformat statements."""

    def __init__(self, parts):
        list.__init__(self, parts)

    @property
    def is_multiple(self):
        for parts in self:
            if parts.is_multiple:
                return True
        return False

    def format(self, tags):
        """
        In order for this function to return TagTrue, there must be at least
        one entity that attempts to look up a field and successfully completes
        this task.

        """
        ret = TagFalse('')
        for part in self:
            if False:
                print()
                print('Formatting')
                print('-----------')
                print(part.to_string())
            value = part.format(tags)
            if False:
                print('Result: ',repr(value))
                print()
            if isinstance(value, list):
                for v in value:
                    assert v.__class__.__name__ == 'TagTrue' or v.__class__.__name__ == 'TagFalse'
            else:
                assert value.__class__.__name__ == 'TagTrue' or value.__class__.__name__ == 'TagFalse'

            ret = utils.add(ret, value)
        if len(ret) == 1:
            return ret[0]
        else:
            return ret


    def __pprint_helper(self, tabs = 0):
        from .Function import Function
        tab_char = '    '
        lines = []
        lines.append(tab_char * tabs + f'{self.__class__.__name__}([')
        for part in self:
            if isinstance(part, Statement):
                lines.extend(Statement.__pprint_helper(part, tabs+1))
            elif isinstance(part, Function):
                lines.append(tab_char * (tabs+1) + f'Function({repr(part.name)}, [')
                for arg in part.args:
                    lines.extend(Statement.__pprint_helper(arg, tabs+2))
                    lines[-1] += ','
                lines.append(tab_char * (tabs+1) + '])')
            else:
                lines.append(tab_char * (tabs+1) + repr(part))
            lines[-1] += ','
        lines.append(tab_char * tabs + ')]')
        return lines

    def pprint(self):
        print('\n'.join(self.__pprint_helper()))

    def __repr__(self):
        return 'Statement({})'.format(', '.join(repr(part) for part in self))

    def to_string(self):
        return ''.join(part.to_string() for part in self)
