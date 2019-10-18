# coding=utf-8
"""Simple debugging procedures."""

import os
import sys
import tempfile
import time

#import __init__
from .chars import *
from .fp_write import *

_fp_write = fp_write

_fdbg = None
_fdbg_name = None
_ofd = None

def dbg_open(name = None, opened_fd = None):
    """Set debug messages on by opening an output file.

    In all cases an open debug file will be closed.  If a valid
    file descriptor is passed in opened_fd, that file will be
    set for use.  Elsewise if name is a string that can be used
    to open a file, that will be used.  Else both arguments may be
    None/False (or not given) to merely close an debug open file.
    """
    global _fdbg
    global _fdbg_name
    global _ofd

    try:
        _fdbg.close()
    except:
        pass
    try:
        os.close(_ofd)
    except:
        pass

    _fdbg = None
    _fdbg_name = None
    _ofd = None

    if not name:
        """Just closing old file."""
        return True

    if not opened_fd:
        try:
            opened_fd = os.open(name, os.O_WRONLY)
        except OSError as e:
            print("FAILED opening '{}'; '{}'!".format(name, e.strerror))
            return False

    try:
        _fdbg = os.fdopen(opened_fd, "w", 128)
        _ofd = opened_fd
        _fdbg_name = name
    except OSError as e:
        print("FAILED FDOPEN '{}'; '{}'!".format(name, e.strerror))
        return False

    return True

def pdbg(msg):
    """Print msg string to debug file, only if dbg_open() was called.

    This may be called whether or not dbg_open() was called; in the
    latter case nothing is done.
    """
    if not _fdbg:
        return
    _fp_write(_fdbg, u"{0}: {1}\n".format(time.time(), msg))
    _fdbg.flush()
