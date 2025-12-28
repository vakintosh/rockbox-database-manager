"""TagBool defines a set of boolean wrappers around arbitrary objects.

TagBool, TagTrue, and TagFalse are factory functions that return boolean
wrapper objects.

Boolean wrapper objects inherit the class that is supplied to the factory
function, and thus can be used like ordinary objects.  The only difference is
that they evaluate to a predefined boolean value.  When boolean wrapper objects
are added together, the base classes must be addable, and the resulting
boolean value of the wrapper class returns True if *either* of the added
objects evaluates to True.

Rules concerning titleformat boolean values are somewhat complicated.  In
general, itleFormat objects should evaluate to True if there is a valid
tag lookup contained somewhere within the format.  This can be accomplished
with either a %field% statement or using one of the meta functions [i.e.
$meta(field), $meta_test(field), $meta_sep(field), or $meta_num(field) ].
Certain functions also evaluate to True regardless of the boolean value of
their arguments, for instance $strstr.

"""


def TagBool(value, rep=None):
    """
    A factory function that returns an object with the value of <rep>
    that evaluates to the specified bool value.
    """
    if rep is None:
        if value:
            rep = "1"
        else:
            rep = ""

    class BoolClass(str):
        """
        A boolean unicode class.  The class derives from unicode, so any
        unicode methods should be transparent.  The class evaluates to a
        boolean value independent of its unicode value.
        """

        def __bool__(self):
            return value

        def __repr__(self):
            return self.__class__.__name__ + "(" + repr(rep) + ")"

        def __add__(self, other):
            return TagBool(
                bool(self) or bool(other), rep.__class__.__add__(self, other)
            )

    BoolClass.__name__ = "TagTrue" if value else "TagFalse"
    return BoolClass(rep)


def TagTrue(rep="1"):
    """
    A factory function that returns an object that evaluates to True
    and is converted to a string as the <rep> parameter.
    """
    return TagBool(True, rep)


def TagFalse(rep=""):
    """
    A factory function that returns an object that evaluates to False
    and is converted to a string as the <rep> parameter.
    """
    return TagBool(False, rep)
