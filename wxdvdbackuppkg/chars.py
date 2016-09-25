# coding=utf-8
"""Some character handling hacks."""

import wx

import __init__

__all__ = ('_T', '_', '_Tnec', 's_eq', 's_ne', '_ucode_type')

py_v_is_3 = __init__.py_v_is_3

# Charset and string hacks
# Python 2.7 and 3.x differ significantly
_ucode_type = 'utf-8'
if not py_v_is_3:
    try:
        unicode('\xc3\xb6\xc3\xba\xc2\xa9', _ucode_type)
    except UnicodeEncodeError:
        _ucode_type = None
    except NameError:
        # NameError happens w/ py 3.x, should not happen w/ 2.x; if it
        # happens, assume version check was bogus and try (probably in
        # vain) to proceed as with py 3.x
        py_v_is_3 = True
        unicode = str
else:
    unicode = str

# use _T (or _) for all strings for string safety -- _("") for
# strings that should get language translation, and _T("") for
# string that should not be translated -- as in wxWidgets C++
if _ucode_type == None:
    def _T(s):
        return s
elif not py_v_is_3:
    def _T(s):
        if isinstance(s, str):
            return unicode(s, _ucode_type)
        return s
else:
    def _T(s):
        try:
            return s.decode('utf-8', 'replace')
        except:
            return str(s)

# use _T as necessary
if not py_v_is_3:
    def _Tnec(s):
        if isinstance(s, str):
            return _T(s)
        return s
else:
    def _Tnec(s):
        if not isinstance(s, str):
            return _T(s)
        return s

# inefficient string equality test, unicode vs. ascii safe
def s_eq(s1, s2):
    if _Tnec(s1) == _Tnec(s2):
        return True
    return False

def s_ne(s1, s2):
    if _Tnec(s1) != _Tnec(s2):
        return True
    return False

# E.g.: _("Sounds more poetic in Klingon.")
# TODO: other hookup needed for i18n -- can wait
# until translation volunteers materialize
#_ = wx.GetTranslation
def _(s):
    return wx.GetTranslation(_Tnec(s))

