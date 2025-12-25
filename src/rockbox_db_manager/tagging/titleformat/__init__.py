from . import statement
from .statement import Statement
from .conditional import Conditional
from .field import Field
from .string import String
from .function import Function

def compile(format_string):
    titleformat, dummy_length = statement.parse(format_string)
    return titleformat

def format(format_string, tags):
    return compile(format_string).format(tags)
