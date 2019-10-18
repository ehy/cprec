# coding=utf-8
"""
Miscellaneous procedures and classes.
"""

import errno
eintr  = errno.EINTR
echild = errno.ECHILD
efault = errno.EFAULT
einval = errno.EINVAL
import os
import re
import stat
import wx

#import __init__
from .chars import *
from .msgprocs import *
from .debug import pdbg

_dbg = pdbg


"""
    utility procedures
"""


def x_lstat(path, quiet = False, use_l = True):
    """Stat a file and on error return None rather than throw.

    If queit is True then print no errors -- else print on msg object.
    If use_l is True (default) use lstat(2)
    """
    try:
        if use_l:
            return os.lstat(path)
        else:
            return os.stat(path)
    except OSError as e:
        m = _("Error: cannot stat '{0}': '{1}' (errno {2})").format(
            path, e.strerror, e.errno)
        _dbg(m)
        if not quiet:
            msg_line_ERROR(m)
        return None


# There are important changes from wxWidgets 2.8 -> 3.x -- need to know
_wxpy_is_v3 = None
def is_wxpy_v3():
    global _wxpy_is_v3
    if _wxpy_is_v3 == None:
        if wx.MAJOR_VERSION >= 3:
            _wxpy_is_v3 = True
        elif wx.MAJOR_VERSION == 2 and wx.MINOR_VERSION >= 9:
            _wxpy_is_v3 = True
        else:
            _wxpy_is_v3 = False

    return _wxpy_is_v3

# utility for wx window objects with children: invoke a procedure
# on window's children, and their children, recursivley -- procedure
# must take window object parameter
def invoke_proc_for_window_children(window, proc):
    proc(window)

    for wnd in window.GetChildren():
        invoke_proc_for_window_children(wnd, proc)

# for Unix systems that have different nodes for raw vs. block
# devices: get desired path from arg
# TODO: check OpenSolaris!
os_uname = os.uname()[0]
raw_node_rx = re.compile('^rcd[0-9]+[a-z]$')
block_node_rx = re.compile('^cd[0-9]+[a-z]$')
def raw_node_path(pth):
    # pertinent BSD systems that use r* for raw nodes
    bsd = (_T("NetBSD"), _T("OpenBSD"))

    if os_uname in bsd:
        spl = os.path.split(pth)
        if s_eq(spl[0], '/dev') and block_node_rx.match(_T(spl[1])):
            pth = os.path.join(_T(spl[0]), _T('r{0}').format(spl[1]))

    return pth

def block_node_path(pth):
    # pertinent BSD systems that use r* for raw nodes
    bsd = (_T("NetBSD"), _T("OpenBSD"))

    if os_uname in bsd:
        spl = os.path.split(pth)
        if s_eq(spl[0], '/dev') and raw_node_rx.match(_T(spl[1])):
            pth = os.path.join(_T(spl[0]), _T(spl[1][1:]))

    return pth



"""
    utility classes
"""


class WXObjIdSource:
    """
    A sequential integer ID dispenser for wx objects like
    menu/toolbar items, buttons
    prefix WX in capitols to distinguish from actual wx objects/code
    """
    seed = wx.ID_HIGHEST + 1000
    cur = seed
    incr = 1

    def __init__(self, offs = 0):
        self.offs = offs

    def __call__(self):
        return self.get_new_id()

    def get_seed(self):
        return self.__class__.seed

    def get_cur(self):
        return self.__class__.cur

    def get_new_id(self):
        if True:
            v = self.__class__.cur + self.offs
            self.__class__.cur += self.__class__.incr
        else:
            v = wx.NewId()
        wx.RegisterId(v)
        return v
