# coding=utf-8
"""File object write workaround procedure."""

import codecs

#import __init__
from .chars import *

# When 'fp' is a FILE-like object, the fp.write() method will
# not handle unicode objects with chars beyond ASCII; it
# will throw UnicodeEncodeError -- there is a wrapper
# codecs.open() that returns a FILE-like object that
# handles encoding, but a wrapper for fdopen() is absent
# (or undocumented) -- so use this fp_write()
if py_v_is_3:
    def fp_write(f_object, s):
        try:
            return f_object.write(s)
        except:
            # TODO: specify exceptions!
            if _ucode_type == None:
                _cod = 'ascii'
            else:
                _cod = _ucode_type
            return f_object.write(bytes(s, _cod))

else:
    def fp_write(f_object, s):
        if isinstance(s, unicode):
            if _ucode_type == None:
                _cod = 'ascii'
            else:
                _cod = _ucode_type
            return f_object.write(codecs.encode(_Tnec(s), _cod))
        return f_object.write(s)
