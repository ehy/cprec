#! /usr/bin/env python
# coding=utf-8
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

"""
DVD Backup fronted for cprec and dd-dvd, growisofs, genisoimage/mkisofs
"""

import codecs
import collections
import errno
eintr  = errno.EINTR
echild = errno.ECHILD
efault = errno.EFAULT
einval = errno.EINVAL
import math
import os
import re
import select
import signal
import stat
import string
import sys
import tempfile
import threading
import time
import wx
try:
    import wx.adv
    phoenix = True
    wxadv = wx.adv
except ImportError:
    import wx.aui
    phoenix = False
    wxadv = wx

# from wxPython samples
import wx.lib.mixins.listctrl as listmix
import wx.lib.sized_controls as sc
import wx.lib.scrolledpanel as scrollpanel
from wx.lib.embeddedimage import PyEmbeddedImage
try:
    import wx.lib.agw.multidirdialog as MDD
except:
    pass
# end from wxPython samples


# will often need to know whether interpreter is Python 3
_is_py3 = False
if sys.version_info.major >= 3:
    _is_py3 = True


"""
    Global procedures
"""

# Charset and string hacks
# Python 2.7 and 3.x differ significantly
_ucode_type = 'utf-8'
if not _is_py3:
    try:
        unicode('\xc3\xb6\xc3\xba\xc2\xa9', _ucode_type)
    except UnicodeEncodeError:
        _ucode_type = None
    except NameError:
        # NameError happens w/ py 3.x, should not happen w/ 2.x; if it
        # happens, assume version check was bogus and try (probably in
        # vain) to proceed as with py 3.x
        _is_py3 = True
        unicode = str
else:
    unicode = str

# use _T (or _) for all strings for string safety
if _ucode_type == None:
    def _T(s):
        return s
elif not _is_py3:
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
if not _is_py3:
    def _Tnec(s):
        if isinstance(s, str):
            return _T(s)
        return s
else:
    def _Tnec(s):
        if not isinstance(s, str):
            return _T(s)
        return s

# When 'fp' is a FILE-like object, the fp.write() method will
# not handle unicode objects with chars beyond ASCII; it
# will throw UnicodeEncodeError -- there is a wrapper
# codecs.open() that returns a FILE-like object that
# handles encoding, but a wrapper for fdopen() is absent
# (or undocumented) -- so use this fp_write()
if _is_py3:
    def fp_write(f_object, s):
        try:
            return f_object.write(s)
        except:
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

msg_red_color = wx.RED
msg_green_color = wx.Colour(0, 227, 0)
msg_blue_color = wx.BLUE
#msg_yellow_color = wx.Colour(227, 227, 0)
msg_yellow_color = wx.Colour(202, 145, 42)
msg_default_color = wx.BLACK

def msg_(msg, clr = None):
    if _msg_obj_init_is_done == True:
        if clr == None:
            _msg_obj.AppendTextColored(msg, msg_default_color)
        else:
            _msg_obj.AppendTextColored(msg, clr)
    else:
        fp_write(sys.stdout, msg)

def err_(msg, clr = None):
    _dbg(msg)
    if _msg_obj_init_is_done == True:
        if clr == None:
            _msg_obj.AppendTextColored(msg, msg_red_color)
        else:
            _msg_obj.AppendTextColored(msg, clr)
    else:
        fp_write(sys.stderr, msg)

def msg_red(msg):
    msg_(msg, msg_red_color)

def msg_green(msg):
    msg_(msg, msg_green_color)

def msg_blue(msg):
    msg_(msg, msg_blue_color)

def msg_yellow(msg):
    msg_(msg, msg_yellow_color)


def msg_ERROR(msg):
    msg_red(msg)

def msg_WARN(msg):
    msg_yellow(msg)

def msg_GOOD(msg):
    msg_green(msg)

def msg_INFO(msg):
    msg_blue(msg)


def msg_line_(msg, clr = None):
    if _msg_obj_init_is_done == True:
        msg_(_T("\n") + msg, clr)
    else:
        msg_(msg + _T("\n"), clr)

def err_line_(msg, clr = None):
    m = _T("{0}: {1}").format(PROG, msg)
    if _msg_obj_init_is_done == True:
        err_(_T("\n") + m, clr)
        fp_write(sys.stderr, m + _T("\n"))
    else:
        err_(m + _T("\n"), clr)

def msg_line_red(msg):
    msg_line_(msg, msg_red_color)

def msg_line_green(msg):
    msg_line_(msg, msg_green_color)

def msg_line_blue(msg):
    msg_line_(msg, msg_blue_color)

def msg_line_yellow(msg):
    msg_line_(msg, msg_yellow_color)


def msg_line_ERROR(msg):
    msg_line_red(msg)

def msg_line_WARN(msg):
    msg_line_yellow(msg)

def msg_line_GOOD(msg):
    msg_line_green(msg)

def msg_line_INFO(msg):
    msg_line_blue(msg)

# stat a file and on error return None rather than throw
# and print error message
def x_lstat(path, quiet = False, use_l = True):
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
    Development hacks^Wsupport
"""

PROGLONG = _T(os.path.split(sys.argv[0])[1])
PROG = PROGLONG
def __mk_PROG():
    try:
        tr = PROGLONG.rindex(_T(".py"))
    except:
        tr = len(PROGLONG)

    global PROG
    PROG = PROGLONG[:tr]

__mk_PROG()

if "-XGETTEXT" in sys.argv:
    try:
        # argv[0] is unreliable, but this is not for general use.
        _xgt = "xgettext"
        _xgtargs = (_xgt, "-o", "-", "-L", "Python",
                "--keyword=_", "--add-comments", sys.argv[0])
        os.execvp(_xgt, _xgtargs)
    except OSError as e:
        sys.stderr.write("Exec {0} {p}: {1} ({2})\n".format(
            _xgt, e.strerror, e.errno, p = sys.argv[0]))
        exit(1)


if "-DBG" in sys.argv:
    _ofd, _fdbg_name = tempfile.mkstemp(".dbg", "_DBG_wxDVDBackup-")
    _fdbg = os.fdopen(_ofd, "w", 0)
else:
    _fdbg = None

def _dbg(msg):
    if not _fdbg:
        return
    fp_write(_fdbg, u"{0}: {1}\n".format(time.time(), msg))

_dbg(_T("debug file opened"))


"""
    Global data
"""

# version globals: r/o
# jump 0.0.2.0->0.3.0 to sync with package
version_string = _T("0.4.0")
version_name   = _("Mortal Coil Shed")
version_mjr    = 0
version_mjrrev = 4
version_mnr    = 0
version_mnrrev = 0
version = (
    version_mjr<<24|version_mjrrev<<16|version_mnr<<8|version_mnrrev)
maintainer_name = _T("Ed Hynan")
maintainer_addr = _T("<edhynan@gmail.com>")
copyright_years = _T("2016")
program_site    = _T("https://github.com/ehy/cprec")
program_desc    = _T("Flexible backup for video DVD discs.")
program_devs    = [maintainer_name]

_msg_obj = None
_msg_obj_init_is_done = False

# Two arrow images courtesy of wxPython demo/images.py,
# for list control columns indicating sort order
SmallUpArrow = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYA"
    "AAAf8/9hAAAABHNCSVQICAgIfAhkiAAAADxJ"
    "REFUOI1jZGRiZqAEMFGke2gY8P/f3/9kGwDT"
    "jM8QnAaga8JlCG3CAJdt2MQxDCAUaOjyjKMp"
    "cRAYAABS2CPsss3BWQAAAABJRU5ErkJggg==")

SmallDnArrow = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYA"
    "AAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAEhJ"
    "REFUOI1jZGRiZqAEMFGke9QABgYGBgYWdIH/"
    "//7+J6SJkYmZEacLkCUJacZqAD5DsInTLhDR"
    "bcPlKrwugGnCFy6Mo3mBAQChDgRlP4RC7wAAAABJRU5ErkJggg==")



"""
    Classes
"""


"""
ChildProcParams:
Parameter holding object to simplify interface to ChildTwoStreamReader.
Arguments to constructor:
    cmd = string, name of command; may or not be path or a simple name,
    cmdargs = a list object with args -- [0] must be set as usual,
    cmdenv = any environment variables to be set for the process:
        this may be a map ('dict') with the variable as key and value
        as the value, or either a tuple or list of 2-tuples, each
        of which has the variable at the zero index and value at one,
    stdin_fd = if present and not None this may be a readable integer
        file descriptor that will serve as input for the process, or
        another ChildProcParams object as part of a linked list that
        will create a process pipline (see below), or a string with a
        filename to be opened for reading (unchecked); if this is not
        given or is None then /dev/null will be opened for use;
        finally, the ChildProcParams object will only close descriptors
        opened herein -- i.e., a name string or None or not given.

# ChildTwoStreamReader builds a pipeline if ChildProcParams is in fact
# a list where ChildProcParams.fd is another ChildProcParams and so on.
#
# For example, like this . . .
pipecmds = []
pipecmds.append( ("cat", (), {}) )
pipecmds.append( ("sed",
    ('-e', 's/lucy/& IN THE SKY/g', '-e', 's/kingbee/IM A & BABY/g'),
     {}) )
pipecmds.append( ("tr", ('#', '*'), {}) )
pipecmds.append( ("grep", ('-E', '-v', rxpatt), {}) )
pipecmds.append( ("sort", (), {"LC_ALL":"C"}) )
pipecmds.append( ("uniq", (), {}) )

parm_obj = in_fd = os.open(infile, os.O_RDONLY)

for cmd, aargs, envmap in pipecmds:
    cmdargs = [cmd]
    for arg in aargs:
        cmdargs.append(arg)
    try:
        parm_obj = ChildProcParams(cmd, cmdargs, envmap, parm_obj)
    except ChildProcParams.BadParam as e:
        PutMsgLineERROR("Exception '%s'" % e)
        exit(1)

if parm_obj:
    ch_proc = ChildTwoStreamReader(parm_obj)
    is_ok = ch_proc.go_and_read()
    status = ch_proc.wait()
os.close(in_fd)
"""
class ChildProcParams:
    def __init__(
        self, cmd, cmdargs = None, cmdenv = None, stdin_fd = None
        ):
        self.xcmd = cmd

        if isinstance(cmdargs, list):
            self.xcmdargs = cmdargs
        elif cmdargs == None:
            self.xcmdargs = [cmd]
        else:
            self.__except_init()
            raise ChildProcParams.BadParam(_("cmdargs is wrong type"))

        if (isinstance(cmdenv, list) or
            isinstance(cmdenv, dict) or
            isinstance(cmdenv, tuple)):
            self.xcmdenv = cmdenv
        elif cmdenv == None:
            self.xcmdenv = []
        else:
            self.__except_init()
            raise ChildProcParams.BadParam(_("cmdenv is wrong type"))

        if isinstance(stdin_fd, str) or isinstance(stdin_fd, unicode):
            self.infd = os.open(stdin_fd, os.O_RDONLY)
            self.infd_opened = True
            self.proc_input  = False
        elif isinstance(stdin_fd, int):
            self.infd = stdin_fd
            self.infd_opened = False
            self.proc_input  = False
        elif isinstance(stdin_fd, ChildProcParams):
            self.infd = stdin_fd
            self.infd_opened = False
            self.proc_input  = True
        elif stdin_fd == None:
            self.infd = os.open(os.devnull, os.O_RDONLY)
            self.infd_opened = True
            self.proc_input  = False
        else:
            self.__except_init()
            raise ChildProcParams.BadParam(_("stdin_fd is wrong type"))

    def __del__(self):
        if self.infd_opened and self.infd > -1:
            try:
                os.close(self.infd)
            except OSError as e:
                # TODO: indicate error
                pass
            except AttributeError:
                # py3 throwing this at end of script; bug in py3
                # that modules might be GC'd at shutdown before
                # objects use them. sys.version: 3.4.3
                pass
            except:
                # py3 throwing something else intermittently,
                # finding os to be 'NoneType'
                pass

    def __except_init(self):
        self.xcmd = None
        self.xcmdargs = None
        self.xcmdenv = None
        self.infd = None
        self.infd_opened = False
        self.proc_input  = False

    def close_infd(self):
        if self.infd_opened and self.infd > -1:
            os.close(self.infd)
        self.infd_opened = False
        self.infd = -1

    class BadParam(Exception):
        def __init__(self, args):
            Exception.__init__(self, args)


"""
Exec a child process, when both its stdout and stderr are wanted --
    class ChildProcParams for child parameters.
Method go() (see comment there) returns read fd on which child
    stdout lines have prefix "1: " and stderr has "2: " and anything
    else is a message from an auxiliary child (none at present)
Method go_and_read() (see comment there) invokes go() and reads and
    stores lines of outputs in three arrays which can be retrieved
    with get_read_lists() -- after which reset_read_lists() can be
    called if object is to be used again.
See method comments in class definition
"""
class ChildTwoStreamReader:
    prefix1 = _T("1: ")
    prefix2 = _T("2: ")
    prefixX = _T("x: ") # Exceptional, errors

    catch_sigs = (
        signal.SIGINT,
        signal.SIGTERM,
        signal.SIGQUIT,
        signal.SIGHUP,
        signal.SIGUSR1,
        signal.SIGUSR2,
        #signal.SIGPIPE,
        signal.SIGALRM
    )
    norest_sigs = (
        signal.SIGINT,signal.SIGTERM,signal.SIGQUIT,signal.SIGALRM
    )
    _exit_sigs = (
        signal.SIGINT,
        signal.SIGTERM,
        signal.SIGQUIT,
        signal.SIGHUP,
        #signal.SIGUSR1,
        signal.SIGUSR2,
        signal.SIGPIPE
    )

    fork_err_status = 69
    exec_err_status = 66
    exec_wtf_status = 67
    pgrp_err_status = 68

    # do not refer to this directly: use static _get_pipestat_rx
    pipestat_rx = None

    # file-like object open modes
    open_mode_r = "rb"
    open_mode_w = "wb"

    def __init__(self,
                 child_params = None,
                 gist = None,
                 line_rdsize = 4096):
        # I've read that file.readline(*size*) requires a non-zero
        # *size* arg to reliably return "" *only* on EOF
        # (which is needed)
        self.szlin = line_rdsize

        # If this is not None, it is invoked in dtor, e.g. for cleanup;
        # No ctor param to set it -- use set_dtor_lambda()
        self.dtor_lambda = None

        self.params = child_params
        self.core_ld = gist

        self.xcmd = None

        if self.params != None:
            self.xcmd = self.params.xcmd
            self.xcmdargs = self.params.xcmdargs
            self.xcmdenv = self.params.xcmdenv
        else:
            self.xcmdargs = []
            self.xcmdenv = []

        # this is orig, object, not result of a fork()
        self.root = True

        self.extra_data = None
        self.error_tuple = None
        # list of tuple for pipeline each
        # (pid, status, signalled, extra)
        self.procstat = [ (-1, -1, False, None) ]
        # flag necessitated by growisofs signal handling:
        # blocks/unblocks sigs, and will exit(EINTR) on interrupted call
        # so cannot assume cancel signal yields signalled status --
        # caller should call set_growisofs() when needed
        self.growisofs = False

        self.rlin1 = []
        self.rlin2 = []
        self.rlinx = []


    def __del__(self):
        if self.dtor_lambda != None:
            self.dtor_lambda()


    def set_dtor_lambda(self, procobj):
        self.dtor_lambda = procobj

    @staticmethod
    def status_string(stat, signalled = False):
        if signalled:
            r = _("terminated with signal {n}")
            if stat == signal.SIGINT:
                s = _T("SIGINT")
            elif stat == signal.SIGTERM:
                s = _T("SIGTERM")
            elif stat == signal.SIGQUIT:
                s = _T("SIGQUIT")
            elif stat == signal.SIGHUP:
                s = _T("SIGHUP")
            elif stat == signal.SIGUSR1:
                s = _T("SIGUSR1")
            elif stat == signal.SIGUSR2:
                s = _T("SIGUSR2")
            elif stat == signal.SIGPIPE:
                s = _T("SIGPIPE")
            elif stat == signal.SIGALRM:
                s = _T("SIGALRM")
            else:
                s = _T(str(stat))

            return r.format(n = s)

        if stat == ChildTwoStreamReader.fork_err_status:
            return _("failed, because fork() system call failed")
        elif stat == ChildTwoStreamReader.exec_err_status:
            return _("failed, could not be executed")
        elif stat == ChildTwoStreamReader.exec_wtf_status:
            return _("failed with an unknown execution error")
        elif stat == ChildTwoStreamReader.pgrp_err_status:
            return _("failed to create new process group")
        elif stat:
            return _("failed")


        return _("succeeded")


    """
    protected: setup signals handler in children
    """
    def _child_sigs_setup(self):
        norest = self.norest_sigs

        for sig in self.catch_sigs:
            signal.signal(sig, self._child_sigs_handle)
            if not sig in norest:
                signal.siginterrupt(sig, False)

    """
    protected: setup signals default in children
    """
    def _child_sigs_defaults(self):
        for sig in self.catch_sigs:
            signal.signal(sig, signal.SIG_DFL)

    """
    protected: handle signals in children
    """
    def _child_sigs_handle(self, sig, frame):
        mpid = os.getpid()
        _dbg(_T("handler pid %d, with signal %d") % (mpid, sig))
        # are we 1st child. grouper leader w/ children?
        if not self.root:
            # USR1 used by this prog
            if sig == signal.SIGUSR1:
                sig = signal.SIGINT
                for p, s, b, x in self.procstat:
                    _dbg(_T("handler kill {p}, with signal {s}").format(
                        p = p, s = sig))
                    self.kill(sig, p)
            else:
                self.kill(sig)
            return
        if sig in self._exit_sigs:
            _dbg(_T("handler:exit pid %d, with signal %d") % (mpid, sig))
            os._exit(1)

    """
    static protected: get regex gor pipestatus lines
    """
    @staticmethod
    def _get_pipestat_rx():
        if ChildTwoStreamReader.pipestat_rx == None:
            ChildTwoStreamReader.pipestat_rx = re.compile(
                "status:\s+cmd='([^']*)'"
                "\s+code='([^']*)'"
                "\s+signalled='([^']*)'"
                "\s+status_string='([^']*)'"
                "(.*)$")

        return ChildTwoStreamReader.pipestat_rx

    """
    static public: return list [cmd, code, bool_signalled, string]
                   for a status line from pgrp child, or False
    """
    @staticmethod
    def get_pipestat_line_data(line):
        rx = ChildTwoStreamReader._get_pipestat_rx()
        m = rx.search(line)
        if not m:
            return False

        sig = True
        if s_eq(m.group(3), "False"):
            sig = False

        return [
            m.group(1), int(m.group(2)), sig, m.group(4), m.group(5)
            ]

    """
    method public: return list [cmd, code, bool_signalled, string]
                   for a status line from pgrp child, or False
    """
    def get_stat_line_data(self, line):
        return self.__class__.get_pipestat_line_data(line)

    """
    method public: return list of lists from get_stat_line_data(),
                   in order -- call after self.wait()
    """
    def get_pipeline_status(self):
        r = []

        for l in self.rlinx:
            dat = self.get_stat_line_data(l)
            if dat:
                r.append(dat)

        return r

    """
    public: kill (signal) child pid
    """
    def kill(self, sig = 0, pid = None):
        plen = len(self.procstat)
        idx = -1

        if pid != None:
            for i in range(plen):
                if pid == self.procstat[i][0]:
                    idx = i
                    break
            if idx == -1:
                return -1

        return self.kill_index(sig, idx)

    """
    public: kill child pid at index into pipeline
    """
    def kill_index(self, sig = 0, idx = -1):
        if not (idx == -1 or idx in range(len(self.procstat))):
            return -1
        pid = self.procstat[idx][0]

        if pid > 0 or pid < -1:
            try:
                os.kill(pid, sig)
                return 0
            except OSError as e:
                self.error_tuple = (pid, sig, e.errno, e.strerror)

        return -1

    """
    public: wait on child at index 'idx' in self.procstat
    opts may be given os.WNOHANG, or string "nohang"
    return status on success, -1 on error, -2 on none-ready
    """
    def wait(self, idx = -1, opts = 0):
        if idx == -1 or idx in range(len(self.procstat)):
            pidtuple = self.procstat[idx]
        else:
            return -1

        wpid = pidtuple[0]

        if wpid == -1 or not pidtuple[1] == -1:
            return -1

        if s_eq(opts, "nohang"):
            opts = os.WNOHANG
        elif opts != 0 and opts != os.WNOHANG:
            return -1

        while True:
            try:
                pid, stat = os.waitpid(wpid, opts)

                # had WNOHANG and nothing ready:
                if pid == 0 and stat == 0:
                    return -2

                # not handling WIFSTOPPED; we're not tracing and
                # opt WUNTRACED is disallowed
                # likewise WIFCONTINUED as WCONTINUED is disallowed

                if os.WIFSIGNALED(stat):
                    cooked = os.WTERMSIG(stat)
                    bsig = True
                elif os.WIFEXITED(stat):
                    cooked = os.WEXITSTATUS(stat)
                    bsig = False
                else:
                    _dbg(_T("wait not {tsts}: {stat}").format(
                        tsts = _T("WIFSIGNALED or WIFEXITED"),
                        stat = stat))
                    return -1

                self.procstat[idx] = (
                    pid, cooked, bsig, self.procstat[idx][3])
                return cooked

            except OSError as e:
                if e.errno  == eintr:
                    continue
                if e.errno  == echild:
                    _dbg(_T("wait failing ECHILD {p}").format(p = wpid))
                else:
                    _dbg(_T("wait error \"{s}\" (errno {n})").format(
                        s = e.strerror, n = e.errno))
                return -1

        _dbg(_T("wait pid {p} FAILURE").format(p = wpid))
        return -1

    """
    protected: child wait on all in process group
    """
    def _child_wait_all(self):
        aw = self.procstat

        lr = r = -1
        ls = False
        awlen = len(aw)
        for i in range(awlen):
            stat = self.wait(i)
            r = max(r, stat)
            if r > lr:
                lr = r
                _dbg(_T("New stat {c}, signalled is {s}").format(
                    c = lr, s = aw[i][2]))
            _dbg(_T("WAIT_ALL pid {p}, stat {s}").format(
                p = aw[i][0], s = stat))

        return r

    """
    public: do kill and wait on current child
    """
    def kill_wait(self, sig = 0):
        if self.kill(sig) != 0:
            return -1
        return self.wait()

    """
    set extra data that instance will carry
    """
    def set_extra_data(self, dat = None):
        self.extra_data = dat

    """
    get extra data that may have been set for instance to carry
    """
    def get_extra_data(self):
        return self.extra_data

    """
    when instantiated for growisofs, this should be set: see __init__()
    """
    def set_growisofs(self, it_is_so = True):
        self.growisofs = it_is_so

    """
    get the growisofs flag
    """
    def is_growisofs(self):
        return self.growisofs


    """
    command may be set after object init
    """
    def set_command(self, cmd, cmdargs, cmdenv = None, l_rdsize = 4096):
        p = ChildProcParams(cmd, cmdargs, cmdenv)
        self.set_command_params(p, l_rdsize)

    """
    command may be set after object init
    """
    def set_command_params(self, child_params, line_rdsize = 4096):
        self.szlin = line_rdsize

        self.params = child_params

        self.xcmd = None

        if self.params != None:
            self.xcmd = self.params.xcmd
            self.xcmdargs = self.params.xcmdargs
            self.xcmdenv = self.params.xcmdenv
        else:
            self.xcmdargs = []
            self.xcmdenv = []


    """
    get tuple of arrays filled by go_and_read -- this will return
    the refs before go_and_read has been called, so they might
    not be currently filled -- the first two in the tuple of three
    are the command std{out,err}; the third will be any output from
    an auxiliary child process, and should be empty
    """
    def get_read_lists(self):
        return (self.rlin1, self.rlin2, self.rlinx)

    """
    get_read_lists() does not reset arrays and if object is reused then
    output can accumulate, or this can be called to reset output store
    """
    def reset_read_lists(self):
        self.rlin1 = []
        self.rlin2 = []
        self.rlinx = []


    """
    get child status, return tuple integer code, boolean signalled --
    stat is -1 if method is called before child process has been
    run -- if child has been run, this optionally resets data -1, False
    so that object may be used again; hence this method can be called
    once per child run, or if running async e.g. in new thread then
    other thread may call this to poll until status is not -1
    """
    def get_status(self, reset = False):
        ret = (self.procstat[-1][1], self.procstat[-1][2])
        if reset:
            self.procstat = [ (-1, -1, False, None) ]

        return ret

    """
    get child status descriptive string in a tuple with
    status and signalled boolean, and optionally reset status
    """
    def get_status_string(self, reset = False):
        stat, sig = self.get_status(reset)
        return (stat, sig, self.__class__.status_string(stat, sig))

    """
    simple helper for caller of go() below: it returns a 2 tuple
    on success or error: on success both elements are ints -- pid
    and read descriptor -- on error one element will not be and int
    -- presently the only error return is that the tuple will be
    errno, strerror from OSError object, make the second element
    a str (but this may change)
    """
    def go_return_ok(self, fpid, rfd):
        if not isinstance(rfd, int):
            return False
        if fpid < 1:
            return False
        return True

    """
    fork() and return tuple (child_pid, read_fd),
    or on OSError (errno, strerror), or on other error (0, "message")
    -- caller must wait on pid -- this object will know nothing more
    about it
    """
    def go(self):
        if not isinstance(self.params, ChildProcParams):
            self.error_tuple = (0, _T("error: no child command"))
            return self.error_tuple

        is_path = os.path.split(self.xcmd)
        if len(is_path[0]) > 0:
            is_path = True
        else:
            is_path = False

        try:
            rfd, wfd = os.pipe()
        except OSError as e:
            self.error_tuple = (e.errno, e.strerror)
            return self.error_tuple

        try:
            fpid = os.fork()
        except OSError as e:
            os.close(rfd)
            os.close(wfd)
            self.error_tuple = (e.errno, e.strerror)
            return self.error_tuple

        # Novelty: nested procs
        def wrlinepfx(fp, pfx, lin):
            fp_write(fp, pfx)
            fp_write(fp, lin)

        def s_procdata(args, env):
            __s = _T("")
            for __t in args:
                __t = _Tnec(__t)
                __s = _T("{s} - arg \"{a}\"").format(s = __s, a = __t)
            try:
                if isinstance(env, dict):
                    for k in env:
                        v = _Tnec(env[k])
                        k = _Tnec(k)
                        __s = _T("{s} - env \"{k}\"=\"{v}\"").format(
                            s = __s, k = k, v = v)
                elif (isinstance(env, tuple) or isinstance(env, list)):
                    for envtuple in env:
                        k = _Tnec(envtuple[0])
                        v = _Tnec(envtuple[1])
                        __s = _T("{s} - env \"{k}\"=\"{v}\"").format(
                            s = __s, k = k, v = v)
            except:
                pass

            return __s

        def wrprocstat(fp, cmd, args, env, status, signalled, sstr):
            __p = self.prefixX
            wrlinepfx(fp, __p,
                _T("status: "
                "cmd='{cmd}' "
                "code='{code}' "
                "signalled='{sig}' "
                "status_string='{sstr}'"
                "{argenv}\n").format(
                    cmd = cmd, code = status,
                    sig = signalled, sstr = sstr,
                    argenv = s_procdata(args, env))
                )

        def wrprocdata(fp, cmd, args, env):
            __p = self.prefixX
            wrlinepfx(fp, __p,
                _T("    status: cmd='{cmd}' {argenv}\n").format(
                    cmd = cmd, argenv = s_procdata(args, env))
                )

        def wrexecfail(fp, cmd, args, env, nerr, serr):
            __p = self.prefixX
            wrlinepfx(fp, __p, _T(" execfail {n} \"{s}\":\n").format(
                n = nerr, s = _Tnec(serr)))
            wrprocdata(fp, cmd, args, env)

        def doexecfail(fp, cmd, args, env, nerr, serr):
            wrexecfail(fp, cmd, args, env, nerr, serr)
            for __p, __s, __b, __x in self.procstat:
                self.kill(signal.SIGINT, __p)
            self._child_wait_all()

        if fpid == 0:
            # clear proc list
            self.procstat = []

            # for reference in methods
            self.root = False

            # start new group
            mpid = os.getpid()
            try:
                pgrp = os.getpgrp()
                if pgrp != mpid:
                    os.setpgrp()
                pgrp = os.getpgrp()
            except OSError as e:
                os._exit(self.pgrp_err_status)

            # success?
            if mpid != pgrp:
                os._exit(self.pgrp_err_status)

            self._child_sigs_setup()

            os.close(rfd)

            # make file-pointer-like object
            ndup = 3
            if wfd < ndup:
                os.dup2(wfd, ndup)
                os.close(wfd)
                wfd = ndup
            fw = os.fdopen(wfd, self.open_mode_w, 0)

            exrfd1, exwfd1 = os.pipe()
            exrfd2, exwfd2 = os.pipe()

            # do stdin, making pipeline as needed
            ifd = exrfd1
            pipelist = [self.params]
            lastparams = self.params

            # ChildProcParams may be a linked list with
            # member infd as the next-pointer, but they
            # need to be handled tail-first, so collect
            # them in a list[] using .insert(0,) to reverse
            fd = self.params.infd
            while isinstance(fd, ChildProcParams):
                pipelist.insert(0, fd)
                lastparams = fd
                fd = fd.infd

            # otherwise member infd should be a file descriptor
            if isinstance(fd, int) and fd > 0:
                os.dup2(fd, 0)
                if lastparams != None:
                    lastparams.close_infd()

            # fork/exec pipe list items in _mk_pipe_proc()
            for fd in pipelist:
                ifd, pid, cmd, parms = self._mk_pipe_proc(
                                        fd, exwfd1, exwfd2)
                # (-1, -errno, sys-errno-string, paramobj)
                if ifd < 0:
                    _dbg(
                        _T("EXEC FAIL {cmd} -- \"{s}\" ({e})").format(
                            cmd = parms.xcmd, e = -pid, s = cmd)
                        )
                    doexecfail(fw,
                        parms.xcmd, parms.xcmdargs, parms.xcmdenv,
                        -pid, cmd)
                    os._exit(self.exec_err_status)
                elif ifd > 0:
                    os.dup2(ifd, 0)
                    os.close(ifd)
                    self.procstat.append((pid, -1, False, parms))
                    ifd = 0

            if exrfd1 != ifd:
                os.close(exrfd1)
                exrfd1 = ifd

            fpid = pid

            os.close(exwfd1)
            os.close(exwfd2)
            # The FILE* equivalents are opened with 0 third arg to
            # disable buffering, to work in concert with poll(),
            # and provide parent timely info
            fr1 = os.fdopen(exrfd1, self.open_mode_r, 0)
            fr2 = os.fdopen(exrfd2, self.open_mode_r, 0)

            flist = []
            flist.append(exrfd1)
            flist.append(exrfd2)

            errbits = select.POLLERR|select.POLLHUP|select.POLLNVAL
            pl = select.poll()
            pl.register(flist[0], select.POLLIN|errbits)
            pl.register(flist[1], select.POLLIN|errbits)

            pfx = self.prefix1
            lin = _T("")
            while True:
                try:
                    rl = pl.poll(None)
                except select.error as e:
                    (err, msg) = e
                    if err == eintr:
                        continue
                    break

                if len(rl) == 0:
                    break

                lin = _T("")
                for fd, bits in rl:
                    if fd == exrfd1:
                        pfx = self.prefix1
                        frN = fr1
                    elif fd == exrfd2:
                        pfx = self.prefix2
                        frN = fr2
                    else:
                        continue

                    if bits & select.POLLIN:
                        lin = frN.readline(self.szlin)

                        if len(lin) > 0:
                            wrlinepfx(fw, pfx, lin)
                        else:
                            flist.remove(fd)
                            pl.unregister(fd)
                    else:
                        flist.remove(fd)
                        pl.unregister(fd)

                if len(flist) == 0:
                    break

            stat = self._child_wait_all()

            if stat < 0:
                fw.close()

                # bad failure, like pid n.g.
                os._exit(1)
            else:
                highstat = stat

                for pid, stat, sig, parms in self.procstat:
                    if parms == None:
                        cmd = _T("[unknown command]")
                        aa  = []
                        ae  = []
                    else:
                        cmd = parms.xcmd
                        aa  = parms.xcmdargs
                        ae  = parms.xcmdenv
                        # cannot allow linebreaks in args or env here
                        for i in range(len(aa)):
                            tstr  = aa[i].replace(_T("\n"), _T("<NL>"))
                            aa[i] = tstr.replace(_T("\r"), _T("<CR>"))
                        aeo = self._mk_sane_env(ae)
                        parms.close_infd()

                    sstr = self.__class__.status_string(stat, sig)
                    wrprocstat(fw, cmd, aa, aeo, stat, sig, sstr)

                if sig:
                    fw.close()
                    # want to provide same status to parent, so
                    # suicide with same signal -- python does not
                    # seem to have {os,signal}.raise() so os.kill()
                    self._child_sigs_defaults()
                    os.kill(os.getpid(), stat)
                    signal.pause()
                    # should not reach here!
                    os._exit(1)
                else:
                    fw.close()
                    os._exit(stat)

        else:
            os.close(wfd)
            self.error_tuple = None
            self.procstat[0] = (fpid,
                self.procstat[0][1],
                self.procstat[0][2],
                self.procstat[0][3])
            return (fpid, rfd)

        # Not reached
        self.error_tuple = (0, _T("error: internal logic error"))
        return self.error_tuple

    # 'protected' proc for self.go() -- fork and exec for pipleline --
    # return (child-stdout-fd, child-pid, command, paramobj) on success,
    # or (-1, -errno, sys-errno-string, paramobj) on failure
    def _mk_pipe_proc(self, paramobj, fd1, fd2):
        xcmd = paramobj.xcmd
        xcmdargs = paramobj.xcmdargs
        xcmdenv = paramobj.xcmdenv

        is_path = os.path.split(xcmd)
        if len(is_path[0]) > 0:
            is_path = True
        else:
            is_path = False

        try:
            rfd, wfd = os.pipe()
        except OSError as e:
            return (-1, -e.errno, e.strerror, paramobj)

        try:
            fpid = os.fork()
            if fpid > 0:
                _dbg(_T("_mk_pipe_proc {this} new pid {new}").format(
                    this = os.getpid(), new = fpid))
        except OSError as e:
            os.close(rfd)
            os.close(wfd)
            return (-1, -e.errno, e.strerror, paramobj)

        if fpid == 0:
            os.close(rfd)

            if wfd != 1:
                os.dup2(wfd, 1)
                os.close(wfd)

            os.close(fd1)

            if fd2 != 2:
                os.dup2(fd2, 2)
                os.close(fd2)

            self._child_sigs_defaults()
            try:
                self._putenv_cntnr(xcmdenv)
                if is_path:
                    os.execv(xcmd, xcmdargs)
                else:
                    os.execvp(xcmd, xcmdargs)
                os._exit(self.exec_wtf_status)
            except OSError as e:
                os._exit(self.exec_err_status)

        # parent
        else:
            os.close(wfd)

        return (rfd, fpid, xcmd, paramobj)

    def _putenv_cntnr(self, cntnr):
        try:
            if (isinstance(cntnr, tuple) or
                isinstance(cntnr, list)):
                for envtuple in cntnr:
                    os.environ[envtuple[0]] = envtuple[1]
            elif isinstance(cntnr, dict):
                for k in cntnr:
                    os.environ[k] = cntnr[k]
        except:
            pass

    def _mk_sane_env(self, cntnr):
        o = []
        try:
            if (isinstance(cntnr, tuple) or
                isinstance(cntnr, list)):
                for ctuple in cntnr:
                    k = ctuple[0]
                    v = ctuple[1]
                    tstr  = v.replace(_T("\n"), _T("<NL>"))
                    v = tstr.replace(_T("\r"), _T("<CR>"))
                    o.append((k, v))
            elif isinstance(cntnr, dict):
                for k in cntnr:
                    v = cntnr[k]
                    tstr  = v.replace(_T("\n"), _T("<NL>"))
                    v = tstr.replace(_T("\r"), _T("<CR>"))
                    o.append((k, v))
        except:
            pass

        return o

    def null_cb_go_and_read(self, n, s):
        """Default callback for go_and_read()
        """
        return 0

    def kill_for_cb_go_and_read(self, pid, n):
        """Killer for go_and_read() -- pass signal number in n
        """
        if n > 0:
            os.kill(pid, n)

    """
    fork() and read output -- return False on fork error, else True,
                              and then wait() and then
                              get_status() should be called,
                              then get_read_lists() (possibly
                              reset_read_lists() after that)
                              - Optionally pass a callback in cb that
                              takes two args: int stream number
                                (1, or 2, or -1 for unexpected),
                                and string (a line just read)
                                - cb should return 0 or signum
                                to kill() with
    """
    def go_and_read(self, cb = None):
        fpid, rfd = self.go()
        if self.go_return_ok(fpid, rfd):
            return self.read_curchild(rfd, cb)

        # N.G.
        return False

    def read_curchild(self, rfd, cb = None):
        return self.read(self.procstat[-1][0], rfd, cb)

    def read(self, fpid, rfd, cb = None):
        if not self.go_return_ok(fpid, rfd):
            return False

        fr = os.fdopen(rfd, self.open_mode_r, 0)

        if cb == None:
            cb = self.null_cb_go_and_read

        l1 = len(self.prefix1)
        l2 = len(self.prefix1)
        lX = len(self.prefixX)
        while True:
            lin = _Tnec(fr.readline(self.szlin + 3))

            if len(lin) > 0:
                if self.prefix1 == lin[:l1]:
                    l = lin[l1:]
                    self.rlin1.append(l)
                    self.kill_for_cb_go_and_read(fpid, cb(1, l))
                elif self.prefix2 == lin[:l2]:
                    l = lin[l2:]
                    self.rlin2.append(l)
                    self.kill_for_cb_go_and_read(fpid, cb(2, l))
                elif self.prefixX == lin[:lX]:
                    l = lin[lX:]
                    self.rlinx.append(l)
                    self.kill_for_cb_go_and_read(fpid, cb(-1, l))
                else:
                    self.rlinx.append(lin)
                    self.kill_for_cb_go_and_read(fpid, cb(-1, lin))
            else:
                break

        fr.close()
        return True


"""
RepairedMDDialog -- a multi-directory selection dialog, deriving
                    from wxPython:agw.MultiDirDialog to repair
                    broken GTK2 implementation of underlying
                    wxTreeCtrl by removing misguided false items
                    "Home directory" etc. -- also repairs bug
                    in wxPython:agw.MultiDirDialog that returns
                    items under '/' prefixed with '//'.
                    Furthermore, parameter defaults are tuned
                    to my preferences.
"""
class RepairedMDDialog(MDD.MultiDirDialog):
    bugstr = (_T('Home Directory'), _T('Home directory'), _T('Desktop'))

    def __init__(self,
                 parentwnd,
                 prompt = _("Choose one or more directories:"),
                 tit = _("Browse For Directories:"),
                 defpath = _T('/'),
                 wxstyle = wx.DD_DEFAULT_STYLE,
                 agwstyle = (MDD.DD_DIR_MUST_EXIST|
                             MDD.DD_MULTIPLE),
                 locus = wx.DefaultPosition,
                 dims = wx.DefaultSize,
                 tag = _T("repaired_mddialog")):
        MDD.MultiDirDialog.__init__(self,
                                    parent = parentwnd,
                                    message = prompt,
                                    title = tit,
                                    defaultPath = defpath,
                                    style = wxstyle,
                                    agwStyle = agwstyle,
                                    pos = locus,
                                    size = dims,
                                    name = tag)

        self.__repair_tree()

        self.Bind(wx.EVT_SYS_COLOUR_CHANGED, self.on_sys_color)


    #private
    def on_sys_color(self, event):
        event.Skip()

        f = lambda wnd: self._color_proc_per_child(wnd)
        invoke_proc_for_window_children(self, f)

    def _color_proc_per_child(self, wnd):
        fclr = _msg_obj.GetForegroundColour()
        bclr = _msg_obj.GetBackgroundColour()

        wnd.SetForegroundColour(fclr)
        wnd.SetBackgroundColour(bclr)

        wnd.SetThemeEnabled(True)
        wnd.Refresh(True)
        wnd.Update()

    # Protected: override MDD.MultiDirDialog method
    def CreateButtons(self):
        import wx.lib.buttons as buttons

        if self.agwStyle == 0:
            self.newButton = buttons.ThemedGenBitmapTextButton(
                self, wx.ID_NEW, MDD._new.GetBitmap(),
                _("Make New Folder"), size=(-1, 28))
        else:
            self.newButton = wx.StaticText(
                self, wx.ID_NEW, _T("/\\_o0o_/\\"),
                wx.DefaultPosition, wx.DefaultSize, 0)

        self.okButton = buttons.ThemedGenBitmapTextButton(
            self, wx.ID_OK, MDD._ok.GetBitmap(),
            _("OK"), size=(-1, 28))
        self.cancelButton = buttons.ThemedGenBitmapTextButton(
            self, wx.ID_CANCEL, MDD._cancel.GetBitmap(),
            _("Cancel"), size=(-1, 28))

    # Private: fix the tree control
    def __repair_tree(self):
        if _T("HOME") in os.environ:
            init_dir = os.environ[_T("HOME")]
        else:
            # Give up right here
            return

        bug = self.bugstr
        dir_ctrl = self.dirCtrl
        treectrl = dir_ctrl.GetTreeCtrl()

        item_id = treectrl.GetFirstVisibleItem()

        # WTF?
        wtfstr = _T('Sections')
        wtflen = len(wtfstr)
        if treectrl.GetItemText(item_id)[:wtflen] == wtfstr:
            (item_id, cookie) = treectrl.GetFirstChild(item_id)

        rm_items = []

        while item_id:
            lbl = treectrl.GetItemText(item_id)
            if s_eq(lbl, 'Desktop'):
                rm_items.insert(0, item_id)
            elif lbl in bug:
                treectrl.SetItemText(item_id, init_dir)
            item_id = treectrl.GetNextSibling(item_id)

        for item_id in rm_items:
            treectrl.DeleteChildren(item_id)
            treectrl.Delete(item_id)

        treectrl.UnselectAll()
        self.folderText.SetValue(_T(''))


    # Use in place of GetPaths()
    def GetRepairedPaths(self):
        if _T("HOME") in os.environ:
            init_dir = os.environ[_T("HOME")]
        else:
            init_dir = False

        bug = self.bugstr
        # Handle bugs and implementation flaws:
        # wxTreeCtrl is misguidedly flawed in that it
        # always starts with items "Home directory" and
        # "Desktop" and actually returns those strings
        # without translation to a real filesystem name,
        # which is *massively* brain dead^W^WThe Wrong Thing.
        # Also, from MDD.MultiDirDialog, full Unix
        # paths are returned starting with '//' (rather
        # than '/').
        # Therefore, partially work around with replacement;
        # but this can easily break -- in fact I guess the
        # brain dead strings are subject to i18 translation --
        # Ah ha, there is a 'ticket' open on this:
        #   http://trac.wxwidgets.org/ticket/17190
        # As of this writing, 2016/01/19, trac says "three months ago"
        # (instead of giving a date: sheesh) and there is
        # no sign of anyone having looked at it.
        pts = self.GetPaths()
        str_machd = _T('Macintosh HD')
        dir_machd = str_machd + _T('/')
        len_machd = len(str_machd)
        rm_idx = []
        for i in range(len(pts)):
            p = pts[i]
            if s_eq(p[:2], '//'):
                p = p.replace(_T('//'), _T('/'))
            # the 'Macintosh HD' stuff is *untested*!
            elif p[:len_machd] == str_machd:
                if p == str_machd or p == dir_machd:
                    rm_idx.insert(0, i)
                    continue
                if s_eq(p[len_machd], '/'):
                    p = p[len_machd:]
            else:
                for misguided in bug:
                    if p[:len(misguided)] == misguided:
                        if init_dir:
                            p = p.replace(misguided, init_dir)
                        else:
                            m = _(
                              "'HOME' env. var. needed; but not found")
                            raise RepairedMDDialog.Unfixable(m)
                        break

            pts[i] = p

        for i in rm_idx:
            del pts[i]

        return pts

    class Unfixable(Exception):
        def __init__(self, args):
            Exception.__init__(self, args)


"""
AMsgWnd -- a text output window to appear within the ASashWnd
"""
class AMsgWnd(wx.TextCtrl):
    def __init__(self, parent, wi, hi, id = -1):
        wx.TextCtrl.__init__(self,
            parent, id, "", wx.DefaultPosition, (wi, hi),
            wx.TE_MULTILINE|wx.SUNKEN_BORDER|wx.TE_RICH|wx.HSCROLL)

        self.parent = parent

        self.scroll_end = False
        self.scroll_end_user_set = False
        self.showpos = 0

        self.default_text_style = self.GetDefaultStyle()

        # wx 3.x: self.default_text_style.GetFont() returns
        # an invalid font, making self.orig_font.GetPointSize()
        # throw an exception. Workaround:
        if is_wxpy_v3():
            fntsz = 9
            self.orig_font = wx.Font(
                fntsz,
                wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL
            )
            self.default_text_style.SetFont(self.orig_font)
            self.SetDefaultStyle(self.default_text_style)
        else:
            self.orig_font = self.default_text_style.GetFont()
            fntsz = self.orig_font.GetPointSize()

        self.mono_font = wx.Font(
            fntsz,
            wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL
        )

        self.showpos = self.GetLastPosition()

        global _msg_obj
        _msg_obj = self
        global _msg_obj_init_is_done
        _msg_obj_init_is_done = True
        global msg_default_color

        msg_default_color = self.GetForegroundColour()

        # Scroll top/bottom are not working -- apparently
        # only for scrolled windows and scroll bars --
        # but leave code in place in case this changes,
        # or some workaround presents itself.
        self.Bind(wx.EVT_SCROLLWIN_TOP, self.on_scroll_top)
        self.Bind(wx.EVT_SCROLLWIN_BOTTOM, self.on_scroll_bottom)
        self.Bind(wx.EVT_SYS_COLOUR_CHANGED, self.on_sys_color)

        msg_GOOD(_("Welcome to {prog}.").format(prog = PROG))
        msg_line_INFO(_("Using wxPython {pyvers}.\n\n").format(
            pyvers = wx.version()))
        self.print_color_legend()


    #private
    def on_sys_color(self, event):
        event.Skip()

        global msg_default_color

        bclr = self.GetBackgroundColour()
        fclr = msg_default_color = self.GetForegroundColour()

        self.default_text_style.SetBackgroundColour(bclr)
        self.default_text_style.SetTextColour(fclr)
        self.SetDefaultStyle(self.default_text_style)

        msg_line_INFO(_("Graphical interface color change detected. "))
        self.print_color_legend()

    def print_color_legend(self):
        msg_INFO(_("Message window line colour legend:"))
        msg_line_GOOD(_("This is the 'good outcome' color"))
        msg_line_WARN(_("This is the 'warning' colour"))
        msg_line_ERROR(_("This is the 'error occurred' color"))
        msg_line_INFO(_("This is the 'informational line' colour"))
        msg_line_(_(
            "This is the color of lines from child program output\n"
            ))


    def on_scroll_top(self, event):
        if event.GetOrientation() == wx.HORIZONTAL:
            return
        self.scroll_end = False
        self.scroll_end_user_set = False
        self.showpos = 0

    def on_scroll_bottom(self, event):
        if event.GetOrientation() == wx.HORIZONTAL:
            return
        self.scroll_end = True
        self.scroll_end_user_set = False
        self.showpos = self.GetLastPosition()

    # end private
    def set_mono_font(self):
        self.default_text_style.SetFont(self.mono_font)
        self.SetDefaultStyle(self.default_text_style)


    def set_default_font(self):
        self.default_text_style.SetFont(self.orig_font)
        self.SetDefaultStyle(self.default_text_style)


    def conditional_scroll_adjust(self):
        nlin = self.GetNumberOfLines()
        if nlin <= 0:
            return

        llin = self.GetLineLength(nlin - 1)

        if self.scroll_end == True and llin >= 0:
            self.SetInsertionPointEnd()
            self.showpos = self.GetLastPosition() - llin

        self.ShowPosition(self.showpos)

    def get_msg_obj(self):
        return self

    def set_scroll_to_end(self, true_or_false):
        if true_or_false == True or true_or_false == False:
            self.scroll_end = true_or_false
            self.scroll_end_user_set = True

    def SetValue(self, val):
        wx.TextCtrl.SetValue(self, val)
        self.conditional_scroll_adjust()

    def SetValueColored(self, val, clr):
        # Oy, GetDefaultStyle() does not return
        # a useful value! (GTK2)
        #saved = self.GetDefaultStyle()
        self.SetDefaultStyle(wx.TextAttr(clr))
        self.SetValue(val)
        self.SetDefaultStyle(self.default_text_style)
        #self.SetDefaultStyle(saved)

    def AppendText(self, val):
        wx.TextCtrl.AppendText(self, val)
        self.conditional_scroll_adjust()

    def AppendTextColored(self, val, clr):
        # Ouch, GetDefaultStyle() does not return
        # a useful value! (GTK2)
        #saved = self.GetDefaultStyle()
        self.SetDefaultStyle(wx.TextAttr(clr))
        self.AppendText(val)
        self.SetDefaultStyle(self.default_text_style)
        #self.SetDefaultStyle(saved)



"""
AFileListCtrl -- Control to display additional file/dir selections
"""
class AFileListCtrl(wx.ListCtrl, listmix.ColumnSorterMixin):
    def __init__(self, parent, gist, id = -1, size = wx.DefaultSize):
        wx.ListCtrl.__init__(self, parent, id,
            wx.DefaultPosition, size,
            wx.LC_REPORT|wx.LC_HRULES|wx.LC_VRULES)

        self.parent = parent
        self.logger = gist.get_msg_wnd

        if phoenix:
            insert_column_it = self.InsertColumn
        else:
            insert_column_it = self.InsertColumnItem

        li = wx.ListItem()
        li.SetImage(-1)
        # TRANSLATORS: 'name' is a file name
        li.SetText(_("Name"))
        insert_column_it(0, li)
        self.SetColumnWidth(0, 192)
        # TRANSLATORS: This is a full path with file name (if reg. file)
        li.SetText(_("Full Path"))
        li.SetAlign(wx.LIST_FORMAT_LEFT)
        insert_column_it(1, li)
        self.SetColumnWidth(1, 1024)

        # images for column click sort - see wxPython demos/ListCtrl.py
        self.imgl = wx.ImageList(16, 16)
        self.imgup = self.imgl.Add(SmallUpArrow.GetBitmap())
        self.imgdn = self.imgl.Add(SmallDnArrow.GetBitmap())
        self.SetImageList(self.imgl, wx.IMAGE_LIST_SMALL)
        # also for sort, init mixin
        listmix.ColumnSorterMixin.__init__(self, 2)
        self.itemDataMap = {}
        self.itemDataMap_ix = 0

        # context menu id's
        self.sel_all_id = gist.get_new_idval()
        self.rm_item_id = gist.get_new_idval()
        self.empty_list = gist.get_new_idval()

        self.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
        self.Bind(wx.EVT_MENU, self.on_event_menu)
        self.Bind(wx.EVT_SYS_COLOUR_CHANGED, self.on_sys_color)


    #private
    def on_sys_color(self, event):
        event.Skip()

        f = lambda wnd: self._color_proc_per_child(wnd)
        invoke_proc_for_window_children(self, f)

    def _color_proc_per_child(self, wnd):
        fclr = _msg_obj.GetForegroundColour()
        bclr = _msg_obj.GetBackgroundColour()

        wnd.SetForegroundColour(fclr)
        wnd.SetBackgroundColour(bclr)

        wnd.SetThemeEnabled(True)
        wnd.Refresh(True)
        wnd.Update()

    def sel_all(self):
        n = self.GetItemCount()
        msk = wx.LIST_STATE_SELECTED
        for i in range(0, n):
            self.SetItemState(i, msk, msk)

    def rm_selected(self):
        msk = wx.LIST_STATE_SELECTED
        while True:
            i = self.GetNextItem(-1, wx.LIST_NEXT_ALL, msk)
            if i < 0:
                return
            ix = self.GetItemData(i)
            del self.itemDataMap[ix]
            self.DeleteItem(i)

    def rm_all(self):
        self.DeleteAllItems()
        self.itemDataMap = {}
        self.itemDataMap_ix = 0

    def add_file(self, path, idx = -1):
        if idx < 0:
            idx = self.GetItemCount()
        return self.add_item_color(path, idx)

    # Note this checks paths with {l,}stat -- add_item_color
    # should do it -- TODO later
    def add_multi_files(self, paths, idx = -1):
        if idx < 0:
            idx = self.GetItemCount()

        for p in paths:
            st = x_lstat(p)
            # x_lstat() does print an error message
            if st == None:
                continue

            if stat.S_ISLNK(st.st_mode):
                msg_line_WARN(_("Warning:"))
                msg_(_(" '{0}' is a symlink;"
                    " symlinks are recreated, not followed."
                    ).format(p))
                idx = self.add_slink(p, idx) + 1
            elif stat.S_ISDIR(st.st_mode):
                if s_eq(p, "/"):
                    msg_line_ERROR(_(
                        "Error: '/' is the root directory;"
                        " you must be joking."))
                    continue
                idx = self.add_dir(p, idx) + 1
            elif stat.S_ISCHR(st.st_mode):
                msg_line_WARN(_("Warning:"))
                msg_(_(" '{0}' is a raw device node;"
                    " it will be copied, but do you"
                    " really want it?").format(p))
                idx = self.add_spcl(p, idx) + 1
            elif stat.S_ISBLK(st.st_mode):
                msg_line_WARN(_("Warning:"))
                msg_(_(" '{0}' is a block device node;"
                    " it will be copied, but do you"
                    " really want it?").format(p))
                idx = self.add_spcl(p, idx) + 1
            elif stat.S_ISFIFO(st.st_mode):
                msg_line_WARN(_("Warning:"))
                msg_(_(" '{0}' is a FIFO pipe;"
                    " it will be copied, but do you"
                    " really want it?").format(p))
                idx = self.add_spcl(p, idx) + 1
            elif stat.S_ISSOCK(st.st_mode):
                msg_line_ERROR(_(
                    "Error: '{0}' is a unix domain socket;"
                    " it will not be copied.").format(p))
                continue
            elif stat.S_ISREG(st.st_mode):
                idx = self.add_file(p, idx) + 1
            else:
                msg_line_WARN(_("Warning:"))
                msg_(_(" '{0}' is an unknown fs object type;"
                    " a copy will be attempted if it is not removed"
                    " from the list").format(p))
                idx = self.add_file(p, idx) + 1

        return idx

    def add_dir(self, path, idx = -1):
        if idx < 0:
            idx = self.GetItemCount()
        return self.add_item_color(path, idx, msg_blue_color)

    def add_slink(self, path, idx = -1):
        if idx < 0:
            idx = self.GetItemCount()
        return self.add_item_color(path, idx, msg_green_color)

    def add_spcl(self, path, idx = -1):
        if idx < 0:
            idx = self.GetItemCount()
        return self.add_item_color(path, idx, msg_yellow_color)


    def add_multi_dirs(self, paths, idx = -1):
        if idx < 0:
            idx = self.GetItemCount()

        for p in paths:
            idx = self.add_dir(p, idx) + 1

        return idx

    def add_item_color(self, path, idx, color = None):
        nm = os.path.basename(path)

        im = self.itemDataMap_ix + 1
        self.itemDataMap_ix = im
        self.itemDataMap[im] = (nm, path)

        if phoenix:
            # wxPhoenix: InsertStringItem is deprecated
            ii = self.InsertItem(idx, nm)
        else:
            ii = self.InsertStringItem(idx, nm)

        if color != None:
            self.SetItemTextColour(ii, color)

        if phoenix:
            # wxPhoenix: SetStringItem is deprecated
            self.SetItem(ii, 1, path)
        else:
            self.SetStringItem(ii, 1, path)

        self.SetItemData(ii, im)

        return ii

    def get_item(self, idx = 0):
        if idx < 0:
            return None

        n = self.GetItemData(idx)

        if n in self.itemDataMap:
            return self.itemDataMap[n][1]

        return None

    def get_all_items(self):
        n = self.GetItemCount()
        l = []

        for i in range(0, n):
            l.append(self.get_item(i))

        return l

    # for sort mixin
    def GetListCtrl(self):
        return self

    # for sort mixin
    def GetSortImages(self):
        return (self.imgdn, self.imgup)

    def on_context_menu(self, event):
        point = event.GetPosition()
        if point.x == -1 and point.y == -1:
            size = self.GetSize()
            point.x = size.x / 2
            point.y = size.y / 2
        else:
            point = self.ScreenToClient(point)

        self.show_context_menu(point)

    def show_context_menu(self, pos):
        menu = wx.Menu()
        menu.Append(self.sel_all_id, _("Select All"))
        menu.AppendSeparator()
        menu.Append(self.rm_item_id, _("Remove Selected Items"))
        menu.Append(self.empty_list, _("Remove All"))
        self.PopupMenu(menu, pos)

    def on_event_menu(self, event):
        id = event.GetId()

        if id == self.sel_all_id:
            self.sel_all()
        elif id == self.rm_item_id:
            self.rm_selected()
        elif id == self.empty_list:
            self.rm_all()


"""
ABasePane -- a base class for scrolling panels used here
(NOTE: alternative wxPython wx.lib.scrolledpanel -- imported
as scrollpanel here -- has some subtle advantages, e.g. the
volume info panel, which is always larger than visible space and
therefore has vertical a scroll bar, will auto-scroll to reveal
a newly focused control that had been hidden when tabbing
through controls; wx.ScrolledWindow does not do so. BUT,
a major disadvantage: click any text text field and it might
scroll to bottom! N.G.)
.
This class also provides code for transfering child focus to a peer
window based on this -- see code starting at comment
    # for derived classes hacking control focus behavior
The focus transfer code is useful for wxPy (wxWidgets) 2.8.x only!
In wxPy (wxWidgets) 3.0.x tab traversal is broken for children of
Sash{Layout}Window (used in this prog) and maybe others.  Using C++,
tabbing is not technically broken because templates provide tabbing
code and programs can use, e.g.:
    typedef wxNavigationEnabled<wxSashWindow> ASashWnd_base;
    typedef wxNavigationEnabled<wxSashLayoutWindow> ASashWnd_laywin;
***but*** wxPy 3.0.x has not done this!  Therefore, using panels, and
expecting panel-parented controls to have tab traversal, will only
fail if panels are children of wxSashLayoutWindow.  Even using
<control>.SetFocus() fails, so tab traversal cannot be (re)implemented!
Still hoping I missed something, or can find a workaround.
"""
class ABasePane(wx.ScrolledWindow):
#class ABasePane(scrollpanel.ScrolledPanel):
    def __init__(self, parent, gist, wi, hi, id = -1):
        wx.ScrolledWindow.__init__(self,
        #scrollpanel.ScrolledPanel.__init__(self,
                        parent, id,
                        style = wx.CLIP_CHILDREN |
                                wx.FULL_REPAINT_ON_RESIZE
                        )
        self.parent = parent
        self.core_ld = gist
        self.sz = wx.Size(wi, hi)

        self.scrollrate_x = 10
        self.scrollrate_y = 10

        self.SetScrollRate(self.scrollrate_x, self.scrollrate_y)
        self.SetVirtualSize(self.sz)

        # control widget windows subject to enable_all()
        self.child_wnds = []
        self.child_wnds_prev_state = {}

        self.focus_partner_fore = None
        self.focus_partner_back = None

        self.keep_focus = True
        self.forward_focus = True

        # for focus transfer to neighbor
        self.focus_terminals = {"first" : None, "last" : None}

    # for derived classes hacking control focus behavior --
    # this only works for wxPy 2.8; wxPy 3.0 is broken re. focus
    # and traversal, failing to use the wx 3.x Navigation templates
    # for wxSash{,Layout)Window
    def take_focus(self, forward = True):
        if forward:
            if self.focus_terminals["first"]:
                self.focus_terminals["first"].SetFocus()
                return True
        else:
            # wxWindow::GetPrevSibling is new in 2.8.8
            # Sigh. Test wxPy 2.8.12, and wnd.GetPrevSibling()
            # raises exception.
            try:
                wnd1st = self.focus_terminals["first"]
                wnd = wnd1st
                while wnd:
                    wnd = wnd.GetPrevSibling()
                    if wnd == wnd1st:
                        break
                    if wnd and wnd.IsEnabled():
                        break

                if wnd:
                    wnd.SetFocus()
                    return True
            except:
                if self.focus_terminals["first"]:
                    self.focus_terminals["first"].SetFocus()
                    return True

        return False

    # for derived classes hacking control focus behavior
    def give_focus(self, forward = True):
        if forward and self.focus_partner_fore:
            return self.focus_partner_fore.take_focus(forward)
        elif self.focus_partner_back:
            return self.focus_partner_back.take_focus(forward)

        return False

    def set_focus_partner_fore(self, wnd):
        self.focus_partner_fore = wnd

    def set_focus_partner_back(self, wnd):
        self.focus_partner_back = wnd

    # tab focus hacks; derived classes can Bind() handlers:
    def set_focus_first(self, event):
        forward = self.forward_focus
        self.forward_focus = False
        if self.keep_focus:
            self.keep_focus = False
            event.Skip()
        else:
            self.keep_focus = True
            self.give_focus(forward)

    def kill_focus_first(self, event):
        #print "KILL FOCUS 1"
        event.Skip()

    def set_focus_last(self, event):
        #print "SET FOCUS 2"
        event.Skip()

    def kill_focus_last(self, event):
        event.Skip()
        if not self.focus_terminals["first"]:
            return

        try:
            fwnd = wx.Window_FindFocus()
        except AttributeError:
            fwnd = wx.Window.FindFocus()
        except:
            fwnd = False

        if fwnd:
            i1 = self.focus_terminals["first"].GetId()
            i2 = fwnd.GetId()
            if i1 != i2:
                self.forward_focus = True
                return

        self.forward_focus = False

    # help theme compat
    def init_for_children(self):
        f = lambda wnd: wnd.SetThemeEnabled(True)
        invoke_proc_for_window_children(self, f)

    def add_child_wnd(self, wnd):
        if not wnd in self.child_wnds:
            self.child_wnds.append(wnd)

    # call wx Window->Enable(benabled) on all of self.child_wnds
    # that are not excluded by presence in tuple not_these
    def enable_all(self, benabled = True, not_these = ()):
        for c in self.child_wnds:
            is_en = c.IsEnabled()
            self.child_wnds_prev_state[c] = is_en
            if c in not_these:
                continue

            c.Enable(benabled)

    # restore saved state
    def restore_all(self, not_these = ()):
        for c in self.child_wnds:
            if c in not_these:
                continue
            if c in self.child_wnds_prev_state:
                c.Enable(self.child_wnds_prev_state[c])

    # let methods attach to wx.Panel children
    def attach_methods(self, pnl):
        pnl.add_child_wnd = self.add_child_wnd
        pnl.enable_all = self.enable_all
        pnl.restore_all = self.restore_all


"""
AVolInfPane -- Pane window for operation target volume info fields setup
"""
class AVolInfPane(ABasePane):
    def __init__(self, parent, gist, wi, hi, id = -1):
        ABasePane.__init__(self, parent, gist, wi, hi, id)

        self.SetMinSize(wx.Size(self.sz.width, 64))
        self.panel = AVolInfPanePanel(self, gist,
            wx.Size(self.sz.width, self.sz.height * 2),
            id = gist.get_new_idval())
        self.SetVirtualSize(self.panel.GetSize())

    def get_panel(self):
        return self.panel

    def config_rd(self, config):
        self.get_panel().config_rd(config)

    def config_wr(self, config):
        self.get_panel().config_wr(config)

"""
AVolInfPanePanel -- Panel window for operation volume info fields setup
"""
class AVolInfPanePanel(wx.Panel):
    def __init__(self, parent, gist, size, id = -1):
        wx.Panel.__init__(self, parent, id, wx.DefaultPosition, size,
                          style = wx.CLIP_CHILDREN |
                                  wx.TAB_TRAVERSAL |
                                  wx.FULL_REPAINT_ON_RESIZE)
        self.parent = parent
        self.parent.attach_methods(self)

        self.core_ld = gist
        self.core_ld.set_vol_wnd(self)

        self.ctls = []

        inf_keys, inf_map, inf_vec = self.core_ld.get_vol_datastructs()

        # top level sizer
        self.mainszr = wx.BoxSizer(wx.VERTICAL)
        self.mainszr.SetMinSize((size.width, wx.DefaultSize.height))

        type_optChoices = []
        type_optChoices.append(_("copy from source"))
        type_optChoices.append(_("hand edit"))

        self.type_opt = wx.RadioBox(
            self, gist.get_new_idval(), _("select field content"),
            wx.DefaultPosition, wx.DefaultSize, type_optChoices, 1,
            wx.RA_SPECIFY_ROWS)
        self.type_opt.SetToolTip(
            wx.ToolTip(_(
                "These fields allow editing of DVD volume "
                "information when the 'advanced' backup "
                "type is selected. (With the 'simple' backup type "
                "volume information is copied as is.)\n"
                "\n"
                "Select whether to use DVD volume information "
                "as found on the source DVD with \"copy from source\", "
                "or use a hand edited volume information set "
                "with \"hand edit\".\n"
                "\n"
                "The hand-edit fields will remain if you change the "
                "source disc, so they may be useful as a starter "
                "for another backup.\n"
                "\n"
                "The \"copy from source\" fields may be edited, and "
                "changes will apply to burns until the source disc "
                "check (the 'Check' button) is done again. Then these "
                "fields will be overwritten.\n"
                "\n"
                "In either case, it is best to ensure that the "
                "'Volume ID' field has a useful value, with no spaces, "
                "since this is often used as a label for the mounted "
                "disc."
                )
            ))
        self.add_child_wnd(self.type_opt)

        # type opt in top level sizer
        self.mainszr.Add(self.type_opt, 0, wx.ALL, 5)

        rn = 1
        for key, flen, opt, deflt, label in inf_keys:
            box = wx.StaticBoxSizer(
                wx.StaticBox(
                    self, gist.get_new_idval(),
                    _("{0} ({1} characters max.)").format(
                        label, flen)),
                wx.VERTICAL
                )

            sty = 0
            if flen > 64:
                sty = sty | wx.TE_MULTILINE

            txt = wx.TextCtrl(
                self, gist.get_new_idval(), "",
                wx.DefaultPosition, wx.DefaultSize,
                sty, wx.DefaultValidator, key)
            if not sty & wx.TE_MULTILINE:
                txt.SetMaxLength(flen)
            txt.SetValue(deflt)

            box.Add(txt, 1, wx.EXPAND|wx.ALL, 2)
            self.ctls.append(txt)
            self.add_child_wnd(txt)

            if flen > 64:
                self.mainszr.Add(box, 3, wx.EXPAND|wx.ALL, 3)
            else:
                self.mainszr.Add(box, 0, wx.EXPAND|wx.ALL, 3)

        self.dict_source = {}
        self.dict_user = {}

        self.SetSizer(self.mainszr)
        self.Layout()

        self.type_opt.Bind(
            wx.EVT_RADIOBOX, self.on_type_opt)

        self.type_opt.SetSelection(0)
        self.do_on_type_opt(0)


    def config_rd(self, config):
        if config.HasEntry(_T("volinf_type_opt")):
            opt = max(0, min(1, config.ReadInt(_T("volinf_type_opt"))))
            self.type_opt.SetSelection(opt)
            self.do_on_type_opt(opt)
        else:
            opt = self.type_opt.GetSelection()

        if opt != 1:
            self.do_on_type_opt(1)
        for c in self.ctls:
            nam = c.GetName()
            cnam = _T("volinf_") + nam
            if config.HasEntry(cnam):
                val = config.Read(cnam)
                c.SetValue(val)
        if opt != 1:
            self.do_on_type_opt(opt)

    def config_wr(self, config):
        opt = self.type_opt.GetSelection()
        config.WriteInt(_T("volinf_type_opt"), opt)

        if opt != 1:
            self.do_on_type_opt(1)
        for c in self.ctls:
            val = c.GetValue()
            nam = c.GetName()
            cnam = _T("volinf_") + nam
            config.Write(cnam, val)
        if opt != 1:
            self.do_on_type_opt(opt)

    def on_type_opt(self, event):
        self.do_on_type_opt(event.GetSelection())

    def do_on_type_opt(self, idx):
        dict_source = self.dict_source
        dict_user = self.dict_user

        if idx == 0:
            for c in self.ctls:
                l = c.GetName()
                dict_user[l] = c.GetValue()
                if l in dict_source:
                    c.SetValue(dict_source[l])
                else:
                    c.SetValue(_T(''))
                #c.Enable(False)
        elif idx == 1:
            for c in self.ctls:
                #c.Enable(True)
                l = c.GetName()
                if l in dict_user:
                    c.SetValue(dict_user[l])
                else:
                    c.SetValue(_T(''))

    def set_source_info(self, voldict, force = False):
        self.dict_source = {}
        dict_source = self.dict_source
        idx = self.type_opt.GetSelection()

        for key in voldict:
            c = self.FindWindowByName(key)
            if not c:
                continue

            val = voldict[key]
            dict_source[key] = val
            if idx == 0 or force:
                c.SetValue(val)

    def get_fields(self):
        r = {}
        for c in self.ctls:
            val = c.GetValue()
            if val:
                r[c.GetName()] = val

        return r


"""
ATargetPane -- Pane window for operation target setup
"""
class ATargetPane(ABasePane):
    def __init__(self, parent, gist, wi, hi, id = -1):
        ABasePane.__init__(self, parent, gist, wi, hi, id)
        self.panel = ATargetPanePanel(self, gist, self.sz)

        # tab focus hacks:
        self.focus_terminals["first"].Bind(
            wx.EVT_SET_FOCUS, self.set_focus_first)
        self.focus_terminals["first"].Bind(
            wx.EVT_KILL_FOCUS, self.kill_focus_first)
        self.focus_terminals["last"].Bind(
            wx.EVT_SET_FOCUS, self.set_focus_last)
        self.focus_terminals["last"].Bind(
            wx.EVT_KILL_FOCUS, self.kill_focus_last)


"""
ATargetPanePanel -- Pane window for operation target setup
"""
class ATargetPanePanel(wx.Panel):
    def __init__(self, parent, gist, size, id = -1):
        wx.Panel.__init__(self, parent, id, wx.DefaultPosition, size)
        self.parent = parent
        self.parent.attach_methods(self)

        self.core_ld = gist
        self.core_ld.set_target_wnd(self)

        # top level sizer
        self.bSizer1 = wx.FlexGridSizer(0, 1, 0, 0)
        self.bSizer1.AddGrowableCol(0)

        self.set_select = []

        type_optChoices = []
        type_optChoices.append(_("file/directory"))
        type_optChoices.append(_("burner"))
        type_optChoices.append(_("simultaneous"))

        self.type_opt = wx.RadioBox(
            self, gist.get_new_idval(), _("output type:"),
            wx.DefaultPosition, wx.DefaultSize, type_optChoices, 1,
            wx.RA_SPECIFY_ROWS)

        self.parent.focus_terminals["first"] = self.type_opt

        self.type_opt.SetItemToolTip(0,
            _(
            "The option 'file/directory' will write a filesystem image "
            "file (an .iso; if the 'simple' backup type is selected) "
            "or a directory hierarchy (if the 'advanced' "
            "backup type is selected) on your hard drive."
            "\n\n"
            "The backup data will not be burned to DVD disc."
            ))
        self.type_opt.SetItemToolTip(1,
            _(
            "The option 'burner' will write the backup to a DVD blank "
            "in the burner drive specified in 'output target' below, "
            "after reading the source DVD and writing temporary data "
            "on the hard drive."
            "\n\n"
            "When a burn operation succeeds, you will be asked whether "
            "you would like to burn another backup copy.  If you "
            "select 'yes' then the same temporary data is used so "
            "that the source disc does not need to be read again."
            "\n\n"
            "When burning is done, or on error, temporary data is "
            "deleted."
            ))
        self.type_opt.SetItemToolTip(2,
            _(
            "The option 'simultaneous' is useful if you have two "
            "DVD drives: one to read and one to write on. This option "
            "is only available when the 'simple' backup type "
            "is selected."
            "\n\n"
            "The backup is burned as it is read from the source disc, "
            "without a temporary copy. For several reasons, this "
            "might be the least reliable method. Data should be ready "
            "for the burner drive when it is needed, so the source "
            "disc must be readable at a rate that exceeds the burn "
            "speed."
            "\n\n"
            "Using this, you should make sure your computer is not "
            "very busy, and that the source disc is in good condition "
            "and unlikely to be difficult to read."
            "\n\n"
            "Noting the caution above, this option remains useful for "
            "a quick backup."
            ))

        self.add_child_wnd(self.type_opt)

        ttip = _(
            "If you select the \"file/directory\" option, then "
            "provide a path and name for the hard drive output."
            "\n\n"
            "If you select \"burner\" or \"simultaneous\" "
            "then select the device node associated with the DVD "
            "burner you wish to use."
            "\n\n"
            "You may enter the path directly in the text field, or "
            "click the button to use a file selection dialog."
            )

        self.box_whole = wx.StaticBoxSizer(
            wx.StaticBox(
                self, gist.get_new_idval(), _("output target:")),
            wx.VERTICAL
            )

        self.select_label = wx.StaticText(
            self, gist.get_new_idval(),
            _("specify a name for 'file/directory', or burner device:"),
            wx.DefaultPosition, wx.DefaultSize, 0)
        self.select_label.Wrap(-1)
        self.box_whole.Add(self.select_label, 0, wx.ALL, 5)

        self.fgSizer_node_whole = wx.FlexGridSizer(0, 1, 0, 0)
        self.fgSizer_node_whole.AddGrowableCol(0)
        self.fgSizer_node_whole.AddGrowableRow(0, 1)
        self.fgSizer_node_whole.AddGrowableRow(1, 2)
        self.fgSizer_node_whole.SetFlexibleDirection(wx.BOTH)
        self.fgSizer_node_whole.SetNonFlexibleGrowMode(
            wx.FLEX_GROWMODE_SPECIFIED)

        self.input_select_node = wx.TextCtrl(
            self, gist.get_new_idval(), "",
            wx.DefaultPosition, wx.DefaultSize,
            wx.TE_PROCESS_ENTER)
        self.input_select_node.SetToolTip(wx.ToolTip(ttip))
        self.fgSizer_node_whole.Add(
            self.input_select_node, 1,
            wx.ALL|wx.EXPAND, 2)
        self.add_child_wnd(self.input_select_node)
        self.set_select.append(self.input_select_node)

        nodbuttsz = wx.BoxSizer(wx.HORIZONTAL)

        self.parent.focus_terminals["last"] = self.input_select_node

        self.button_select_node = wx.Button(
            self, gist.get_new_idval(),
            _("Select Target"),
            wx.DefaultPosition, wx.DefaultSize, 0)
        self.button_select_node.SetToolTip(wx.ToolTip(ttip))
        nodbuttsz.Add(
            self.button_select_node, 1,
            wx.ALIGN_CENTER|wx.ALL, 1)
        self.add_child_wnd(self.button_select_node)
        self.set_select.append(self.button_select_node)

        self.fgSizer_node_whole.Add(
            nodbuttsz, 5, wx.EXPAND, 1)

        self.box_whole.Add(
            self.fgSizer_node_whole, 1, wx.EXPAND, 1)

        # begin vol info panel
        self.box_volinfo = wx.StaticBoxSizer(
            wx.StaticBox(self, gist.get_new_idval(),
                _("target volume info fields (optional):")),
            wx.VERTICAL
            )

        self.panel_volinfo = AVolInfPane(
            self, self.core_ld, size.width - 40, size.height - 40,
            id = gist.get_new_idval())
        self.add_child_wnd(self.panel_volinfo)

        self.box_volinfo.Add(
            self.panel_volinfo, 1, wx.EXPAND, 1)
        # end vol info panel

        self.box_check = wx.StaticBoxSizer(
            wx.StaticBox(self, gist.get_new_idval(),
                _("check first, then run:")),
            wx.VERTICAL
            )

        self.fgSizer1 = wx.FlexGridSizer(0, 2, 0, 0)
        self.fgSizer1.AddGrowableCol(0)
        self.fgSizer1.AddGrowableCol(1)
        self.fgSizer1.AddGrowableRow(0)
        self.fgSizer1.SetFlexibleDirection(wx.HORIZONTAL)
        self.fgSizer1.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_NONE)

        self.check_button = wx.Button(
            self, gist.get_new_idval(),
            _("Check"), wx.DefaultPosition, wx.DefaultSize, 0)
        self.check_button.SetToolTip(wx.ToolTip(
            _("Run check on source (and optionally target) disc.")))

        self.fgSizer1.Add(
            self.check_button, 0, wx.EXPAND|wx.ALL, 5)
        self.add_child_wnd(self.check_button)

        self.run_label = _("Run it")
        self.cancel_label = _("Cancel")
        self.cancel_mode = False
        self.run_button = wx.Button(
            self, gist.get_new_idval(),
            self.run_label, wx.DefaultPosition, wx.DefaultSize, 0)
        self.fgSizer1.Add(
            self.run_button, 0, wx.EXPAND|wx.ALL, 5)
        self.run_button.Enable(False)
        self.add_child_wnd(self.run_button)

        self.box_check.Add(
            self.fgSizer1, 1, wx.EXPAND, 5)


        # type opt in top level sizer
        self.bSizer1.Add(self.type_opt, 1, wx.ALL, 5)

        self.bSizer1.Add(
            self.box_whole, 1,
            wx.EXPAND|wx.ALL, 5)

        # volume info scrolled pane
        self.bSizer1.Add(
            self.box_volinfo, 1,
            wx.EXPAND|wx.ALL, 5)

        # check select in top level sizer
        self.bSizer1.Add(
            self.box_check, 1, wx.EXPAND|wx.ALL, 5)

        self.bSizer1.AddGrowableRow(2, 2)

        self.SetSizer(self.bSizer1)
        self.Layout()

        self.input_select_node.Bind(
            wx.EVT_TEXT_ENTER, self.on_select_node)
        self.type_opt.Bind(
            wx.EVT_RADIOBOX, self.on_type_opt)
        self.check_button.Bind(
            wx.EVT_BUTTON, self.on_check_button)
        self.run_button.Bind(
            wx.EVT_BUTTON, self.on_run_button)
        self.button_select_node.Bind(
            wx.EVT_BUTTON, self.on_button_select_node)



    def config_rd(self, config):
        if config.HasEntry(_T("target_type_opt")):
            opt = max(0, min(2, config.ReadInt(_T("target_type_opt"))))
            self.type_opt.SetSelection(opt)
            self.do_opt_id_change(opt)
        if config.HasEntry(_T("target_device")):
            self.input_select_node.SetValue(
                config.Read(_T("target_device")))
            self.on_select_node(None)
        self.panel_volinfo.config_rd(config)

    def config_wr(self, config):
        self.panel_volinfo.config_wr(config)
        config.WriteInt(
            _T("target_type_opt"), self.type_opt.GetSelection())
        config.Write(
            _T("target_device"), self.input_select_node.GetValue())

    def on_select_node(self, event):
        self.dev = self.input_select_node.GetValue()
        self.core_ld.target_select_node(self.dev)
        if not self.dev:
            return
        msg_line_INFO(_("set target to {0}").format(self.dev))

    def set_button_select_node_label(self):
        typ = self.type_opt.GetSelection()
        tit = _("Select burner device node")

        # to fs:
        if typ == 0:
            if self.core_ld.get_is_whole_backup():
                tit = _("Select file name")
            else:
                tit = _("Select directory name")

        self.button_select_node.SetLabel(tit)

    def on_button_select_node(self, event):
        typ = self.type_opt.GetSelection()
        tit = _("Select burner device node")
        tdr = _T("")
        sty = 0

        # to fs:
        if typ == 0:
            if self.core_ld.get_is_whole_backup():
                tit = _("Select file name for filesystem image")
            else:
                tit = _("Select directory name for hierarchy")
            # wx.FD_OVERWRITE_PROMPT removed: manager object prompts
            #sty = wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT
            sty = wx.FD_SAVE
        # to device
        else:
            tdr = _T("/dev")
            sty = wx.FD_OPEN|wx.FD_FILE_MUST_EXIST

        pw = wx.GetApp().GetTopWindow()
        file_dlg = wx.FileDialog(pw, tit, tdr, _T(""), _T("*"), sty)

        r = file_dlg.ShowModal()

        if r == wx.ID_OK:
            fil = file_dlg.GetPath()
            self.input_select_node.SetValue(fil)
            self.on_select_node(None)

    def do_opt_id_change(self, t_id):
        if t_id == 0:
            self.select_label.SetLabel(
                _("specify name for file/directory:"))
        elif t_id == 1:
            self.select_label.SetLabel(
                _("specify device node for burner:"))
        elif t_id == 2:
            self.select_label.SetLabel(
                _("specify device node for second burner:"))

    def on_type_opt(self, event):
        t_id = event.GetEventObject().GetSelection()
        self.do_opt_id_change(t_id)
        self.core_ld.target_opt_id_change(t_id)

    def on_check_button(self, event):
        self.core_ld.do_check(None)

    def on_run_button(self, event):
        self.dev = self.input_select_node.GetValue()
        rdev = raw_node_path(self.dev)
        if s_ne(self.dev, rdev):
            self.dev = rdev
            self.input_select_node.SetValue(rdev)
        self.core_ld.do_run(self.dev)

    def set_run_label(self):
        self.cancel_mode = False
        self.run_button.SetLabel(self.run_label)

    def set_cancel_label(self):
        self.cancel_mode = True
        self.run_button.SetLabel(self.cancel_label)

    def get_cancel_mode(self):
        return self.cancel_mode

    def get_target_text(self):
        return self.input_select_node.GetValue()

    def set_target_text(self, target_text, quiet = False):
        self.input_select_node.SetValue(target_text)
        self.dev = target_text
        if not quiet:
            msg_line_INFO(_("set target to {0}").format(self.dev))



"""
ASourcePane -- Pane window for operation source setup
"""
class ASourcePane(ABasePane):
    def __init__(self, parent, gist, wi, hi, id = -1):
        ABasePane.__init__(self, parent, gist, wi, hi, id)
        self.panel = ASourcePanePanel(
            self, gist, self.sz, gist.get_new_idval())

        # tab focus hacks:
        self.focus_terminals["first"].Bind(
            wx.EVT_SET_FOCUS, self.set_focus_first)
        self.focus_terminals["first"].Bind(
            wx.EVT_KILL_FOCUS, self.kill_focus_first)
        self.focus_terminals["last"].Bind(
            wx.EVT_SET_FOCUS, self.set_focus_last)
        self.focus_terminals["last"].Bind(
            wx.EVT_KILL_FOCUS, self.kill_focus_last)

"""
ASourcePanePanel -- Pane window for operation source setup
"""
class ASourcePanePanel(wx.Panel):
    def __init__(self, parent, gist, size, id = -1, def_type_opt = 0):
        wx.Panel.__init__(self, parent, id, wx.DefaultPosition, size)
        self.parent = parent
        self.parent.attach_methods(self)

        self.core_ld = gist
        self.core_ld.set_source_wnd(self)

        self.dev = None

        self.SetMinSize(size)
        self.SetMaxSize(size)

        self.set_whole = []
        self.set_hier = []

        # top level sizer
        self.bSizer1 = wx.FlexGridSizer(0, 1, 0, 0)
        self.bSizer1.AddGrowableCol(0)
        self.bSizer1.AddGrowableRow(2)
        self.bSizer1.SetMinSize(size)

        type_optChoices = []
        type_optChoices.append(_("simple"))
        type_optChoices.append(_("advanced"))

        self.type_opt = wx.RadioBox(
            self, gist.get_new_idval(), _("backup type:"),
            wx.DefaultPosition, wx.DefaultSize, type_optChoices, 1,
            wx.RA_SPECIFY_ROWS)

        self.parent.focus_terminals["first"] = self.type_opt

        self.type_opt.SetItemToolTip(0,
            _(
            "Simply make an exact backup copy of the DVD, "
            "without additional options."
            "\n\n"
            "With this backup type the source DVD does not need "
            "to be mounted."
            ))
        self.type_opt.SetItemToolTip(1,
            _(
            "Make a backup copy of the DVD allowing additional "
            "options. Two additional options exist:"
            "\n\n"
            "1) Files and directories may be added to the backup copy "
            "(using 'optional extras' below)."
            "\n"
            "2) Some information fields may set in the backup copy "
            "filesystem (using 'target volume info fields' "
            "on the right)."
            "\n\n"
            "When this option is selected, the source DVD must be "
            "mounted (see the mount(1) manual page). This is because "
            "its files must be available for regular access."
            ))

        self.add_child_wnd(self.type_opt)

        self.box_whole = wx.StaticBoxSizer(
            wx.StaticBox(
                self, gist.get_new_idval(), _("backup source:")
                ),
            wx.VERTICAL
            )

        ttip = _(
            "If you're using \"advanced\", the "
            "second backup type option, use the 'Select Mount' button "
            "to use a directory selector dialog to select the mount "
            "point. You may enter the mount point in the text field "
            "by hand (and then press enter/return)."
            "\n\n"
            "For the \"simple\" option use 'Select Node' to select "
            "the device node with a file selector dialog, or enter "
            "the device node path in the text field "
            "by hand (and then press enter/return)."
            )

        staticText3 = self.static_nodelabel = wx.StaticText(
            self, gist.get_new_idval(),
            _("select device node or mount point:"),
            wx.DefaultPosition, wx.DefaultSize, 0)
        self.static_nodelabel.SetToolTip(wx.ToolTip(ttip))
        staticText3.Wrap(-1)
        self.box_whole.Add(staticText3, 0, wx.ALL, 5)

        self.fgSizer_node_whole = wx.FlexGridSizer(0, 1, 0, 0)
        self.fgSizer_node_whole.AddGrowableCol(0)

        self.input_node_whole = wx.TextCtrl(
            self, gist.get_new_idval(), "",
            wx.DefaultPosition, wx.DefaultSize,
            wx.TE_PROCESS_ENTER)
        self.input_node_whole.SetToolTip(wx.ToolTip(ttip))
        self.fgSizer_node_whole.Add(
            self.input_node_whole, 1, wx.ALL|wx.EXPAND, 2)
        self.add_child_wnd(self.input_node_whole)

        nodbuttsz = wx.BoxSizer(wx.HORIZONTAL)

        self.parent.focus_terminals["last"] = self.input_node_whole

        self.button_node_whole = wx.Button(
            self, gist.get_new_idval(),
            _("Select Node"),
            wx.DefaultPosition, wx.DefaultSize, 0)
        self.button_node_whole.SetToolTip(wx.ToolTip(ttip))
        nodbuttsz.Add(
            self.button_node_whole, 1,
            wx.ALIGN_CENTER|wx.ALL, 1)
        self.add_child_wnd(self.button_node_whole)
        self.set_whole.append(self.button_node_whole)

        self.button_dir_whole = wx.Button(
            self, gist.get_new_idval(),
            _("Select Mount"),
            wx.DefaultPosition, wx.DefaultSize, 0)
        self.button_dir_whole.SetToolTip(wx.ToolTip(ttip))
        nodbuttsz.Add( self.button_dir_whole, 1,
            wx.ALIGN_CENTER|wx.ALL, 1)
        self.add_child_wnd(self.button_dir_whole)

        self.fgSizer_node_whole.Add(
            nodbuttsz, 5, wx.EXPAND, 1)

        self.box_whole.Add(
            self.fgSizer_node_whole, 1, wx.EXPAND, 1)

        self.box_hier = wx.StaticBoxSizer(
            wx.StaticBox(self, gist.get_new_idval(),
                _("optional extras:")),
            wx.VERTICAL
            )

        self.fgSizer_extra_hier = wx.FlexGridSizer(0, 1, 0, 0)
        self.fgSizer_extra_hier.AddGrowableCol(0)
        self.fgSizer_extra_hier.AddGrowableRow(0)
        self.fgSizer_extra_hier.SetFlexibleDirection(wx.BOTH)
        self.fgSizer_extra_hier.SetNonFlexibleGrowMode(
            wx.FLEX_GROWMODE_SPECIFIED)

        ln_sz = self.static_nodelabel.GetClientSize()
        flsz = wx.Size(wx.DefaultSize.width, ln_sz.height * 3) #12 * 5)
        self.addl_list_ctrl = AFileListCtrl(
            self, gist, id = gist.get_new_idval(), size = flsz)
        self.addl_list_ctrl.SetToolTip(
            wx.ToolTip(_(
                "If the \"advanced\" backup type is selected, "
                "additional files and directories may be included in "
                "the backup, subject to available space remaining "
                "after the source disc files, of course.\n"
                "\n"
                "For example, a serious fan of the source DVD might "
                "like to include reference materials like locally "
                "saved web pages, or scans of case covers, "
                "scans of autographs, etc..\n"
                "\n"
                "These materials will be available when the backup "
                "disc is mounted as an ISO-9660 filesystem.\n"
                "\n"
                "The buttons below the list control operate as "
                "implied by their labels. For removal of items, the "
                "list control allows item selection with the mouse "
                "(use the control or shift keys for multiple "
                "selections) or through a menu that appears if the "
                "control receives a right button click."
                )))
        self.add_child_wnd(self.addl_list_ctrl)

        self.fgSizer_extra_hier.Add(
            self.addl_list_ctrl, 50, wx.EXPAND, 5)
        self.set_hier.append(self.addl_list_ctrl)

        lstbuttsz = wx.BoxSizer(wx.HORIZONTAL)

        self.button_addl_files = wx.Button(
            self, gist.get_new_idval(),
            _("Add Files"),
            wx.DefaultPosition, wx.DefaultSize, 0)
        lstbuttsz.Add(
            self.button_addl_files, 1,
            wx.EXPAND, 2)
        self.set_hier.append(self.button_addl_files)
        self.add_child_wnd(self.button_addl_files)

        self.button_addl_dirs = wx.Button(
            self, gist.get_new_idval(),
            _("Add Directories"),
            wx.DefaultPosition, wx.DefaultSize, 0)
        lstbuttsz.Add(
            self.button_addl_dirs, 1,
            wx.EXPAND, 2)
        self.set_hier.append(self.button_addl_dirs)
        self.add_child_wnd(self.button_addl_dirs)

        self.fgSizer_extra_hier.Add(lstbuttsz, 1, wx.EXPAND, 5)

        lstbuttsz2 = wx.BoxSizer(wx.HORIZONTAL)

        self.button_addl_rmsel = wx.Button(
            self, gist.get_new_idval(),
            _("Remove Selected"),
            wx.DefaultPosition, wx.DefaultSize, 0)
        lstbuttsz2.Add(self.button_addl_rmsel, 1,  wx.EXPAND, 2)
        self.set_hier.append(self.button_addl_rmsel)
        self.add_child_wnd(self.button_addl_rmsel)

        self.button_addl_clear = wx.Button(
            self, gist.get_new_idval(),
            _("Clear List"),
            wx.DefaultPosition, wx.DefaultSize, 0)
        lstbuttsz2.Add(self.button_addl_clear, 1, wx.EXPAND, 2)
        self.set_hier.append(self.button_addl_clear)
        self.add_child_wnd(self.button_addl_clear)

        self.fgSizer_extra_hier.Add(lstbuttsz2, 1, wx.EXPAND, 5)

        self.box_hier.Add(self.fgSizer_extra_hier, 17, wx.EXPAND, 5)

        # type opt in top level sizer
        self.bSizer1.Add(self.type_opt, 0, wx.ALL, 5)

        # whole image dev select in top level sizer
        self.bSizer1.Add(self.box_whole, 20, wx.EXPAND|wx.ALL, 5)

        # hierarchy copy dev select in top level sizer
        self.bSizer1.Add(self.box_hier, 23, wx.EXPAND|wx.ALL, 5)

        self.SetSizer(self.bSizer1)
        self.Layout()

        # Connect Events
        self.type_opt.Bind(
            wx.EVT_RADIOBOX, self.on_type_opt)
        self.input_node_whole.Bind(
            wx.EVT_TEXT_ENTER, self.on_nodepick_whole)
        self.input_node_whole.Bind(
            wx.EVT_TEXT, self.on_nodepick_whole_evtext)
        self.button_node_whole.Bind(
            wx.EVT_BUTTON, self.on_nodepick_whole_button)
        self.button_dir_whole.Bind(
            wx.EVT_BUTTON, self.on_dirpick_whole_button)
        self.button_addl_files.Bind(
            wx.EVT_BUTTON, self.on_button_addl_files)
        self.button_addl_dirs.Bind(
            wx.EVT_BUTTON,  self.on_button_addl_dirs)
        self.button_addl_rmsel.Bind(
            wx.EVT_BUTTON,  self.on_button_addl_rmsel)
        self.button_addl_clear.Bind(
            wx.EVT_BUTTON,  self.on_button_addl_clear)

        # Files and dirs selectors
        # Bug note: with wx.FD_PREVIEW (which is nice for images)
        # the app will block and need to be KILLed if a fifo/pipe
        # appearing in the selector is merely clicked; click
        # /dev/stdout etc. and get a signal
        # TODO: add system knowledge for file dialog
        # default directory and file
        self.file_dlg = wx.FileDialog(
            self.parent, _("Select File"),
            _T("/dev"), _T("dvd"), _T("*"),
            wx.FD_OPEN|wx.FD_FILE_MUST_EXIST
            )

        # TODO: improve default dir search with system specific trends
        defdir = _T("/")
        chkdirs = (_T("/media"), )
        for chkdir in chkdirs:
            if os.path.isdir(chkdir):
                defdir = chkdir
                break

        self.dir_dlg = wx.DirDialog(
            self.parent, _("Select Mount Point"),
            defdir, wx.DD_DIR_MUST_EXIST
            )

        if _T("HOME") in os.environ:
            init_dir = os.environ[_T("HOME")]
        else:
            init_dir = _T("/")

        # Trouble with multi-dir-dialog on phoenix
        if phoenix:
            self.mddialog = None
            self.init_mdd_dir = init_dir
        else:
            self.mddialog = RepairedMDDialog(
                self.parent,
                tit = _("Select Additional Directories"),
                defpath = init_dir
            )



    # configuration
    def config_rd(self, config):
        if config.HasEntry(_T("source_type_opt")):
            opt = max(0, min(1, config.ReadInt(_T("source_type_opt"))))
            self.type_opt.SetSelection(opt)
            self.do_opt_id_change(opt)
        if config.HasEntry(_T("source_device")):
            self.input_node_whole.SetValue(
                config.Read(_T("source_device")))
            self.on_nodepick_whole(None)

    def config_wr(self, config):
        config.WriteInt(
            _T("source_type_opt"), self.type_opt.GetSelection())
        config.Write(
            _T("source_device"), self.input_node_whole.GetValue())

    def do_opt_id_change(self, t_id):
        if t_id == 0:
            set_off = self.set_hier
            set_on  = self.set_whole
            self.static_nodelabel.SetLabel(
                _("select DVD device node or mount point:"))
        else:
            set_on  = self.set_hier
            set_off = self.set_whole
            self.static_nodelabel.SetLabel(
                _("select DVD mount point directory:"))

        for c in set_off:
            c.Enable(False)
        for c in set_on:
            c.Enable(True)

        self.core_ld.source_opt_id_change(t_id)

    def on_type_opt(self, event):
        self.do_opt_id_change(event.GetEventObject().GetSelection())

    def on_nodepick_whole(self, event):
        self.dev = self.input_node_whole.GetValue()
        self.core_ld.source_select_node(self.dev)
        if not self.dev:
            return
        msg_line_INFO(_("set source device to {0}").format(self.dev))

    def on_nodepick_whole_evtext(self, event):
        self.dev = self.input_node_whole.GetValue()
        self.core_ld.source_select_node(self.dev)

    def on_nodepick_whole_button(self, event):
        r = self.file_dlg.ShowModal()
        if r == wx.ID_OK:
            fil = self.file_dlg.GetPath()
            self.input_node_whole.SetValue(fil)
            self.on_nodepick_whole(None)

    def on_dirpick_whole_button(self, event):
        r = self.dir_dlg.ShowModal()
        if r == wx.ID_OK:
            fil = self.dir_dlg.GetPath()
            self.input_node_whole.SetValue(fil)
            self.on_nodepick_whole(None)

    def on_button_addl_files(self, event):
        # Bug note: with wx.FD_PREVIEW (which is nice for images)
        # the app will block and need to be KILLed if a fifo/pipe
        # appearing in the selector is merely clicked; click
        # /dev/stdout etc. and get a signal
        dlg = wx.FileDialog(
            self.parent,
            _("Select Additional Files"),
            _T(""), _T(""), _T("*"),
            wx.FD_OPEN|wx.FD_MULTIPLE|wx.FD_FILE_MUST_EXIST
        )

        if dlg.ShowModal() != wx.ID_OK:
            return

        self.addl_list_ctrl.add_multi_files(dlg.GetPaths())


    def on_button_addl_dirs(self, event):
        dlg = self.mddialog
        destroy = False

        try:
            # In 'classic' wxPy, self.mddialog will be assigned in
            # __init__(), but in 'phoenix' this raises an error
            # suggesting it is designed to created be on each use, so:
            if dlg == None:
                dlg = RepairedMDDialog(
                    self.parent,
                    tit = _("Select Additional Directories"),
                    defpath = self.init_mdd_dir
                )
                destroy = True

            resp = dlg.ShowModal()

            if resp != wx.ID_OK:
                return

            try:
                pts = dlg.GetRepairedPaths()
            except RepairedMDDialog.Unfixable as msg:
                msg_line_WARN(msg)
                raise Exception(msg)

            self.addl_list_ctrl.add_multi_files(pts)


        except RepairedMDDialog.Unfixable as m:
            raise Exception(m)

        except Exception as m:
            msg_line_ERROR(_("MDDialog exception: '{0}'").format(m))

            destroy = True
            dlg = wx.DirDialog(
                self.parent,
                _("Select Additional Directories"),
                self.init_mdd_dir,
                wx.DD_DIR_MUST_EXIST
            )

            resp = dlg.ShowModal()

            self.addl_list_ctrl.add_multi_files([dlg.GetPath()])
        finally:
            if destroy:
                self.mddialog = None
                if dlg:
                    dlg.Destroy()


    def on_button_addl_rmsel(self, event):
        self.addl_list_ctrl.rm_selected()

    def on_button_addl_clear(self, event):
        self.addl_list_ctrl.rm_all()

    def get_all_addl_items(self):
        return self.addl_list_ctrl.get_all_items()

    def set_source_text(self, text, quiet = False):
        self.input_node_whole.SetValue(text)
        self.dev = text
        if not quiet:
            msg_line_INFO(_("set source to {0}").format(self.dev))


"""
AProgBarPanel -- small class for wxGauge progress bar
"""
class AProgBarPanel(wx.Panel):
    def __init__(self, parent, gist, ID = -1, rang = 1000,
                 style = wx.GA_HORIZONTAL | wx.GA_SMOOTH):
        wx.Panel.__init__(self, parent, ID)

        self.gist = gist
        self.gauge = wx.Gauge(
            self, gist.get_new_idval(), rang,
            style = style)

        if style & wx.GA_HORIZONTAL and not style & wx.GA_VERTICAL:
            szr = wx.HORIZONTAL
        else:
            szr = wx.VERTICAL

        szr = wx.BoxSizer(szr)
        szr.Add(self.gauge, 1, wx.EXPAND | wx.ALL, 2)
        self.SetSizer(szr)
        self.Layout()

    def get_gauge(self):
        return self.gauge

    def IsVertical(self):
        return self.get_gauge().IsVertical()

    def GetValue(self):
        return self.get_gauge().GetValue()

    def SetValue(self, value):
        self.get_gauge().SetValue(value)

    def GetRange(self):
        return self.get_gauge().GetRange()

    def SetRange(self, value):
        self.get_gauge().SetRange(value)

    def Pulse(self):
        self.get_gauge().Pulse()


"""
AChildSashWnd -- adjustable child of adjustable child of top frame

                 see ASashWnd class below
"""
class AChildSashWnd(wxadv.SashWindow):
    def __init__(self, parent, sz, logobj, ID, title, gist):
        wxadv.SashWindow.__init__(self, parent, ID)

        self.core_ld = gist

        self.pane_minw = 40
        szw1 = parent.GetSize()
        pane_width = sz.width / 2

        self.swnd = []
        self.swnd.append(
            wxadv.SashLayoutWindow(
                self, gist.get_new_idval(),
                wx.DefaultPosition, (240, 30),
                wx.NO_BORDER|wxadv.SW_3D
            ))
        self.swnd[0].SetDefaultSize((pane_width, 1000))
        self.swnd[0].SetOrientation(wxadv.LAYOUT_VERTICAL)
        self.swnd[0].SetAlignment(wxadv.LAYOUT_LEFT)
        self.swnd[0].SetBackgroundColour(wx.Colour(240, 240, 240))
        self.swnd[0].SetSashVisible(wxadv.SASH_RIGHT, True)
        self.swnd[0].SetExtraBorderSize(1)

        self.swnd.append(
            wxadv.SashLayoutWindow(
                self, gist.get_new_idval(),
                wx.DefaultPosition, (240, 30),
                wx.NO_BORDER|wxadv.SW_3D
            ))
        self.swnd[1].SetDefaultSize((pane_width, 1000))
        self.swnd[1].SetOrientation(wxadv.LAYOUT_VERTICAL)
        self.swnd[1].SetAlignment(wxadv.LAYOUT_LEFT)
        self.swnd[1].SetBackgroundColour(wx.Colour(240, 240, 240))
        self.swnd[1].SetSashVisible(wxadv.SASH_RIGHT, True)
        self.swnd[1].SetExtraBorderSize(1)

        w_adj = 20
        h_adj = 40
        self.child1_maxw = pane_width
        self.child1_maxh = sz.height

        self.child2_maxw = pane_width
        self.child2_maxh = sz.height

        self.child1 = ASourcePane(
            self.swnd[0], gist,
            self.child1_maxw - w_adj, self.child1_maxh - h_adj,
            id = gist.get_new_idval()
            )
        self.child2 = ATargetPane(
            self.swnd[1], gist,
            self.child2_maxw - w_adj, self.child2_maxh - h_adj,
            id = gist.get_new_idval()
            )

        self.child1.set_focus_partner_fore(self.child2)
        self.child1.set_focus_partner_back(self.child2)

        self.child2.set_focus_partner_fore(self.child1)
        self.child2.set_focus_partner_back(self.child1)

        self.child1.take_focus()

        self.remainingSpace = self.swnd[1]

        self.child1_maxw += w_adj
        self.child2_maxw += w_adj

        ids = []
        ids.append(self.swnd[0].GetId())
        ids.append(self.swnd[1].GetId())
        ids.sort()

        self.Bind(
            wxadv.EVT_SASH_DRAGGED_RANGE, self.on_sash_drag,
            id = ids[0], id2 = ids[1]
            )

        self.Bind(wx.EVT_SIZE, self.OnSize)


    # Call once only, after ctor completes, so that parent may
    # treat children, knowing they are created.
    def post_contruct(self):
        self.SetThemeEnabled(True)
        self.child1.init_for_children()
        self.child1.init_for_children()

    def on_sash_drag(self, event):
        event.Skip()

        if event.GetDragStatus() == wxadv.SASH_STATUS_OUT_OF_RANGE:
            msg_line_WARN(_('sash drag is out of range'))
            return

        eobj = event.GetEventObject()

        if eobj is self.swnd[0]:
            wi = min(event.GetDragRect().width, self.child1_maxw)
            self.swnd[0].SetDefaultSize((wi, self.child1_maxh))

        elif eobj is self.swnd[1]:
            wi = min(event.GetDragRect().width, self.child2_maxw)
            self.swnd[1].SetDefaultSize((wi, self.child2_maxh))

        wxadv.LayoutAlgorithm().LayoutWindow(self, self.remainingSpace)
        self.remainingSpace.Refresh()

    def OnSize(self, event):
        event.Skip()

        sz  = self.swnd[0].GetSize()
        sz1 = self.swnd[1].GetSize()

        wxadv.LayoutAlgorithm().LayoutWindow(self, self.remainingSpace)

        if sz1.width < self.pane_minw:
            w0 = sz.width - (self.pane_minw - sz1.width)
            if w0 >= self.pane_minw:
                self.swnd[0].SetDefaultSize((w0, sz.height))
            else:
                self.swnd[0].SetDefaultSize((self.pane_minw, sz.height))
            wxadv.LayoutAlgorithm().LayoutWindow(
                self, self.remainingSpace)

        elif sz.width < self.pane_minw:
            self.swnd[0].SetDefaultSize((self.pane_minw, sz.height))
            wxadv.LayoutAlgorithm().LayoutWindow(
                self, self.remainingSpace)

        elif sz1.width > self.child2_maxw:
            w0 = min(sz.width + (sz1.width - self.child2_maxw),
                self.child1_maxw)
            if sz.width < w0:
                self.swnd[0].SetDefaultSize((w0, sz.height))
                wxadv.LayoutAlgorithm().LayoutWindow(
                    self, self.remainingSpace)


    def get_msg_obj(self):
        return self.swnd[1].get_msg_obj()


"""
ASashWnd -- adjustable child of top frame
"""
class ASashWnd(wxadv.SashWindow):
    def __init__(self, parent, ID, title, gist,
                       init_build = True, size = (800, 600)):
        wxadv.SashWindow.__init__(self,
                               parent, ID, name = title, size = size)

        self.core_ld = gist

        # Param init_build means do build/create now, or
        # let parent code call method to build
        self.init_build_done = False
        if init_build:
            self._init_build()

    def _init_build(self):
        if self.init_build_done:
            return

        self.init_build_done = True

        parent = self.GetParent()
        gist = self.core_ld

        self.msg_minh = 72
        self.msg_inith = 100
        sz = self.GetClientSize()
        #sz.height -= 32 #
        #sz.height -= self.msg_inith
        #sz.height -= self.msg_minh
        top_ht = sz.height - self.msg_inith

        self.swnd = []
        self.swnd.append(
            wxadv.SashLayoutWindow(
                self, gist.get_new_idval(),
                wx.DefaultPosition,
                (300, top_ht),
                wx.NO_BORDER|wxadv.SW_3D
            ))
        self.swnd[0].SetDefaultSize((sz.width, top_ht))
        self.swnd[0].SetOrientation(wxadv.LAYOUT_HORIZONTAL)
        self.swnd[0].SetAlignment(wxadv.LAYOUT_TOP)
        self.swnd[0].SetBackgroundColour(wx.Colour(240, 240, 240))
        self.swnd[0].SetSashVisible(wxadv.SASH_BOTTOM, True)
        self.swnd[0].SetExtraBorderSize(1)

        self.swnd.append(
            wxadv.SashLayoutWindow(
                self, gist.get_new_idval(),
                wx.DefaultPosition,
                (300, self.msg_minh),
                wx.NO_BORDER|wxadv.SW_3D
            ))
        self.swnd[1].SetDefaultSize((sz.width, self.msg_minh))
        self.swnd[1].SetOrientation(wxadv.LAYOUT_HORIZONTAL)
        self.swnd[1].SetAlignment(wxadv.LAYOUT_BOTTOM)
        self.swnd[1].SetBackgroundColour(wx.Colour(240, 240, 240))
        self.swnd[1].SetSashVisible(wxadv.SASH_BOTTOM, True)
        self.swnd[1].SetExtraBorderSize(1)

        self.child1_maxw = 16000
        self.child1_maxh = 16000

        self.child2_maxw = 16000
        self.child2_maxh = 16000

        # It's not clear why, but top section height
        # must be further reduced on some GUI systems,
        # e.g., Xubuntu
        fudge_ht = 28
        sz1 = wx.Size(sz.width, top_ht - fudge_ht)
        self.child1 = AChildSashWnd(
            self.swnd[0], sz1, parent, gist.get_new_idval(),
            _T("Source and Destination"), gist
            )
        self.child2 = AMsgWnd(
            self.swnd[1], 100, self.msg_minh, id = gist.get_new_idval())
        self.core_ld.set_msg_wnd(self.child2)
        self.child2.set_scroll_to_end(True)

        self.remainingSpace = self.swnd[1]

        ids = []
        ids.append(self.swnd[0].GetId())
        ids.append(self.swnd[1].GetId())
        ids.sort()

        self.Bind(
            wxadv.EVT_SASH_DRAGGED_RANGE, self.on_sash_drag,
            id=ids[0], id2=ids[-1]
            )

        self.Bind(wx.EVT_SIZE, self.OnSize)


    # Call once only, after ctor completes, so that parent may
    # treat children, knowing they are created.
    def post_contruct(self):
        self.SetThemeEnabled(True)
        self.child1.post_contruct()

    def on_sash_drag(self, event):
        if event.GetDragStatus() == wxadv.SASH_STATUS_OUT_OF_RANGE:
            msg_line_WARN(_('sash drag is out of range'))
            return

        eobj = event.GetEventObject()

        if eobj is self.swnd[0]:
            hi = min(self.child1_maxh, event.GetDragRect().height)
            self.swnd[0].SetDefaultSize((self.child1_maxw, hi))

        elif eobj is self.swnd[1]:
            hi = min(self.child2_maxh, event.GetDragRect().height)
            self.swnd[1].SetDefaultSize((self.child2_maxw, hi))

        wxadv.LayoutAlgorithm().LayoutWindow(self, self.remainingSpace)
        self.remainingSpace.Refresh()
        self.child2.conditional_scroll_adjust()

    def OnSize(self, event):
        ssz = self.GetClientSize()
        sz0 = self.swnd[0].GetSize()
        sz1 = self.swnd[1].GetSize()
        h0 = sz0.height
        h1 = sz1.height

        ssz.height -= sz1.height

        if sz0.height > ssz.height:
            if ssz.height >= self.msg_minh:
                h0 = ssz.height
            else:
                h0 = self.msg_inith

        h1 = ssz.height - h0

        self.swnd[0].SetDefaultSize((sz0.width, h0))
        self.swnd[1].SetDefaultSize((sz0.width, h1))

        wxadv.LayoutAlgorithm().LayoutWindow(self, self.remainingSpace)

        self.child2.conditional_scroll_adjust()

    def get_msg_obj(self):
        return self.child2


# A sequential integer ID dispenser for wx objects like
# menu/toolbar items, buttons
# prefix WX in capitols to distinguish from actual wx objects/code
class WXObjIdSource:
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


# A dialog box for settings
# using a tabbed interface for sections
class ASettingsDialog(wx.Dialog):
    def __init__(self,
            parent, ID, gist,
            title = _("{appname} Settings").format(appname = PROG),
            pos = wx.DefaultPosition, size = (600, 450)):
        wx.Dialog.__init__(self, parent, ID, title, pos, size)

        self.core_ld = gist

        szr = wx.BoxSizer(wx.VERTICAL)
        bdr = 16

        # presently, use std wxNotebook since it is more agreeable
        # with gtk themes; but, leave AuiNotebook code in place for
        # use if, e.g., many more tabs are necessary
        if False:
            self.nb = wx.aui.AuiNotebook(
                self,
                id = gist.get_new_idval(),
                style = wx.aui.AUI_NB_TOP|
                        wx.aui.AUI_NB_TAB_SPLIT|
                        wx.aui.AUI_NB_TAB_MOVE|
                        wx.aui.AUI_NB_SCROLL_BUTTONS)
        else:
            self.nb = wx.Notebook(
                self,
                id = gist.get_new_idval(),
                style = wx.NB_TOP)

        szr.Add(self.nb,
                proportion = 1,
                flag = wx.EXPAND | wx.LEFT|wx.RIGHT|wx.TOP,
                border = bdr)

        bsz = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)

        szr.Add(bsz,
                proportion = 0,
                flag = wx.EXPAND | wx.ALL,
                border = bdr)

        self._setup_data_structs()

        self._mk_rundata_pane()
        self._mk_paths_pane()
        self._mk_advanced_pane()

        self.SetSizer(szr)
        self.SetMinSize(size)
        self.Fit()

        self.Bind(wx.EVT_SYS_COLOUR_CHANGED, self.on_sys_color)


    #private
    def on_sys_color(self, event):
        event.Skip()

        f = lambda wnd: self._color_proc_per_child(wnd)
        invoke_proc_for_window_children(self, f)

    def _color_proc_per_child(self, wnd):
        fclr = _msg_obj.GetForegroundColour()
        bclr = _msg_obj.GetBackgroundColour()

        wnd.SetForegroundColour(fclr)
        wnd.SetBackgroundColour(bclr)

        wnd.SetThemeEnabled(True)
        wnd.Refresh(True)
        wnd.Update()

    def _mk_rundata_pane(self):
        dat = self._data_rundata
        pane = wx.Panel(self.nb, self.core_ld.get_new_idval(),
                        style = wx.TAB_TRAVERSAL
                        | wx.CLIP_CHILDREN
                        | wx.FULL_REPAINT_ON_RESIZE
                        )

        self._mk_pane_items(pane, dat)

        pane.SetToolTip(wx.ToolTip(_(
                "The items under this tab are for "
                "general settings or data used in normal operations."
                )
            ))

        pane.Fit()
        pane.SetMinSize(self.nb.GetSize())

        self.nb.AddPage(pane, _("General Settings"))

    def _mk_paths_pane(self):
        dat = self._data_paths
        pane = wx.Panel(self.nb, self.core_ld.get_new_idval(),
                        style = wx.TAB_TRAVERSAL
                        | wx.CLIP_CHILDREN
                        | wx.FULL_REPAINT_ON_RESIZE
                        )

        self._mk_pane_items(pane, dat)

        pane.SetToolTip(wx.ToolTip(_(
                "The items under this tab are for "
                "the child programs that are the tools "
                "used for the job. These must all be usable. "
                "If any of the tools need a special path, or are "
                "installed with a different name, then "
                "specify the name and/or path in these fields."
                )
            ))

        pane.Fit()
        pane.SetMinSize(self.nb.GetSize())

        self.nb.AddPage(pane, _("Tool Names/Paths"))

    def _mk_advanced_pane(self):
        dat = self._data_advanced
        pane = wx.Panel(self.nb, self.core_ld.get_new_idval(),
                        style = wx.TAB_TRAVERSAL
                        | wx.CLIP_CHILDREN
                        | wx.FULL_REPAINT_ON_RESIZE
                        )

        self._mk_pane_items(pane, dat)

        pane.SetToolTip(wx.ToolTip(_(
                "The items under this tab are advanced "
                "options for cprec and dd-dvd.\n"
                "\n"
                "dd-dvd is the program used when backup type "
                "\"simple\" is selected, and cprec is used when "
                "the \"advanced\" type is selected.\n"
                "\n"
                "To understand these options, see the cprec(1) "
                "and dd-dvd(1) manual pages."
                )
            ))

        pane.Fit()
        pane.SetMinSize(self.nb.GetSize())

        self.nb.AddPage(pane, _("Advanced Options"))

    def _mk_pane_items(self, pane, dat, border = 10):
        bdr = border
        dlen = len(dat)

        add_bdr_space = True

        szr = wx.FlexGridSizer(0, 4, bdr, bdr)
        szr.AddGrowableCol(2, 10)

        if add_bdr_space:
            for c in range(0, 4):
                szr.AddSpacer(bdr)

        for idx in xrange(dlen):
            a = dat[idx]
            typ = a.typ
            i0 = self.core_ld.get_new_idval()
            i1 = self.core_ld.get_new_idval()

            # convenience, save space w/ flags
            #blr = wx.LEFT | wx.RIGHT
            blr = wx.RIGHT

            if add_bdr_space:
                szr.AddSpacer(bdr)

            if s_eq(typ, "text"):
                s = wx.StaticText(pane, i0, a.lbl)
                szr.Add(s, proportion = a.prp,
                    flag = wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL,
                    border = bdr)
                t = wx.TextCtrl(pane, i1, a.dft, name = a.nam)
                szr.Add(t, proportion = a.prp,
                    flag = wx.EXPAND | blr,
                    border = bdr)
                if a.tip:
                    t.SetToolTip(wx.ToolTip(a.tip))
            elif s_eq(typ, "blank"):
                szr.AddSpacer(bdr)
                szr.AddStretchSpacer(a.prp)
            elif s_eq(typ, "hline"):
                s = wx.StaticLine(pane, i0, style = wx.LI_HORIZONTAL)
                szr.Add(s, proportion = a.prp,
                    flag = wx.EXPAND,
                    border = bdr)
                t = wx.StaticLine(pane, i1, style = wx.LI_HORIZONTAL)
                szr.Add(t, proportion = a.prp,
                    flag = wx.EXPAND,
                    border = bdr)
            elif s_eq(typ, "txthline"):
                s = wx.StaticText(pane, i0, a.lbl,
                    style = wx.ALIGN_CENTRE)
                szr.Add(s, proportion = a.prp,
                    flag = wx.ALIGN_CENTRE,
                    border = bdr)
                t = wx.StaticLine(pane, i1, style = wx.LI_HORIZONTAL)
                szr.Add(t, proportion = a.prp,
                    flag = wx.EXPAND,
                    border = bdr)
            elif s_eq(typ, "spin_int"):
                df = a.dft
                mn, mx = a.xtr
                s = wx.StaticText(pane, i0, a.lbl)
                szr.Add(s, proportion = a.prp,
                    flag = wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL,
                    border = bdr)
                t = wx.SpinCtrl(pane, i1, str(df), name = a.nam,
                    initial = df, min = mn, max = mx)
                szr.Add(t, proportion = a.prp,
                    flag = wx.ALIGN_CENTER,
                    border = bdr)
                if a.tip:
                    t.SetToolTip(wx.ToolTip(a.tip))
            elif s_eq(typ, "cprec_option"):
                s = wx.StaticText(pane, i0, a.lbl)
                szr.Add(s, proportion = a.prp,
                    flag = wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL,
                    border = bdr)
                t = wx.CheckBox(pane, i1, name = a.nam,
                    label = _("option: {0}").format(_T("--") + a.nam))
                t.SetValue(a.dft)
                szr.Add(t, proportion = a.prp,
                    flag = wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL,
                    border = bdr)
                if a.tip:
                    t.SetToolTip(wx.ToolTip(a.tip))
            elif s_eq(typ, "app_option"):
                s = wx.StaticText(pane, i0, a.lbl)
                szr.Add(s, proportion = a.prp,
                    flag = wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL,
                    border = bdr)
                if "opt_lbl" in a.xtr:
                    t = wx.CheckBox(pane, i1, name = a.nam,
                        label = a.xtr["opt_lbl"])
                else:
                    t = wx.CheckBox(pane, i1, name = a.nam)
                t.SetValue(a.dft)
                szr.Add(t, proportion = a.prp,
                    flag = wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL,
                    border = bdr)
                if a.tip:
                    t.SetToolTip(wx.ToolTip(a.tip))

            if add_bdr_space:
                szr.AddSpacer(bdr)

        # add item loop done; add last border space if wanted
        if add_bdr_space:
            for c in range(0, 4):
                szr.AddSpacer(bdr)

        # set the sizer on the pane
        pane.SetSizer(szr)
        pane.Layout()


    @staticmethod
    def _mk_data_struct(
                        typ = _T("hline"), # type of control
                        lbl = _T(""),      # control label
                        nam = _T(""),      # control/config name
                        prp = 0,           # control sizer proportion
                        val = _T(""),      # value, set by user
                        dft = _T(""),      # value, default
                        tip = _T(""),      # control 'tooltip'
                        xtr = None         # any extra data
                        ):
        """Using anonymous class, as simple C struct
        """
        class __settings_dialog_private_data_struct:
            pass

        r = __settings_dialog_private_data_struct()

        r.typ = typ
        r.lbl = lbl
        r.nam = nam
        r.prp = prp
        r.val = val
        r.dft = dft
        r.tip = tip
        r.xtr = xtr

        return r

    def _setup_data_structs(self):
        # proc returns structured data from call parameters
        f = self.__class__._mk_data_struct

        # advanced tab
        self._data_advanced = [
            f(_T("txthline"), _("cprec options:"), prp = 5),
            f(_T("cprec_option"), _("Do not fail if file exists:"),
              _T("ignore-existing"), 0, dft = False),
            f(_T("cprec_option"),
              _("Do not copy symbolic links, make new file:"),
              _T("ignore-symlinks"), 0, dft = False),
            f(_T("cprec_option"),
              _("Do not make hard links, make new file:"),
              _T("ignore-hardlinks"), 0, dft = False),
            f(_T("cprec_option"),
              _("Do not make device nodes, pipes, etc.:"),
              _T("ignore-specials"), 0, dft = True),
            f(_T("txthline"), _("cprec and dd-dvd options:"), prp = 5),
            f(_T("spin_int"),
              _("{0} 2048 byte blocks:").format(
                    _T("--block-read-count")),
              _T("block-read-count"), 0,
              dft = 4096, xtr = (1, 4096 * 8)),
            f(_T("spin_int"),
              _("{0} for read errors:").format(
                    _T("--retry-block-count")),
              _T("retry-block-count"), 0,
              dft = 48, xtr = (1, 4096 * 8)),
            f(_T("hline"), prp = 5),
            f(_T("text"),
              _("libdvdread library name or path:"),
              _T("libdvdr"),
              prp = 0),
            f(_T("blank"), prp = 5)
            ]

        # tool paths tab
        self._data_paths = [
            f(_T("blank"), prp = 5),
            f(_T("text"),
              _("growisofs program:"),
              _T("growisofs"),
              prp = 0, dft = _T("growisofs")),
            f(_T("text"),
              _("dvd+rw-mediainfo program:"),
              _T("dvd+rw-mediainfo"),
              prp = 0, dft = _T("dvd+rw-mediainfo")),
            f(_T("text"),
              _("dvd+rw-format program:"),
              _T("dvd+rw-format"),
              prp = 0, dft = _T("dvd+rw-format")),
            f(_T("text"),
              _("mkisofs/genisoimage program:"),
              _T("mkisofs"),
              prp = 0, dft = _T("mkisofs")),
            f(_T("txthline"), _("Included Programs:"), prp = 5),
            f(_T("text"),
              _("cprec program:"),
              _T("cprec"),
              prp = 0, dft = _T("cprec")),
            f(_T("text"),
              _("dd-dvd program:"),
              _T("dd-dvd"),
              prp = 0, dft = _T("dd-dvd")),
            f(_T("blank"), prp = 5)
            ]

        # general runtime data
        self._data_rundata = [
            f(_T("blank"), prp = 5),
            f(_T("text"),
              _("Temp directories (9GB):"),
              _T("temp_dirs"),
              prp = 0, tip = _(
                "The usual directories used to hold temporary data "
                "might not have enough available free space for "
                "DVD size data, or you may have any reason to "
                "wish to specify a temporary directory."
                "\n\n"
                "This is optional, unless the usual directories have "
                "too little space."
                "\n\n"
                "You may enter more than one directory: multiple "
                "directories must be separated by a colon (':') "
                "character."
                )),
            f(_T("app_option"),
              _("Expand variable in temps:"),
              _T("expand_env"), 0, dft = True,
              tip = _(
                "This option affects whether a given "
                "temporary directory will be checked for '$' "
                "as the first character, and have that initial "
                "part replaced from an environment variable of that "
                "name."
                "\n\n"
                "Only the first path component is checked; "
                "any '$' in other components are ignored."
                ),
              xtr = {"opt_lbl":_("e.g., $HOME/tmp")}),
            f(_T("app_option"),
              _("Check environment for temps:"),
              _T("use_env_tempdir"), 0, dft = True,
              tip = _(
                "This option affects whether the usual "
                "environment variables pertaining to temporary "
                "directories are checked."
                ),
              xtr = {"opt_lbl":_T("TMPDIR, TMP, TEMP")}),
            f(_T("app_option"),
              _("Use converntionals for temps:"),
              _T("use_def_tempdir"), 0, dft = True,
              tip = _(
                "This option affects whether a small set of "
                "conventional temporary directory paths will "
                "checked for existance and sufficient free space."
                ),
              xtr = {"opt_lbl":_T("/tmp, /var/tmp, /usr/tmp, $HOME")}),
            f(_T("app_option"),
              _("Use Python path for temps:"),
              _T("use_mod_tempfile_tempdir"), 0, dft = True,
              tip = _(
                "This option affects whether the Python tempfile "
                "module will be queried for its temporary directory "
                "path (Python is the language this is written in)."
                ),
              xtr = {"opt_lbl":_T("tempfile.gettempdir()")}),
            f(_T("hline"), prp = 5),
            f(_T("spin_int"),
              _("Disc insert settle time"),
              _T("disc_settle_time"), 0,
              dft = 5,
              xtr = (1, 120), tip = _(
                "When a backup reaches the burn stage, a dialog box "
                "is shown prompting you to make sure a blank disc is "
                "ready in the target drive. "
                "If you click 'OK' too soon after placing a blank "
                "in the drive, the disc might not be detected "
                "because DVD drives can take several seconds to "
                "examine new media. Therefore, this program will "
                "pause for a few seconds after the dialog is dismissed."
                "\n\n"
                "You may change the number seconds the drive is "
                "given to settle. The default "
                "is 5 seconds, and a range from 1 to 120 is accepted."
                )),
            f(_T("spin_int"),
              _("Disc insert settle retries"),
              _T("disc_settle_retries"), 0,
              dft = 5,
              xtr = (0, 32), tip = _(
                "The 'Disc insert settle time' above might be "
                "insufficient. Rather than give up immediately, the "
                "program may try again a number of times (the pause "
                "is repeated each time). "
                "\n\n"
                "The default "
                "is 5, and a range from 0 to 32 is accepted."
                )),
            f(_T("blank"), prp = 5)
            ]

    def config_rd(self, config):
        dp = self._get_data_paths()
        cf_path = config.GetPath()
        cf_exp  = config.IsExpandingEnvVars()
        config.SetExpandEnvVars(False)

        for pth, dat in dp:
            config.SetPath(_T("/main/settings/") + pth)

            dlen = len(dat)
            for idx in xrange(dlen):
                a = dat[idx]
                typ = a.typ

                if not (s_eq(typ, "text") or
                        s_eq(typ, "spin_int") or
                        s_eq(typ, "app_option") or
                        s_eq(typ, "cprec_option")):
                    continue

                ctl = self.FindWindowByName(a.nam)
                if not ctl: # error; shouldn't happen
                    continue

                cfkey = a.nam
                df = a.dft

                if s_eq(typ, "text"):
                    if config.HasEntry(cfkey):
                        v = config.Read(cfkey)
                        ctl.SetValue(v)
                    else:
                        ctl.SetValue(df)
                elif s_eq(typ, "spin_int"):
                    if config.HasEntry(cfkey):
                        v = config.ReadInt(cfkey)
                        ctl.SetValue(v)
                    else:
                        ctl.SetValue(df)
                elif (s_eq(typ, "cprec_option") or
                      s_eq(typ, "app_option")):
                    if config.HasEntry(cfkey):
                        v = config.ReadInt(cfkey)
                        ctl.SetValue(bool(v))
                    else:
                        ctl.SetValue(df)


        config.SetExpandEnvVars(cf_exp)
        config.SetPath(cf_path)

    def config_wr(self, config):
        dp = self._get_data_paths()
        cf_path = config.GetPath()

        for pth, dat in dp:
            config.SetPath(_T("/main/settings/") + pth)

            dlen = len(dat)
            for idx in xrange(dlen):
                a = dat[idx]
                typ = a.typ

                if not (s_eq(typ, "text") or
                        s_eq(typ, "spin_int") or
                        s_eq(typ, "app_option") or
                        s_eq(typ, "cprec_option")):
                    continue

                ctl = self.FindWindowByName(a.nam)
                if not ctl: # error; shouldn't happen
                    continue

                cfkey = a.nam
                df = a.dft

                if s_eq(typ, "text"):
                    v = ctl.GetValue().strip()
                    if len(v) and s_ne(v, df):
                        config.Write(cfkey, v)
                    elif config.HasEntry(cfkey):
                        config.DeleteEntry(cfkey)
                elif s_eq(typ, "spin_int"):
                    v = int(ctl.GetValue())
                    if v != df:
                        config.WriteInt(cfkey, v)
                    elif config.HasEntry(cfkey):
                        config.DeleteEntry(cfkey)
                elif (s_eq(typ, "cprec_option") or
                      s_eq(typ, "app_option")):
                    v = ctl.GetValue()
                    if bool(v) != df:
                        config.WriteInt(cfkey, int(v))
                    elif df:
                        config.WriteInt(cfkey, int(df))
                    elif config.HasEntry(cfkey):
                        config.DeleteEntry(cfkey)

        config.SetPath(cf_path)


    def _get_data_paths(self):
        return (
            (_T("rundata"), self._data_rundata),
            (_T("tools"), self._data_paths),
            (_T("advanced"), self._data_advanced)
        )



# top/main frame window class
class AFrame(wx.Frame):
    about_info = None

    def __init__(self,
            parent, ID, title, gist,
            pos = wx.DefaultPosition, size = wx.DefaultSize,
            # gauge toolbar range:
            rang = 1000):
        wx.Frame.__init__(self, parent, ID, title, pos, size)

        self.core_ld = gist

        # setup menubar
        self.menu_ids = {}
        self._mk_menu()

        self.CreateStatusBar()

        self._do_app_art()

        # Trim some sash window height, for the progress bar
        trim_ht = 24

        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        panel = wx.Panel(self, gist.get_new_idval())

        item_sizer = wx.BoxSizer(wx.VERTICAL)

        self.sash_wnd = ASashWnd(
            panel, gist.get_new_idval(),
            _T("main_sash_window"),
            gist, True, size = (size.width, size.height - trim_ht))

        self.gauge = AProgBarPanel(
            panel, gist, gist.get_new_idval(), rang)

        item_sizer.Add(self.sash_wnd, 1, wx.EXPAND, 0)
        item_sizer.SetItemMinSize(self.sash_wnd, 0, 48)
        item_sizer.Add(self.gauge, 0, wx.EXPAND, 0)
        item_sizer.SetItemMinSize(self.gauge, 0, 24)
        panel_sizer.Add(panel, 1, wx.EXPAND, 0)

        panel.SetSizer(item_sizer)
        self.SetSizer(panel_sizer)

        self.Bind(wx.EVT_IDLE, self.on_idle)
        self.Bind(wx.EVT_CLOSE, self.on_quit)
        # Custom event from child handler threads
        self.Bind(EVT_CHILDPROC_MESSAGE, self.on_chmsg, id=self.GetId())

        self.Layout()
        self.SetMinSize((150, 100))

        self.dlg_settings = ASettingsDialog(
            self, gist.get_new_idval(), gist)

        self.SetThemeEnabled(True)
        self.dlg_settings.SetThemeEnabled(True)
        self.sash_wnd.post_contruct()

    def _do_app_art(self):
        getters = (
            getwxdvdbackup_16Icon,
            getwxdvdbackup_24Icon,
            getwxdvdbackup_32Icon,
            getwxdvdbackup_48Icon,
            getwxdvdbackup_64Icon,
            )

        self.icons = icons = wx.IconBundle()
        for fimg in getters:
            icons.AddIcon(fimg())

        self.SetIcons(icons)

    def get_gauge(self):
        return self.gauge


    def _mk_menu(self):
        def id_src():
            return self.core_ld.get_new_idval()
        mb = wx.MenuBar()

        # conventional File menu
        mfile = wx.Menu()
        # items
        self.menu_ids[_T("file_settings")] = cur = id_src()
        mfile.Append(cur, _("&Settings"), _("Program settings"))
        self.Bind(wx.EVT_MENU, self.on_menu, id = cur)
        self.menu_ids[_T("file_quit")] = cur = id_src()
        mfile.Append(cur, _("&Quit"), _("Quit the program"))
        self.Bind(wx.EVT_MENU, self.on_menu, id = cur)
        # put current menu on bar
        mb.Append(mfile, _("&File"))

        # conventional Help menu
        mhelp = wx.Menu()
        # items
        self.menu_ids[_T("help_about")] = cur = id_src()
        mhelp.Append(cur, _("&About"), _("About the program"))
        self.Bind(wx.EVT_MENU, self.on_menu, id = cur)
        # put current menu on bar
        mb.Append(mhelp, _("&Help"))

        # finally, put menu on frame window
        self.SetMenuBar(mb)

    def on_menu(self, event):
        cur = event.GetId()

        if cur == self.menu_ids[_T("file_quit")]:
            self.Close(False)
        elif cur == self.menu_ids[_T("file_settings")]:
            self.do_file_settings()
        elif cur == self.menu_ids[_T("help_about")]:
            self.do_about_dialog()

    def do_file_settings(self):
        if self.core_ld.working():
            wx.MessageBox(
                _("Please wait until the current task is finished, or "
                  "if necessary, cancel the task first."),
                _("A Task is Running!"),
                wx.OK | wx.ICON_EXCLAMATION, self)

            return

        cf = self.core_ld.get_config()
        self.dlg_settings.config_rd(cf)

        rs = self.dlg_settings.ShowModal()

        if rs == wx.ID_OK:
            self.dlg_settings.config_wr(cf)

    def do_about_dialog(self):
        if not self.__class__.about_info:
            import zlib
            import base64

            lic = _licence_data
            t = wxadv.AboutDialogInfo()

            t.SetName(PROG)
            t.SetVersion(_T("{vs} {vn}").format(
                vs = version_string, vn = version_name))
            t.SetDevelopers(program_devs)
            t.SetLicence(zlib.decompress(base64.b64decode(lic)))
            t.SetDescription(self._get_about_desc())
            cpyrt = _T("{year} {name} {addr}").format(
                year = copyright_years,
                name = maintainer_name,
                addr = maintainer_addr)
            if _ucode_type == 'utf-8':
                try:
                    t.SetCopyright(_T("© ") + cpyrt)
                except:
                    t.SetCopyright(_T("(C) ") + cpyrt)
            else:
                t.SetCopyright(_T("(C) ") + cpyrt)
            t.SetWebSite(program_site)
            t.SetIcon(self.icons.GetIcon((64, 64)))

            dw = [
                _T("Nona Wordsworth"),
                _T("Rita Manuel")
                ]
            t.SetDocWriters(dw)
            tr = [
                _T("Saul \"Greek\" Tomey"),
                _("Translation volunteers welcome!"),
                _("Contact {email}.").format(email = maintainer_addr)
                ]
            t.SetTranslators(tr)
            t.SetArtists([_T("I. Burns")])

            self.__class__.about_info = t

        wxadv.AboutBox(self.__class__.about_info)

    def _get_about_desc(self):
        desc = program_desc
        return desc

    def config_rd(self, config):
        pass

    def config_wr(self, config):
        if not config:
            return

        mn = 0
        if self.IsIconized():
            mn = 1
        mx = 0
        if self.IsMaximized():
            mx = 1

        config.WriteInt(_T("iconized"), mn)
        config.WriteInt(_T("maximized"), mx)

        if mn == 0 and mx == 0:
            w, h = self.GetSize()
            x, y = self.GetPosition()
            config.WriteInt(_T("x"), max(x, 0))
            config.WriteInt(_T("y"), max(y, 0))
            config.WriteInt(_T("w"), w)
            config.WriteInt(_T("h"), h)


    def on_idle(self, event):
        self.core_ld.do_idle(event)

    def on_quit(self, event):
        rs = wx.MessageBox(
            _("Do you really want to quit {app}?").format(app = PROG),
            _("Confirm Quit"), wx.YES_NO | wx.ICON_QUESTION, self)

        if rs != wx.YES:
            return

        self.core_ld.do_quit(event)
        self.Destroy()

    def on_chmsg(self, event):
        self.core_ld.do_child_message(event)

    def get_msg_obj(self):
        return self.sash_wnd.get_msg_obj()

    def put_status(self, msg, pane = 0):
        self.SetStatusText(msg, pane)

# A thread for time consuming child process --
# cb is a callback, args is/are arguments to pass
class AChildThread(threading.Thread):
    def __init__(self, topwnd, destwnd_id, cb, args):
        threading.Thread.__init__(self)

        self.topwnd = topwnd
        self.destid = destwnd_id
        self.cb = cb
        self.args = args

        self.status = -1
        self.got_quit = False

        self.per_th = APeriodThread(topwnd, destwnd_id)

    def run(self):
        tid = threading.current_thread().ident
        t = _T("tid {tid}").format(tid = tid)
        self.per_th.start()

        m = _T('enter run')
        wx.PostEvent(self.topwnd, AChildProcEvent(m, t, self.destid))

        r = self.cb(self.args)
        self.status = r
        self.per_th.do_stop()
        if self.got_quit:
            return

        self.per_th.join()

        m = _T('exit run')
        wx.PostEvent(self.topwnd, AChildProcEvent(m, t, self.destid))

    def get_status(self):
        return self.status

    def get_args(self):
        return self.args

    def set_quit(self):
        self.got_quit = True
        self.per_th.do_stop()


# A thread for posting an event at intervals --
class APeriodThread(threading.Thread):
    # OS unames I feel good about sleep in thread; {Free,Open}BSD
    # implement sleep() with nanosleep)() and don't diddle signals,
    # NetBSD and Linux use SIGALRM says manual -- others unknown --
    # use of python's time.sleep() vs. the others here is not
    # inconsequential: the others are causing yet another thread
    # to be created (by python, not here), and sleep is not.
    # Of course, python time.sleep() is not just a wrapped call
    # of libc sleep(3); in fact it will take a float argument.
    th_sleep_ok = (_T("FreeBSD"), _T("OpenBSD"))

    def __init__(self, topwnd, destwnd_id, interval = 1, msg = None):
        threading.Thread.__init__(self)

        self.topwnd = topwnd
        self.destid = destwnd_id
        self.got_stop = False
        self.intvl = interval
        self.tid = 0
        self.tmsg = msg

        if s_eq(os.name, 'posix'):
            self.run_internal = self.run_posix
        else:
            self.run_internal = self.run_other

        u = os.uname()
        if u[0] in self.th_sleep_ok:
            self.snooze = lambda : time.sleep(self.intvl)
        else:
            self.snooze = lambda : select.select([], [], [], self.intvl)

    def run(self):
        self.tid = threading.current_thread().ident
        if not self.tmsg:
            self.tmsg = _T("tid {tid}").format(tid = self.tid)
        self.run_internal()

    def run_posix(self):
        while True:
            self.snooze()
            self.__on_intvl()

            if self.got_stop:
                return

    def run_other(self):
        while True:
            t = threading.Timer(
                self.intvl,
                lambda : self.__on_intvl()
                )

            t.start()
            t.join()

            if self.got_stop:
                return

    def __on_intvl(self, payload = None):
        m = _T('time period')
        if self.got_stop:
            return
        if payload == None:
            payload = self.tmsg
        wx.PostEvent(
            self.topwnd, AChildProcEvent(m, payload, self.destid))

    def do_stop(self):
        self.got_stop = True


# custom wx event for child handler thread to communicate
# with main thread safely (post as pending event)
# see wxPython demo 'demo/PythonEvents.py'
T_EVT_CHILDPROC_MESSAGE = wx.NewEventType()
EVT_CHILDPROC_MESSAGE = wx.PyEventBinder(T_EVT_CHILDPROC_MESSAGE, 1)
class AChildProcEvent(wx.PyCommandEvent):
    def __init__(self, evttag, payload = None, destid = None):
        if destid == None:
            destid = wx.GetApp().GetTopWindow().GetId()

        wx.PyCommandEvent.__init__(
            self,
            T_EVT_CHILDPROC_MESSAGE,
            destid
            )

        self.ev_type = evttag
        self.ev_data = payload

    def get_content(self):
        return (self.ev_type, self.ev_data)


# class to get wanted data from verbose output of "dvd+rw-mediainfo"
# -- a utility from dvd+rw-tools, along with growisofs -- feed lines
# to rx_add() method, get data items with get_data_item(key) (see
# class def for keys) or whole map with get_data()
class MediaDrive:
    #re_flags = 0
    re_flags = re.I

    regx = {}

    regx[_T("drive")] = re.compile(
        '^\s*INQUIRY:\s*\[([^\]]+)\]'
        '\s*\[([^\]]+)\]'
        '\s*\[([^\]]+)\].*$',
        re_flags)
    regx[_T("medium")] = re.compile(
        '^\s*Mounted\s+Media:\s*(\S+),\s+((\S+)(\s+(\S.*\S))?)\s*$',
        re_flags)
    regx[_T("medium id")] = re.compile(
        '^\s*Media\s+ID:\s*(\S.*\S)\s*',
        re_flags)
    regx[_T("medium book")] = re.compile(
        '^\s*Media\s+Book\s+Type:\s*'
        '(\S+),\s+(\S+)(\s+(\S.*\S))?\s*$',
        re_flags)
    regx[_T("medium freespace")] = re.compile(
        '^\s*Free\s+Blocks:\s*(\S+)\s*\*.*$',
        re_flags)
    regx[_T("write speed")] = re.compile(
        '^\s*Write\s+Speed\s*#?([0-9]+):\s*'
        '([0-9]+(\.[0-9]+)?)\s*x.*$',
        re_flags)
    regx[_T("current write speed")] = re.compile(
        '^\s*Current\s+Write\s+Speed:\s*([0-9]+(\.[0-9]+)?)\s*x.*$',
        re_flags)
    regx[_T("write performance")] = re.compile(
        '^\s*Write\s+Performance:\s*(\S.*\S)\s*',
        re_flags)
    regx[_T("speed descriptor")] = re.compile(
        '^\s*Speed\s+Descriptor\s*#?([0-9]+):\s*'
        '([0-9]+)/[0-9]+\s+R@([0-9]+(\.[0-9]+)?)\s*x.*'
        '\sW@([0-9]+(\.[0-9]+)?)\s*x.*$',
        re_flags)
    regx[_T("presence")] = re.compile(
        '((^\s*|.*\s)(no|non-DVD)\s+media)\s+mounted.*$',
        re_flags)

    def __init__(self, name = None):
        if name:
            self.name = name
        else:
            self.name = _("[no name]")

        self.data = {}

        self.data[_T("drive")] = []
        for i in (1, 2, 3):
            self.data[_T("drive")].append(_("unknown"))
        self.data[_T("medium")] = {}
        self.data[_T("medium id")] = _T("")
        self.data[_T("medium book")] = _T("")
        self.data[_T("medium freespace")] = 0
        self.data[_T("write speed")] = []
        self.data[_T("current write speed")] = -1
        self.data[_T("write performance")] = _T("")
        self.data[_T("speed descriptor")] = []
        self.data[_T("presence")] = _T("")

    def rx_add(self, lin):
        for k in self.regx:
            m = self.regx[k].match(lin)
            if m:
                if s_eq(k, "drive"):
                    for i in (1, 2, 3):
                        if m.group(i):
                            self.data[k][i - 1] = m.group(i).strip()
                elif s_eq(k, "medium id"):
                    self.data[k] = m.group(1)
                elif s_eq(k, "medium"):
                    self.data[k][_T("id")] = m.group(1)
                    self.data[k][_T("type")] = m.group(3)
                    if m.group(5):
                        self.data[k][_T("type_ext")] = m.group(5)
                    else:
                        self.data[k][_T("type_ext")] = _T("")
                    self.data[k][_T("type_all")] = m.group(2)
                elif s_eq(k, "medium book"):
                    self.data[k] = m.group(2)
                elif s_eq(k, "medium freespace"):
                    self.data[k] = int(m.group(1))
                elif s_eq(k, "write speed"):
                    self.data[k].append(float(m.group(2)))
                elif s_eq(k, "current write speed"):
                    self.data[k] = float(m.group(1))
                elif s_eq(k, "write performance"):
                    self.data[k] = m.group(1)
                elif s_eq(k, "presence"):
                    self.data[k] = m.group(1)
                elif s_eq(k, "speed descriptor"):
                    self.data[k].append(
                        (
                            float(m.group(3)),
                            float(m.group(5)),
                            int(m.group(2))
                        ) )
                else:
                    err_(
                        _("Internal mechanism jammed: please grease")
                    )
                    return False

                return True

        return False

    # return array of write speeds *but* use "Speed Descriptor#N"
    # if no "Write Speed #N" found: dvd+rw-mediainfo source says
    # "Some DVD+units return CD-R descriptors here" and if so the
    # speed descriptors are not printed
    def get_write_speeds(self):
        ra = []
        d = self.get_data_item(_T("write speed"))
        if d:
            for s in d:
                ra.append(s)
        else:
            d = self.get_data_item(_T("speed descriptor"))
            for s in d:
                ra.append(s[1])

        return ra


    def get_data(self):
        return self.data

    def get_data_item(self, key):
        if key in self.data:
            return self.data[key]
        return None


#
# classes for the task of getting POSIX df -kP results for a directory
#

# data structure class to hold df -kP output
class StructDfData:
    def __init__(self,
                 filesystem = None,
                 blocks_total = -1,
                 blocks_used = -1,
                 blocks_avail = -1,
                 percent_capacity = 100,
                 mount_point = None,
                 size_of_block = 1024):
        """ data structure class to hold df -kP output
            Use like C struct, no logic implemented, only
            get procedures for convenience, although members
            may be accessed directly
        """
        self.filesys  = filesystem
        self.blktotal = blocks_total
        self.blkused  = blocks_used
        self.blkavail = blocks_avail
        self.pctused  = percent_capacity
        self.mountpt  = mount_point
        self.blk_sz   = size_of_block

    # getter procs for convenience -- minus 'get...' prefix for brevity
    def filesystem(self):
        return self.filesys

    def blocks_total(self):
        return self.blktotal

    def blocks_used(self):
        return self.blkused

    def blocks_avail(self):
        return self.blkavail

    def percent_capacity(self):
        return self.pctused

    def mount_point(self):
        return self.mountpt

    def size_of_block(self):
        return self.blk_sz

# regex class to masticate df -kP child process lines
class RegexDf_kP:
    #re_flags = 0
    re_flags = re.I

    regx = {}
    regx_err = {}

    # Filesystem     1024-blocks    Used Available Capacity Mounted on
    regx_header_strict = re.compile(
        '^\s*Filesystem\s+([0-9]+)-blocks\s+Used\s+'
        'Available\s+Capacity\s+Mounted\s+on\s*$',
        re_flags)
    regx_header_loose = re.compile(
        '^.*\s([0-9]+)-blocks\s.*$',
        re_flags)
    if False:
        regx[_T("header")] = regx_header_loose
    else:
        regx[_T("header")] = regx_header_strict
    # output line: 1st field 'Filesystem' match is loose
    # to allow unexpected names; likewise last field, mount point,
    # with additional consideration of (ill advised) whitespace
    regx[_T("line")] = re.compile(
        '^\s*(\S+)\s+'
        '([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)%\s+'
        '(\S+(?:\s+\S+)*)\s*$',
        re_flags)
    # Error message format is not specified by POSIX, but is
    # similar in BSD and GNU (differing in single quotes) --
    # check stderr with a loose regex, and optionally match
    # for BSD or GNU error messages
    regx_err[_T("error")] = re.compile(
        '^\s*(\S+(?:\s+\S+)*)\s*$',
        #'^\s*(\S+.*)\s*$',
        re_flags)
    regx_err[_T("error_opt")] = re.compile(
        '^\s*df:\s*\'?(\S+(?:\s+\S+)*)\'?\s*:\s*(\S+(?:\s+\S+)*)\s*$',
        re_flags)

    def __init__(self, name = None):
        """CTor for default init; one optional arg "name" might be
           be useful for single arg parsing ('df -kP /just_one'),
           but this class will not refuse lines to parse in the
           case of output for multiple df args
        """
        if name:
            self.name = name
        else:
            self.name = _T("")

        self.data = {
            _T("blocksize") : None,
            _T("output")    : [],
            _T("error")     : []
            }

    # call with each stderr line -- by default throws
    # at error -- pass do_execpt = False and will
    # return error string, or False if no error
    # (no error means empty or whitespace only line)
    def rx_add_error(self, lin, do_execpt = True):
        lin = lin.strip("\r\n")
        ret_err = False
        m = self.regx_err[_T("error")].match(lin)
        if m:
            nam = m.group(1)
            mopt = self.regx_err[_T("error_opt")].match(lin)
            if mopt:
                nam = mopt.group(1)
                s = _("Error: '{n}' - '{e}'").format(
                    n = nam, e = mopt.group(2))
            else:
                s = _("Error: '{s}'").format(s = nam)

            self.data[_T("error")].append((nam, s))

            if do_execpt:
                self._raise(s)
            else:
                ret_err == s

        return ret_err

    # call with each stdout line -- no return value,
    # throws on error
    def rx_add(self, lin):
        lin = lin.strip("\r\n")
        ok = False
        for k in self.regx:
            m = self.regx[k].match(lin)
            if m:
                if s_eq(k, "header"):
                    self.data[_T("blocksize")] = int(m.group(1))
                    ok = True

                elif s_eq(k, "line"):
                    if self.data[_T("blocksize")]:
                        bsz = self.data[_T("blocksize")]
                    else:
                        bsz = 1024

                    dat = StructDfData(
                        filesystem       = m.group(1),
                        blocks_total     = int(m.group(2)),
                        blocks_used      = int(m.group(3)),
                        blocks_avail     = int(m.group(4)),
                        percent_capacity = int(m.group(5)),
                        mount_point      = m.group(6),
                        size_of_block    = bsz)
                    self.data[_T("output")].append(dat)
                    ok = True

                else:
                    self._raise(_("Internal error"))

                break

        if not ok:
            self._raise(_("df -k -P unexpected output ") + lin)

    def _raise(self, s = _("df -kP error")):
        raise self.__class__.RegexDf_kP_except(s)

    # list of StructDfData
    def get_data(self):
        return self.data[_T("output")]

    # list of tuple (arg_name, error_string_of_our_making)
    def get_errors(self):
        return self.data[_T("error")]

    class RegexDf_kP_except(Exception):
        def __init__(self, msg):
            Exception.__init__(self, msg)

# class to check directories for free space
class FsDirSpaceCheck:
    def __init__(self, checkme):
        """Check directory arg(s) in 'checkme' for free space
           'checkme' may be a string for single check, or an
           iterable of strings
        """
        if isinstance(checkme, unicode) or isinstance(checkme, str):
            chk = [checkme]
        else:
            chk = checkme

        self.chks = []
        self.errs = []
        # result ok
        self.roks = []

        for d in chk:
            try:
                self.chk_dir(d)
                self.chk_access(d)
                self.chks.append(d)
            except (OSError, IOError,
                    self.__class__._internal_except) as e:
                self.errs.append([d, e.strerror])

        self.error = (0, _("No error"))

    def chk_dir(self, d):
        st = os.stat(d)
        if stat.S_ISDIR(st.st_mode):
            return True
        self._raise(errno.ENOTDIR, _("Not a directory"))

    def chk_access(self, d):
        fd, nm = tempfile.mkstemp(_T("file"), _T("test"), d)
        fp = os.fdopen(fd, _T("wrb"), 128)
        fp.write(_T("This test file should not exist unless error"))
        fp.flush()
        fp.close()
        os.unlink(nm)
        return True

    def _raise(self, e, s):
        raise self.__class__._internal_except(e, s)

    class _internal_except:
        def __init__(self, eno, est):
            self.errno = eno
            self.strerror = est

    def _do_ok(self, ch_proc, raise_on_unknown_error = True):
        rlin1, rlin2, rlinx = ch_proc.get_read_lists()
        rx = RegexDf_kP()

        for l in rlin2:
            try:
                rx.rx_add_error(l)
            except RegexDf_kP.RegexDf_kP_except:
                t = rx.get_errors()[-1]
                try:
                    i = self.chks.index(t[0])
                    del self.chks[i]
                    self.errs.append(t)
                    continue
                except ValueError:
                    pass

            if raise_on_unknown_error:
                raise Exception(
                    _("df error '{err}', no arg match").format(err = l))

        try:
            for l in rlin1:
                rx.rx_add(l)
        except RegexDf_kP.RegexDf_kP_except as s:
            raise Exception(_("Error parsing df -kP: '{0}'").format(s))

        res = rx.get_data()
        if len(res) != len(self.chks):
            raise Exception(_(
                "Result length mismatch parsing df -kP: "
                ": args {c}, results {r}").format(
                    c = len(self.chks), r = len(res)))

        # Depend on df output lines appearing in order of command
        # args; else, madness, as df doesn't print arg with line.
        idx = 0
        for r in res:
            d = self.chks[idx]
            self.roks.append((d, r))
            idx += 1

        scode, sig, sstat = ch_proc.get_status_string()
        if scode:
            self._raise(errno.EINVAL, sstat)

    def get_results(self):
        return (self.roks, self.errs)

    def go(self):
        try:
            if not self.chks:
                self._raise(errno.EINVAL, _("No valid args"))

            # df with -kP should not need lang. env vars, as POSIX
            # specifies the POSIX locale for -P, but to be safe . . .
            xenv = {
                _T("LANG"): _T("C"),
                _T("LC_ALL"): _T("C"),
                _T("LC_MESSAGES"): _T("C")
                }

            senv = {}
            for k in os.environ:
                if s_eq(k[:3], "LC_"):
                    senv[k] = os.environ[k]
                    os.environ[k] = _T("C")

            xcmd = _T("df")
            xcmdargs = [ xcmd, _T("-k"), _T("-P") ]
            for d in self.chks:
                xcmdargs.append(d)

            parm_obj = ChildProcParams(xcmd, xcmdargs, xenv, 0)
            ch_proc = ChildTwoStreamReader(parm_obj)

            is_ok = ch_proc.go_and_read()
            ch_proc.wait()

            for k in senv:
                os.environ[k] = senv[k]

            if not is_ok:
                et = ch_proc.error_tuple
                if len(et) == 2:
                    self._raise(et[0], et[1])
                elif len(et) == 4:
                    self._raise(et[2], et[3])
                else:
                    self._raise(errno.EINVAL, _("Unknown error"))

            self._do_ok(ch_proc)
        except (OSError, self.__class__._internal_except) as e:
            self.error = (e.errno, e.strerror)
            return False

        return True

# Check for temp directories with sufficient available space,
# make sorted result available
class TempDirsCheck:
    # default env vars specifying temp dirs
    default_env = [_T("TMPDIR"), _T("TMP"), _T("TEMP")]

    # default temp dirs typical under Unix
    default_dir = [
        _T("/tmp"), _T("/var/tmp"), _T("/usr/tmp"), _T("$HOME")]

    # The default min_space is based on free block values found
    # on double layer DVD blanks, and is not necessarily correct,
    # but info from a few manufacturer's discs all shows
    # 4173824 2048 blocks free, so padding up to a pretty
    # decimal number,
    #   8400000 == (4200000 * 2048 + 1023) / 1024
    # which is a tight fit for a really full double layer DVD,
    # if there are other processes writing on the temporary fs,
    # so using code should consider passing a larger minimum.
    def __init__(self,
                 min_space = 8400000,
                 use_env = True,
                 use_def = True,
                 use_mod_tempfile = True,
                 addl_dirs = [],
                 do_expand = False,
                 sort_type = "none"):
        """min_space is in 1024 byte blocks, default based on DVD+DL
           env are standard or common under Unix; def defined in this
           class, mod_tempfile from the Python module (which *must*
           be imported for reasons other than this), and using code
           may specify more in addl_dirs which, if do_expand is True,
           will be checked for leading '$' and have it substituted from
           env, and ignored if that fails; finally sort_type spec's
           how results should be sorted and may have values "big",
           "small", or anything else, with big meaning most available
           space first, little meaning least available first, or
           anything else preventing sorting
        """
        self.min_space = min_space
        self.sort_type = sort_type
        chks = []

        for d in addl_dirs:
            if do_expand:
                v = self._expand(d)
            else:
                v = d
            if not v or v in chks:
                continue
            chks.append(v)

        if use_env:
            for e in self.__class__.default_env:
                if not e in os.environ:
                    continue
                v = os.environ[e]
                if not v in chks:
                    chks.append(v)

        if use_def:
            for v in self.__class__.default_dir:
                v = self._expand(v)
                if not v:
                    continue
                if not v in chks:
                    chks.append(v)

        if use_mod_tempfile:
            try:
                v = tempfile.gettempdir()
                if v and not v in chks:
                    chks.append(v)
            except OSError:
                pass

        self.chks = chks

        # array of (dirpath, StructDfData),
        # call do() and use return, or later call get_result()
        self.res = []

        # if error occurs, this should have a descriptive string
        self.error = None

    def do(self):
        if not self.chks:
            self.error = _T("No arguments to check")
            return self.res

        try:
            chk = FsDirSpaceCheck(self.chks)

            r_chk = chk.go()

            r_ok, r_ng = chk.get_results()

            if not r_chk:
                e, s = chk.error
                self._init_error(_(
                    "Failed: {s} ({n}) -- "
                    "{ne} err, {ok} good").format(
                        n = e, s = s, ne = len(r_ng), ok = len(r_ok)))

            for (d, m) in r_ng:
                self._init_error(_(
                    "df error on {d} '{m}'").format(d = d, m = m))

            res = []
            for (d, r) in r_ok:
                if r.blocks_avail() >= self.min_space:
                    res.append((d, r))

            lB = lambda a,b: b[1].blocks_avail() - a[1].blocks_avail()
            lS = lambda a,b: a[1].blocks_avail() - b[1].blocks_avail()
            if self.sort_type == "big":
                res.sort(cmp = lB)
            elif self.sort_type == "small":
                res.sort(cmp = lS)

            self.res = res

        except Exception as s:
            self._init_error(s)
        except:
            self._init_error(_T("an unknown error occurred"))

        return self.res

    def get_result(self):
        return self.res

    def get_error(self):
        return self.error

    # private
    def _init_error(self, tail = _T("")):
        if self.error == None:
            self.error = _T("")
        else:
            self.error += _T("\n")
        self.error += tail

    # private
    def _expand(self, d):
        c1 = d[0]
        if s_ne(c1, _T("$")):
            return d

        sl = d.find(_T("/"))
        if sl < 0:
            k = d[1:]
            if k in os.environ:
                k = os.environ[k].strip()
                if k:
                    return k
            return False

        if sl < 2:
            return False

        k = d[1:sl]
        if k in os.environ:
            k = os.environ[k].strip()
            if k:
                k = k.rstrip(_T("/")) + d[sl:]
                return k

        return False


# The gist of it: much of the code in this file concerns
# GUI setup and logic -- that's unavoidable -- but the GUI
# classes should have little or no general logic, most of
# which goes here (other than support classes).
# This will also have manage interaction among GUI elements
# in areas that would require GUI classes to know too much
# about and have references to other GUI classes; so this will
# keep ref's to some GUI objects, be passed to GUI c'tors,
# and provide a few procedures.
class ACoreLogiDat:
    opt_values = collections.namedtuple(
        _T('opt_values'),
        [_T('s_whole'), _T('s_hier'), _T('t_disk'),
            _T('t_dev'), _T('t_direct')])(
        0, 1, 0, 1, 2)

    work_msg_interval = 5
    work_msg_last_int = 0
    work_msg_last_idx = 0
    work_msgs = (
        _("Working"),
        _T("."),
        _T(". ."),
        _T(". . ."),
        _T(". . . ."),
        _T(". . . . ."),
        _T(". . . . . ."),
        _T(". . . . . . ."),
        _T(". . . . . . . ."),
        _T(". . . . . . . . ."),
        _T(". . . . . . . . . ."),
        _T(". . . . . . . . . . ."),
        _T(". . . . . . . . . . . ."),
        _T(". . . . . . . . . . . . ."),
        _T(". . . . . . . . . . . . . ."),
        _T(". . . . . . . . . . . . . . ."),
        _T(". . . . . . . . . . . . . . . ."),
        _T("--------------------------------"),
        _T(". . . . . . . . . . . . . . . ."),
        _T(". . . . . . . . . . . . . . ."),
        _T(". . . . . . . . . . . . . ."),
        _T(". . . . . . . . . . . . ."),
        _T(". . . . . . . . . . . ."),
        _T(". . . . . . . . . . ."),
        _T(". . . . . . . . . ."),
        _T(". . . . . . . . ."),
        _T(". . . . . . . ."),
        _T(". . . . . . ."),
        _T(". . . . . ."),
        _T(". . . . ."),
        _T(". . . ."),
        _T(". . ."),
        _T(". ."),
        _T("."),
        _T("Hey Now!")
        )

    def __init__(self, app):
        self.app = app
        self.source = None
        self.target = None
        self.panes_enabled = True

        self.gauge_wnd = None
        self.msg_wnd = None
        self.statwnd = None
        self.vol_wnd = None

        # set by app object after top window is ready by call to method
        # set_ready_topwnd() -- at which point other data members must
        # have been set
        self.topwnd = None
        self.topwnd_id = -1

        # do set in 1st OnIdle -- just once, and set this true
        self.iface_init = False

        self.target_force_idx = -1

        self.cur_task_items = {}

        self.cur_out_file = None
        self.cur_tempfile = None
        self.all_tempfile = []
        self.last_burn_speed = None

        self.ch_thread = None

        self.in_check_op = False

        self.tid = threading.current_thread().ident

        self.uname = os.uname()
        sys = self.uname[0]

        # tuple of tuples each item being:
        # key printed to stdout by dd-dvd -vn re. DVD volume info,
        # length (space padded) of the field,
        # a {mk,gen,grow}isofs option char to set the field,
        # a default value for the field,
        # a label for a GUI interface object
        #  minus some not wanted here
        self.v_inf_keys = (
          (_T("system_id"),          32, _T("-sysid"), sys, _T("System ID")),
          (_T("volume_id"),          32, _T("-V"), _T(""), _T("Volume ID")),
          (_T("volume_set_id"),     128, _T("-volset"), _T(""), _T("Volume Set ID")),
          (_T("publisher_id"),      128, _T("-publisher"), _T(""), _T("Publisher")),
          (_T("data_preparer_id"),  128, _T("-p"), _T(""), _T("Data Preparer")),
          (_T("application_id"),    128, _T("-A"), PROG, _T("Application ID")),
          (_T("copyright_id"),       37, _T("-copyright"), _T(""), _T("Copyright")),
          (_T("abstract_file_id"),   37, _T("-abstract"), _T(""), _T("Abstract File")),
          (_T("bibliographical_id"), 37,
           _T("-biblio"), _T(""), _T("Bibliographical ID"))
          )
        self.v_inf_map = {}
        self.v_inf_vec = []
        for i in range(len(self.v_inf_keys)):
            it = self.v_inf_keys[i]
            self.v_inf_map[it[0]] = i
            self.v_inf_vec.append(it)

        # settings per task
        self.checked_input_blocks  = 0
        self.checked_input_arg     = _T('')
        self.checked_input_devnode = _T('')
        self.checked_input_mountpt = _T('')
        self.checked_input_devstat = None
        self.target_data = None
        self.checked_media_blocks   = 0
        self.checked_output_arg     = _T('')
        self.checked_output_devnode = _T('')
        self.checked_output_devstat = None


    def enable_panes(self, benable, rest = False):
        if self.panes_enabled == benable:
            return
        self.panes_enabled = benable

        non = (self.target.run_button, )

        if rest:
            self.source.restore_all(non)
            self.target.restore_all(non)
        else:
            self.source.enable_all(benable, non)
            self.target.enable_all(benable, non)

        if benable:
            self.source_opt_id_change(
                self.source.type_opt.GetSelection(), True)

    def set_ready_topwnd(self, wnd):
        self.topwnd = wnd
        self.topwnd_id = wnd.GetId()

        config = self.get_config()
        self.topwnd.config_rd(config)
        self.target.config_rd(config)
        self.source.config_rd(config)

    def do_quit(self, event):
        try:
            self.ch_thread.set_quit()
        except:
            _dbg(_T("self.ch_thread.set_quit(): Except 1 in do_quit()"))

        self.do_cancel(True)

        try:
            config = self.get_config()
            self.source.config_wr(config)
            self.target.config_wr(config)
            self.topwnd.config_wr(config)
        except:
            _dbg(_T("self.get_config(): Exception 2 in do_quit()"))

    def do_idle(self, event):
        if self.iface_init == False:
            do_src = True
            do_tgt = True

            try:
                config = self.get_config()
                if config.HasEntry(_T("source_type_opt")):
                    do_src = False
                if config.HasEntry(_T("target_type_opt")):
                    do_tgt = False
            except:
                pass

            self.iface_init = True
            ov = self.opt_values
            if do_src:
                self.source.type_opt.SetSelection(ov.s_whole)
                self.source.do_opt_id_change(ov.s_whole)
            if do_tgt:
                self.target.type_opt.SetSelection(ov.t_dev)
                self.target.do_opt_id_change(ov.t_dev)
                self.target_opt_id_change(ov.t_dev)


    def target_select_node(self, node):
        if self.working():
            self.target.set_target_text(self.checked_output_arg, True)
        elif node != self.checked_output_arg:
            if not self.get_is_fs_target():
                self.reset_target_data()
                self.target.run_button.Enable(False)

    def target_opt_id_change(self, t_id, quiet = False):
        self.target_force_idx = -1
        self.target.set_button_select_node_label()

    def source_select_node(self, node):
        if self.working():
            self.source.set_source_text(self.checked_input_arg, True)
        elif node != self.checked_input_arg:
            self.reset_source_data()
            self.target.run_button.Enable(False)

    def source_opt_id_change(self, s_id, quiet = False):
        if not self.target:
            return

        ov = self.opt_values
        t_id = self.target.type_opt.GetSelection()

        if s_id == ov.s_whole:
            self.target.type_opt.EnableItem(ov.t_direct, True)
            self.get_volinfo_wnd().Enable(False)
            if self.target_force_idx >= 0:
                self.target.type_opt.SetSelection(
                    self.target_force_idx)
                self.target_force_idx = -1
                if not quiet:
                    msg_line_WARN(_("Warning:"))
                    msg_INFO(_(
                        " The destination has"
                        " been changed from 'burner'"
                        " to 'simultaneous' (as it was earlier)."
                        ))

        elif s_id == ov.s_hier:
            if t_id == ov.t_direct:
                self.target.type_opt.SetSelection(ov.t_dev)
                self.target.do_opt_id_change(ov.t_dev)
                self.target_force_idx = ov.t_direct
                if not quiet:
                    msg_line_WARN(_("Warning:"))
                    msg_INFO(_(
                        " advanced type backup"
                        " cannot be simultaneous; a temporary"
                        " directory is necessary --\n\tthe destination"
                        " has been changed to 'burner'."
                        ))

            self.target.type_opt.EnableItem(ov.t_direct, False)
            self.get_volinfo_wnd().Enable(True)

        self.target.set_button_select_node_label()


    def get_new_idval(self, wx_new_id = False):
        if wx_new_id:
            return wx.NewId()
        return WXObjIdSource()()

    def get_config(self):
        return self.app.get_config()

    def get_vol_datastructs(self):
        """provide data structs prepared in _init_ for volume info panel
        """
        return (self.v_inf_keys, self.v_inf_map, self.v_inf_vec)

    def set_source_wnd(self, wnd):
        self.source = wnd

    def set_target_wnd(self, wnd):
        self.target = wnd

    def set_gauge_wnd(self, wnd = None):
        if wnd == None:
            wnd = self.topwnd
        self.gauge_wnd = wnd.get_gauge()

    def set_msg_wnd(self, wnd):
        self.msg_wnd = wnd

    def set_vol_wnd(self, wnd):
        self.vol_wnd = wnd

    def get_gauge_wnd(self):
        return self.gauge_wnd

    def get_msg_wnd(self):
        return self.msg_wnd

    def get_stat_wnd(self):
        if self.statwnd == None:
            self.statwnd = self.topwnd

        return self.statwnd

    def get_volinfo_wnd(self):
        return self.target.panel_volinfo

    def get_volinfo_ctl(self):
        return self.get_volinfo_wnd().get_panel()

    def get_volinfo_dict(self):
        return self.get_volinfo_crl().get_fields()

    #
    # boolean checks for current op type based on values
    # from GUI objects
    #

    def get_is_whole_backup(self):
        v = self.opt_values.s_whole
        s = self.source.type_opt.GetSelection()
        if s == v:
            return True
        return False

    def get_is_hier_backup(self):
        v = self.opt_values.s_hier
        s = self.source.type_opt.GetSelection()
        if s == v:
            return True
        return False

    def get_is_fs_target(self):
        v = self.opt_values.t_disk
        s = self.target.type_opt.GetSelection()
        if s == v:
            return True
        return False

    def get_is_devnode_target(self):
        v = (self.opt_values.t_dev, self.opt_values.t_direct)
        s = self.target.type_opt.GetSelection()
        if s in v:
            return True
        return False

    def get_is_dev_tmp_target(self):
        v = self.opt_values.t_dev
        s = self.target.type_opt.GetSelection()
        if s == v:
            return True
        return False

    def get_is_dev_direct_target(self):
        v = self.opt_values.t_direct
        s = self.target.type_opt.GetSelection()
        if s == v:
            return True
        return False

    def get_child_from_thread(self):
        if self.ch_thread:
            return (self.ch_thread.get_args())[2]
        return None

    # working state
    # update_working* below are for busy updates to gauge
    # and status bar

    def working(self):
        if self.ch_thread != None:
            return True
        return False

    def update_working_gauge(self):
        if not self.cur_task_items:
            return

        g = self.get_gauge_wnd()

        try:
            nm = self.cur_task_items[_T("taskname")]
            lambda_key = _T("lambda_") + nm
            try:
                self.cur_task_items[lambda_key](g)
            except:
                if s_eq(nm, 'blanking'):
                    l = lambda g: self.update_working_blanking(g)
                elif s_eq(nm, 'cprec'):
                    l = lambda g: self.update_working_cprec(g)
                elif s_eq(nm, 'dd-dvd'):
                    l = lambda g: self.update_working_dd_dvd(g)
                elif s_eq(nm, 'growisofs-hier'):
                    l = lambda g: self.update_working_growisofs_hier(g)
                elif s_eq(nm, 'growisofs-whole'):
                    l = lambda g: self.update_working_growisofs(g)
                elif s_eq(nm, 'growisofs-direct'):
                    l = lambda g: self.update_working_growisofs(g)
                else:
                    l = lambda g: g.Pulse()

                self.cur_task_items[lambda_key] = l
                self.cur_task_items[lambda_key](g)
        except:
            g.Pulse()

    def update_working_blanking(self, gauge_wnd):
        gauge_wnd.Pulse()

    def update_working_dd_dvd(self, gauge_wnd):
        g = gauge_wnd

        try:
            st = os.stat(self.cur_out_file)
        except:
            g.Pulse()
            return

        rng = g.GetRange()

        tot = self.checked_input_blocks << 11 # * 2048

        val = st.st_size * rng / tot
        g.SetValue(val)

    def update_working_growisofs_hier(self, gauge_wnd):
        g = gauge_wnd

        try:
            ln = self.cur_task_items[_T("line")]
        except:
            g.Pulse()
            return

        try:
            rx = self.cur_task_items[_T("growisofs-hier-rx")]
        except:
            rx = re.compile('^\s*([0-9]+\.[0-9]+)\s*%\s+.*$')
            self.cur_task_items[_T("growisofs-hier-rx")] = rx

        m = rx.match(ln)

        if not m:
            g.Pulse()
            return

        cur = float(m.group(1)) / 100.00

        rng = float(g.GetRange())

        val = int(cur * rng)
        g.SetValue(val)

    def update_working_growisofs(self, gauge_wnd):
        g = gauge_wnd

        try:
            ln = self.cur_task_items[_T("line")]
        except:
            g.Pulse()
            return

        try:
            rx = self.cur_task_items[_T("growisofs-rx")]
        except:
            rx = re.compile('^\s*([0-9]+)/([0-9]+)\s.*$')
            self.cur_task_items[_T("growisofs-rx")] = rx

        m = rx.match(ln)

        if not m:
            g.Pulse()
            return

        cur = int(m.group(1))
        sz  = int(m.group(2))

        if sz < 1:
            g.Pulse()
            return

        rng = g.GetRange()

        val = cur * rng / sz
        g.SetValue(val)


    def update_working_cprec(self, gauge_wnd):
        g = gauge_wnd

        try:
            ln = self.cur_task_items[_T("line")]
        except:
            g.Pulse()
            return

        try:
            rx = self.cur_task_items[_T("cprec-rx")]
        except:
            rx = re.compile('^\s*X\s+(\S.*\S)\s+size\s+([0-9]+)\s*$')
            self.cur_task_items[_T("cprec-rx")] = rx

        m = rx.match(ln)

        if not m:
            g.Pulse()
            return

        fn = m.group(1)
        sz = int(m.group(2))

        if sz < 1:
            g.Pulse()
            return

        try:
            st = os.stat(fn)
        except:
            g.Pulse()
            return

        rng = g.GetRange()

        val = st.st_size * rng / sz
        g.SetValue(val)

    def working_msg(self, stat_wnd = None):
        if not self.working():
            return

        if stat_wnd == None:
            stat_wnd = self.get_stat_wnd()

        msgs = self.__class__.work_msgs
        idx = self.work_msg_last_idx
        stat_wnd.put_status(msgs[idx])
        self.work_msg_last_idx = (idx + 1) % len(msgs)

    def update_working_msg(self, stat_wnd = None):
        last = self.work_msg_last_int
        cur = time.time()
        per = cur - last

        if per >= self.work_msg_interval:
            self.work_msg_last_int = cur
            self.working_msg(stat_wnd)

    # various device/medium checks:

    # stat dev and compare time with time tuple (mtime, ctime)
    def do_devtime_check(self, dev, stato):
        st = x_lstat(dev)
        if st and stato:
            mt = stato.st_mtime
            ct = stato.st_ctime
            if st.st_mtime == mt and st.st_ctime == ct:
                return True

        return False

    # stat dev and compare time with time tuple (mtime, ctime)
    def do_devstat_check(self, dev, stato):
        chkdev = os.path.realpath(dev)
        st = x_lstat(chkdev, False, False)
        if st and stato:
            if (st.st_ino == stato.st_ino and
                st.st_dev == stato.st_dev and
                st.st_mtime == stato.st_mtime and
                st.st_ctime == stato.st_ctime
                ):
                return True

        return False

    # stat dev and compare time with time tuple (mtime, ctime)
    def do_burn_pre_check(self, dat = None):
        stmsg = self.get_stat_wnd()

        if dat:
            outdev = dat[_T("target_dev")]
        else:
            outdev = self.checked_output_devnode

        if not outdev:
            self.do_target_check()
            outdev = self.checked_output_devnode

        if not outdev:
            return False

        eq = self.do_devstat_check(outdev, self.checked_output_devstat)
        if not eq:
            if not self.check_target_prompt(outdev, 0):
                m = _("Target medium check failed")
                msg_line_ERROR(m)
                stmsg.put_status(m)
                return False
            else:
                return True

        if not self.do_in_out_size_check():
            return False

        return True

    # compare input size to capacity *after* data members are set
    def check_target_prompt(
        self, outdev, wait_retry, blank_async = False, verbose= False):
        while True:
            if not (self.do_target_medium_check(outdev, wait_retry)
                and self.do_in_out_size_check(blank_async, verbose)):
                m += _(
                    "\nMedium check failed. Try another disc?")
                r = self.dialog(m, _T("yesno"), wx.YES_NO)
                if r != wx.YES:
                    return False
            else:
                break

        return True

    # compare input size to capacity *after* data members are set
    def do_in_out_size_check(self, blank_async = False, verbose= False):
        stmsg = self.get_stat_wnd()

        d = self.target_data
        mm = d.get_data_item(_T("medium"))
        if mm[_T("type_ext")]:
            m = mm[_T("type_ext")]
        else:
            m = mm[_T("type")]
        dbl = re.search('(DL|Dual|Double)', m, re.I)

        m = mm[_T("type")]
        if mm[_T("type_ext")]:
            m = m + _T(" ") + mm[_T("type_ext")]
        rw = re.search('([\+-]\s*RW|re-?write)', m, re.I)

        if self.checked_input_blocks > self.checked_media_blocks:
            m = _(
                "Target medium needs {0} free blocks, found only {1}."
                ).format(
                self.checked_input_blocks, self.checked_media_blocks)
            msg_line_ERROR(m)
            stmsg.put_status(m)

            if rw:
                m += _(
                    "\nMedium appears re-writable. Attempt blanking?")
                r = self.dialog(m, _T("yesno"), wx.YES_NO)
                if r == wx.YES:
                    r = self.do_blank(d.name, blank_async)
                    if blank_async:
                        return r

                    if not r:
                        return False

                    self.do_target_check(reset = True)
                    if self.checked_output_arg:
                        return True

            return False

        if dbl:
            hbl = self.checked_media_blocks / 2
            if self.checked_input_blocks <= hbl:
                m = _(
                    "Disc capacity is {0} blocks, but only {1} needed"\
                    " -- use a single layer DVD blank disc."
                    ).format(
                             self.checked_media_blocks,
                             self.checked_input_blocks,
                             )
                msg_line_ERROR(m)
                stmsg.put_status(m)
                return False

        m = _("Good: {0} free blocks needed, medium has {1}.").format(
            self.checked_input_blocks, self.checked_media_blocks)
        if verbose:
            msg_line_GOOD(m)
        stmsg.put_status(m)

        return True


    # call do_target_check() below, but assume new media has
    # just been inserted and drive might need time to settle
    def do_target_check_insert(self,
                        target_dev = None,
                        async_blank = False,
                        reset = False):
        settle_time = 5
        settle_tries= 5

        cf = self.get_config()
        opth = cf.GetPath()

        cf.SetPath(_T("/main/settings/rundata"))

        cfkey = _T("disc_settle_time")
        if cf.HasEntry(cfkey):
            settle_time = cf.ReadInt(cfkey)

        cfkey = _T("disc_settle_retries")
        if cf.HasEntry(cfkey):
            settle_tries = cf.ReadInt(cfkey)

        cf.SetPath(opth)

        while True:
            wx.GetApp().Yield(True)

            t = time.time()
            wx.Sleep(settle_time)
            t = time.time() - t
            msg_line_INFO(
                _("Slept {secs} to let drive settle.").format(secs = t))

            self.do_target_check(
                target_dev, async_blank, reset, settle_tries)

            if self.checked_output_devnode:
                return True

            if settle_tries < 1 or self.get_is_dev_direct_target():
                break

            msg_line_WARN(_(
                "target medium checked failed; will sleep "
                "{secs} more seconds, then try again "
                "({tries} more retries)"
                ).format(secs = settle_time, tries = settle_tries))

            settle_tries -= 1

        return False


    # general check of target, including medium as necessary
    # param retry_num affects warn/error messages: should be
    # verbose only on the last try (retry_num == 0)
    def do_target_check(self,
                        target_dev = None,
                        async_blank = False,
                        reset = False,
                        retry_num = 0):
        if self.get_is_fs_target():
            return

        if reset:
            self.reset_target_data()

        if not target_dev:
            target_dev = self.target.input_select_node.GetValue()

        if target_dev:
            if self.get_is_dev_direct_target():
                src = self.checked_input_devnode
                try:
                    same = os.path.samefile(src, target_dev)
                    if same:
                        m = _("Can only do direct type burn using "
                              "two different drives, but "
                              "drives {s} and {t} are the same."
                              ).format(s = src, t = target_dev)
                        msg_line_ERROR(m)
                        self.reset_target_data()
                        return
                    else:
                        m = _("Direct: source {s} and target {t}"
                            ).format(s = src, t = target_dev)
                        msg_line_INFO(m)
                except:
                    m = _("Cannot stat source {s} or target {t}"
                        ).format(s = src, t = target_dev)
                    msg_line_ERROR(m)
                    self.reset_target_data()
                    return

            st = self.checked_output_devstat
            if not st:
                if self.check_target_prompt(target_dev, retry_num):
                    if async_blank:
                        return True
                    st = self.checked_output_devstat
                else:
                    st = False

            if st and self.do_devstat_check(target_dev, st):
                self.checked_output_arg = target_dev
                return

        self.reset_target_data()

    # misc. procedures

    def reset_source_data(self):
        self.checked_input_blocks  = 0
        self.checked_input_arg     = _T('')
        self.checked_input_devnode = _T('')
        self.checked_input_mountpt = _T('')
        self.checked_input_devstat = None


    def reset_target_data(self):
        self.target_data = None
        self.checked_media_blocks   = 0
        self.checked_output_arg     = _T('')
        self.checked_output_devnode = _T('')
        self.checked_output_devstat = None


    def cb_go_and_read(self, n, s):
        """Callback for ChildTwoStreamReader.go_and_read()
        invoked from temporary thread
        """
        if not self.working():
            return -1

        e = AChildProcEvent(_T("l%d") % n, s, self.topwnd_id)
        wx.PostEvent(self.topwnd, e)

        return 0

    # called with status of a child process
    def do_child_status(self, stat, chil):
        self.get_gauge_wnd().SetValue(0)

        if self.in_check_op:
            self.read_check_inp_op_result(chil)
            if stat == 0:
                self.target.run_button.Enable(True)
            else:
                self.target.run_button.Enable(False)
            self.in_check_op = False
            if stat == 0:
                target_dev = self.target.input_select_node.GetValue()
                try:
                    rpth = os.path.realpath(target_dev)
                    s1 = os.stat(rpth)
                    s2 = os.stat(self.checked_input_devnode)
                    if not os.path.samestat(s1, s2):
                        self.do_target_check(async_blank = True)
                except:
                    pass

        elif stat == 0 and chil.get_extra_data():
            # With success of read task, ready for burn task:
            # chil.get_extra_data() returns None if user option
            # was backup to local storage, else it returns a dict
            # with data needed to proceed with burn.
            #
            d = chil.get_extra_data()
            outf = d[_T("target_dev")]
            mdone = None
            merr  = None

            if d[_T("in_burn")] == True:
                # this means burn was just done
                self.reset_target_data()
                m = _("Burn succeeded!. Would you like to burn "
                    "another? If yes, put a new burnable blank in "
                    "the burner addressed by node '{0}'.").format(outf)
                r = self.dialog(
                    m, _T("sty"),
                    wx.YES_NO|wx.ICON_QUESTION)
                if r == wx.YES:
                    d[_T("in_burn")] = False
                    r = self.do_target_check_insert(outf, reset = True)
                    if r:
                        d[_T("target_dev")] = self.checked_output_arg
                        if self.do_burn(chil, d):
                            msg_line_INFO(_("Additional burn started."))
                            return
                    else:
                        merr = _("Media Error")

            else:
                m = _("Prepared to burn backup. "
                    "Make sure a writable blank disc is ready in "
                    "the burner controlled by node '{0}'.").format(outf)
                r = self.dialog(
                    m, _T("sty"),
                    wx.OK|wx.CANCEL|wx.ICON_INFORMATION)
                if r == wx.OK:
                    r = self.do_target_check_insert(outf, reset = True)
                    if r:
                        d[_T("target_dev")] = self.checked_output_arg
                        if self.do_burn(chil, d):
                            msg_line_INFO(_("Burn started."))
                            return
                        else:
                            merr = _("Burn Failed")
                    else:
                        merr = _("Media Error")

                #else:
                #    msg_line_INFO(_("Burn cancelled"))

            if merr:
                msg_line_ERROR(merr)
                self.get_stat_wnd().put_status(merr)
            elif mdone:
                msg_line_GOOD(mdone)
                self.get_stat_wnd().put_status(mdone)

        elif stat != 0 and chil.get_extra_data():
            pass

        self.target.set_run_label()
        self.cleanup_run()
        self.enable_panes(True, True)

    # for a msg_*() invocation using monospace face -- static
    def mono_message(
            self, prefunc = None, monofunc = None, postfunc = None):
        if prefunc:
            prefunc()
        if monofunc:
            mw = self.get_msg_wnd()
            mw.set_mono_font()
            monofunc()
            mw.set_default_font()
        if postfunc:
            postfunc()

    def do_child_message(self, event):
        # mth: boolean 'in main thread'
        mth = True
        tid = threading.current_thread().ident
        if tid != self.tid:
            # may use GUI only from main thread
            mth = False

        # message window object
        msgo = self.get_msg_wnd()
        # status line onject
        slno = self.get_stat_wnd()

        typ, dat = event.get_content()

        m = _T('')
        try:
            m = dat.rstrip(_T(' \n\r\t'))
            _dbg(_T("%s: %s") % (typ, m))
        except:
            _dbg(_T("%s: <no data>") % typ)

        if mth and s_eq(typ, 'time period'):
            if not self.in_check_op:
                self.update_working_gauge()
                self.update_working_msg(slno)

            if dat and s_eq(dat, "pulse"):
                if self.gauge_wnd:
                    self.gauge_wnd.Pulse()

        elif mth and s_eq(typ, 'l1'):
            if not self.in_check_op:
                self.mono_message(
                    prefunc = lambda : msg_line_INFO(_T('1:')),
                    monofunc = lambda : msg_(_T(" %s") % m))

            if self.cur_task_items:
                self.cur_task_items[_T("linelevel")] = 1
                self.cur_task_items[_T("line")] = m

        elif mth and s_eq(typ, 'l2'):
            if not self.in_check_op:
                self.mono_message(
                    prefunc = lambda : msg_line_WARN(_T('2:')),
                    monofunc = lambda : msg_(_T(" %s") % m))

            if self.cur_task_items:
                self.cur_task_items[_T("linelevel")] = 2
                self.cur_task_items[_T("line")] = m

        elif mth and s_eq(typ, 'l-1'):
            if not self.in_check_op:
                ok, m, dat = self.get_stat_data_line(m)
                if ok:
                    if dat[1]:
                        msg_line_ERROR(m)
                    # TODO: verbosity flag
                    elif False:
                        msg_line_INFO(m)
                else:
                    self.mono_message(
                        prefunc =lambda : msg_line_WARN(_T('WARNING:')),
                        monofunc=lambda : msg_(_T(" %s") % m))

        elif mth and s_eq(typ, 'enter run'):
            self.target.set_cancel_label()
            m = _T(
                "New thread {0} started for child processes").format(m)
            _dbg(m)
            m = _T("")
            msg_line_INFO(m)
            slno.put_status(m)

        elif s_eq(typ, 'exit run'):
            # thread join() can throw
            j_ok = True
            try:
                self.ch_thread.join()
            except:
                j_ok = False

            ch = self.get_child_from_thread()
            st = self.ch_thread.get_status()
            stat, bsig, sstr = ch.get_status_string(False)

            self.ch_thread = None
            self.work_msg_last_idx = 0

            if mth:
                cmd = ch.xcmd
                if not cmd:
                    cmd = _("Child process")
                m = _("{command} status is \"{status}\"").format(
                    command = cmd, status = sstr)

                if stat:
                    msg_line_ERROR(m)
                else:
                    msg_line_GOOD(m)

                if not j_ok:
                    m = _("Thread join() fail")
                    msg_line_ERROR(m)

                if stat == 0:
                    m = _("Success!")
                elif ((bsig and stat == signal.SIGINT) or
                      (stat == eintr and ch.is_growisofs())):
                    m = _("Cancelled!")
                else:
                    m = _("Failed!")

                slno.put_status(m)

            self.do_child_status(stat, ch)

        elif mth:
            msg_line_ERROR(_("unknown thread event '{0}'").format(typ))

    def get_stat_data_line(self, line, ch_proc = None):
        if not ch_proc:
            ch_proc = self.get_child_from_thread()
        if not ch_proc:
            return (False, line, None)

        dat = ch_proc.get_stat_line_data(line)
        if dat:
            m = _(
                "'{cmd}' has \"{sstr}\"; "
                "exit status {code}, "
                "terminated by signal is: '{sig}' -- "
                "arguments and environment: {ae}"
                ).format(
                    cmd = dat[0], code = dat[1],
                    sig = dat[2], sstr = dat[3],
                    ae = dat[4]
                )
            return (True, m, dat)
        else:
            return (False, line, None)


    def dialog(self, msg, typ = _T("msg"), sty = None):
        if s_eq(typ, "msg"):
            if sty == None:
                sty = wx.OK | wx.ICON_INFORMATION
            return wx.MessageBox(msg, PROG, sty, self.topwnd)

        if s_eq(typ, "yesno"):
            if sty == None:
                sty = wx.YES_NO | wx.ICON_QUESTION
            return wx.MessageBox(msg, PROG, sty, self.topwnd)

        if s_eq(typ, "sty"):
            # just use 'sty' argument
            return wx.MessageBox(msg, PROG, sty, self.topwnd)

        if s_eq(typ, "input"):
            # use 'sty' argument as default text
            return wx.GetTextFromUser(msg, PROG, sty, self.topwnd)

        if s_eq(typ, "intinput"):
            # use 'sty' argument as tuple w/ addl. args
            prmt, mn, mx, dflt = sty
            try:
                return wx.GetNumberFromUser(
                    msg, prmt, PROG, dflt, mn, mx, self.topwnd)
            except AttributeError:
                # Ouch Phoenix don't def GetNumberFromUser(), no alt.?
                n = mn - 1
                ndef = _T("{num}").format(num = dflt)
                while n < mn:
                    t = wx.GetTextFromUser(msg, PROG, ndef, self.topwnd)
                    if len(t) < 1:
                        # cancelled
                        n = dflt
                        break
                    try:
                        n = float(t)
                        if n > mx or n < mn:
                            raise Exception(_T("Bad number"))
                    except:
                        e = _("Enter a number: {mn} to {mx}").format(
                            mn = mn, mx = mx)
                        sx = wx.OK | wx.ICON_ERROR
                        wx.MessageBox(e, PROG, sx, self.topwnd)
                        n = mn - 1

                return n

        if s_eq(typ, "choiceindex"):
            # use 'sty' argument as list of choices
            try:
                return wx.GetSingleChoiceIndex(
                        msg, PROG, sty, self.topwnd)
            except AttributeError:
                # phoenix, ain't got no GetSingleChoiceIndex()
                r = wx.GetSingleChoice(msg, PROG, sty, self.topwnd)
                try:
                    return sty.index(r)
                except:
                    return -1

    #
    # Utilities to help with files and directories
    #

    def get_usable_temp_directory(self, verbose = False):
        use_env = True
        use_def = True
        use_mod_tempfile = True
        do_expand = True
        addl = []

        cf = self.get_config()
        opth = cf.GetPath()
        # Want the TempDirsCheck object to handle optional env. expand
        oexp = cf.IsExpandingEnvVars()
        cf.SetExpandEnvVars(False)

        cf.SetPath(_T("/main/settings/rundata"))
        cfkey = _T("temp_dirs")
        if cf.HasEntry(cfkey):
            try:
                tt = cf.Read(cfkey).strip()
                t = _T(tt)
            except:
                try:
                    t = cf.Read(cfkey).strip()
                except:
                    t = _T("")
            if t:
                addl = t.split(_T(':'))
                for i in range(len(addl)):
                    addl[i] = addl[i].strip()

        cfkey = _T("expand_env")
        if cf.HasEntry(cfkey):
            t = cf.ReadInt(cfkey)
            if t:
                do_expand = True
            else:
                do_expand = False

        cfkey = _T("use_env_tempdir")
        if cf.HasEntry(cfkey):
            t = cf.ReadInt(cfkey)
            if t:
                use_env = True
            else:
                use_env = False

        cfkey = _T("use_def_tempdir")
        if cf.HasEntry(cfkey):
            t = cf.ReadInt(cfkey)
            if t:
                use_def = True
            else:
                use_def = False

        cfkey = _T("use_mod_tempfile_tempdir")
        if cf.HasEntry(cfkey):
            t = cf.ReadInt(cfkey)
            if t:
                use_mod_tempfile = True
            else:
                use_mod_tempfile = False

        cf.SetExpandEnvVars(oexp)
        cf.SetPath(opth)

        if self.checked_input_blocks:
            src_blks = self.checked_input_blocks
            # Add ~500MB as margin
            margin = 524288000
            # 1024 byte blocks
            min_space = ((src_blks << 11) + margin) >> 10
            msg_line_WARN(_(
                "Requiring temporary space with {freespace} "
                "1024-byte blocks free: source DVD requires "
                "{srcsize1024} 1024-byte blocks ("
                "{srcsize2048} 2048-byte blocks), with "
                "{margin} 1024-byte blocks as margin"
                ).format(freespace = min_space,
                         srcsize1024 = src_blks << 1,
                         srcsize2048 = src_blks,
                         margin = margin >> 10))
        else:
            min_space = 8700000
            msg_line_WARN(_(
                "Requiring default temporary space with "
                "{freespace} 1024-byte blocks free"
                ).format(freespace = min_space))

        chk = TempDirsCheck(
            use_env = use_env, use_def = use_def,
            use_mod_tempfile = use_mod_tempfile, do_expand = do_expand,
            min_space = min_space, addl_dirs = addl)

        res = chk.do()
        err = chk.get_error()

        if err:
            msg_line_WARN(_("directory errors:\n") + err)

        if not res:
            self.dialog(_(
                "Cannot find a directory with enough available "
                "space for temporary data!"
                "\n\n"
                "Please select the 'File' menu, 'Settings' item, "
                "and provide a path to a directory that your user "
                "or group identity may write to, and which has "
                "a minimum of nine (9) gigabytes of available "
                "free space."
                ), sty = wx.ICON_ERROR)
            return False

        if verbose:
            for (d, r) in res:
                # count in 2048 byte blocks
                bcnt = (r.blocks_avail() * r.size_of_block()) >> 11
                msg_line_INFO(_(
                    "dir '{d}' has {cnt} DVD-size blocks free").format(
                        d = d, cnt = bcnt))

        return res

    def get_tempfile(self):
        da = self.get_usable_temp_directory()
        if not da:
            msg_line_ERROR(_T("CANNOT FIND SUFFICIENT TEMP SPACE."))
            return False

        d = da[0][0]
        msg_line_INFO(_(
            "using temporary directory '{tdir}'").format(tdir = d))

        try:
            ofd, outf = tempfile.mkstemp(_T('.iso'), _T('dd-dvd-'), d)
            self.cur_tempfile = outf
            return (ofd, outf)
        except OSError as e:
            m = _("Error making temporary file: '{0}' (errno {1})"
                ).format(e.strerror, e.errno)
            msg_line_ERROR(m)
            self.get_stat_wnd().put_status(m)
            self.dialog(m, _T("msg"), wx.OK|wx.ICON_EXCLAMATION)
            return False

    # not *the* temp dir like /tmp. but a temporary directory
    def get_tempdir(self):
        da = self.get_usable_temp_directory()
        if not da:
            msg_line_ERROR(_T("CANNOT FIND SUFFICIENT TEMP SPACE."))
            return False

        d = da[0][0]
        msg_line_INFO(_(
            "using temporary directory '{tdir}'").format(tdir = d))

        try:
            outf = tempfile.mkdtemp(_T('-iso'), _T('cprec-'), d)
            self.cur_tempfile = outf
            return outf
        except OSError as e:
            m = _("Error making temporary directory: '{0}' (errno {1})"
                ).format(e.strerror, e.errno)
            msg_line_ERROR(m)
            self.get_stat_wnd().put_status(m)
            self.dialog(m, _T("msg"), wx.OK|wx.ICON_EXCLAMATION)
            return False

    def get_openfile(self, outf, fl = os.O_WRONLY|os.O_CREAT|os.O_EXCL):
        try:
            # octal prefix 0o (zero,letter-o) requires Python 2.6;
            # Python 3 requires that prefix
            ofd = os.open(outf, fl, 0o666)
            return (ofd, outf)
        except OSError as e:
            m = _("Error opening file '{2}': '{0}' (errno {1})"
                ).format(e.strerror, e.errno, outf)
            msg_line_ERROR(m)
            self.get_stat_wnd().put_status(m)
            self.dialog(m, _T("msg"), wx.OK|wx.ICON_EXCLAMATION)
        except AttributeError:
            msg_line_ERROR(_("Internal error opening {0}").format(outf))
        except Exception as e:
            msg_line_ERROR(
                _("BASE EXCEPTION '{s}' opening {f}").format(
                    f = outf, s = e))
        except:
            msg_line_ERROR(
                _("UNKNOWN EXCEPTION opening {0}").format(outf))

        return False

    # must call this in try: block, it return single, tuple or False
    def get_outfile(self, outf):
        is_direct = self.get_is_dev_direct_target()

        if is_direct and self.get_is_whole_backup():
            tof = (_T("/dev/fd/0"), _T("/dev/stdin"))
            for f in tof:
                st = x_lstat(f, True, True)
                if st:
                    return f
            # TODO: make fifo e.g.
            #tnam = self.get_tempdir()
            #f = os.path.join(tnam, _T("wxDVDBackup"))
            #try os.mkfifo(f, 0700)
            # etc.
            return False
        elif self.get_is_fs_target() and self.get_is_whole_backup():
            if not outf:
                ttf = self.cur_tempfile
                try:
                    tfd, tnam = self.get_tempfile()
                    m = _("No output file given!\nUse '{0}'?").format(
                        tnam)
                    r = self.dialog(m, _T("yesno"), wx.YES_NO)
                    if r == wx.YES:
                        self.cur_tempfile = ttf
                        return (tfd, tnam)
                    else:
                        try:
                            os.unlink(tnam)
                            os.close(tfd)
                        except:
                            pass
                except:
                    # error making temp file! handle elsewhere
                    pass
                self.cur_tempfile == ttf
                return False

            self.cleanup_run()
            st = x_lstat(outf)

            if st:
                outreg = outf
                sym = stat.S_ISLNK(st.st_mode)
                nsl = 0
                ext = True
                reg = True

                if sym:
                    while True:
                        outreg = os.readlink(outreg)
                        st = x_lstat(outreg)
                        if not st:
                            break
                        if stat.S_ISLNK(st.st_mode):
                            nsl += 1
                            continue
                        break

                    outreg = os.path.realpath(outf)
                    st = x_lstat(outreg)

                if st:
                    reg = stat.S_ISREG(st.st_mode)
                else:
                    ext = False
                    reg = False

                if sym and ext:
                    if not reg:
                        m = _("{0} is a symbolic link to {1}.").format(
                            outf, outreg)
                        if nsl > 0:
                            m = _(
                                "{0} (with {1} symlinks between.)"
                                ).format(m, nsl)
                        self.dialog(m, _T("msg"), wx.OK|wx.ICON_ERROR)
                        return False

                    m = _(
                        "{0} is a symbolic link to file {1}."
                        ).format(outf, outreg)
                    if nsl > 0:
                        m = _(
                            "{0} is a symbolic link to file {1} "
                            "(with {2} symlinks between.)\n"
                            "Should you overwrite {3}?"
                            ).format(outf, outreg, nsl, outreg)
                    r = self.dialog(m, _T("yesno"), wx.YES_NO)
                    if r != wx.YES:
                        return False
                    return self.get_openfile(
                        outreg, os.O_WRONLY|os.O_TRUNC)

                if sym:
                    m = _(
                        "{0} is a symbolic link to non-existing {1}.\n"
                        "Use the name '{2}'?"
                        ).format(outf, outreg, outreg)
                    r = self.dialog(m, _T("yesno"), wx.YES_NO)
                    if r != wx.YES:
                        return False

                    return self.get_openfile(outreg)

                if reg:
                    m = _(
                        "{0} is an existing file.\nReplace it?"
                        ).format(outf)
                    r = self.dialog(m, _T("yesno"), wx.YES_NO)
                    if r != wx.YES:
                        return False

                if not ext:
                    return self.get_openfile(outf)

                if not reg:
                    m = _(
                        # TRANSLATORS: {0} and {1} are both the same
                        # file name
                        "{0} is an existing non-regular file.\n"
                        "Provide a new target, or remove file {1}"
                        ).format(outf, outf)
                    self.dialog(m, _T("msg"), wx.OK|wx.ICON_INFORMATION)
                    return False

                return self.get_openfile(outf, os.O_WRONLY|os.O_TRUNC)

            # not empty string, and not extant
            return self.get_openfile(outf)

        if self.get_is_fs_target() and self.get_is_hier_backup():
            if not outf:
                ttf = self.cur_tempfile
                try:
                    tnam = self.get_tempdir()
                    m = _(
                        "No output directory given!\nUse '{0}'?"
                        ).format(tnam)
                    r = self.dialog(m, _T("yesno"), wx.YES_NO)
                    if r == wx.YES:
                        self.cur_tempfile = ttf
                        return tnam
                    else:
                        try:
                            os.rmdir(tnam)
                        except:
                            pass
                except:
                    # error making temp file! handle elsewhere
                    pass
                self.cur_tempfile == ttf
                return False

            self.cleanup_run()
            st = x_lstat(outf, True)

            if st and not stat.S_ISDIR(st.st_mode):
                m = _(
                 "{0} exists. Please choose another directory name."
                 ).format(outf)
                self.dialog(m, _T("msg"), wx.OK|wx.ICON_ERROR)
                return False

            if st:
                m = _(
                 "Directory {0} exists. Remove and replace (lose) it?"
                 ).format(outf)
                r = self.dialog(m, _T("yesno"), wx.YES_NO)
                if r == wx.YES:
                    self.rm_temp(outf)
                else:
                    return False

            try:
                # octal prefix 0o (zero,letter-o) requires Python 2.6;
                # Python 3 requires that prefix
                os.mkdir(outf, 0o777)
            except OSError as e:
                m = _(
                    "Failed, error creating directory \"{0}\":"
                    "'{1}' (errno {2})"
                    ).format(outf, e.strerror, e.errno)
                msg_line_ERROR(m)
                self.get_stat_wnd().put_status(m)
                self.dialog(m, _T("msg"), wx.OK|wx.ICON_EXCLAMATION)
                return False

            return outf

        #else from: if self.get_is_fs_target():
        else:
            return False


    # after done with temp file/dir, remove it --
    # populated directories created by cprec could sometimes be
    # handled with python shutil.rmtree, but that might not deal
    # with unexpected modes that might be set (e.g. dirs w/o x).
    def rm_temp(self, tmp):
        if not tmp:
            return

        try:
            os.chown(tmp, os.getuid(), os.getgid())
            # octal prefix 0o (zero,letter-o) requires Python 2.6;
            # Python 3 requires that prefix
            os.chmod(tmp, 0o700)
        except:
            pass

        st = x_lstat(tmp)
        if not st:
            # BAD, should not happen
            return

        if not stat.S_ISDIR(st.st_mode):
            os.unlink(tmp)
            return

        lst = os.listdir(tmp)

        for ent in lst:
            np = os.path.join(tmp, ent)
            self.rm_temp(np)

        os.rmdir(tmp)

    def cleanup_run(self):
        try:
            self.rm_temp(self.cur_tempfile)
        except:
            _dbg(_T("cleanup_run: exept in rm_temp(self.cur_tempfile)"))
        self.cur_tempfile = None
        self.get_gauge_wnd().SetValue(0)


    def check_target_dev(self, target_dev):
        st = x_lstat(target_dev, True, False)
        if not st or not (
                stat.S_ISCHR(st.st_mode) or
                stat.S_ISBLK(st.st_mode)):
            m = _("Please enter the target DVD burner device node"
                  " in the 'backup target' field")
            msg_line_ERROR(m)
            self.get_stat_wnd().put_status(m)
            r = self.dialog(m, _T("input"), target_dev)
            if len(r) > 0 and r != target_dev:
                target_dev = r
                self.target.set_target_text(r)
                return self.check_target_dev(target_dev)
            return False

        s2 = os.stat(self.checked_input_devnode)
        same = os.path.samestat(st, s2)
        if not same and not self.do_target_medium_check(target_dev):
            return False

        return target_dev

    #
    # Procedures to run the work tasks
    #

    def do_check(self, dev):
        self.reset_source_data()
        self.enable_panes(False, False)
        if not self.do_dd_dvd_check(dev):
            self.enable_panes(True, True)


    def do_cancel(self, quiet = False):
        is_gr = False

        if self.working():
            ch = self.get_child_from_thread()
            ch.kill(signal.SIGUSR1)
            is_gr = ch.is_growisofs()

        if not quiet:
            m = _("Operation cancelled")
            msg_line_INFO(m)
            self.get_stat_wnd().put_status(m)
            if is_gr:
                m = _("Please give burn process (growisofs) time "
                      "to exit cleanly -- do not kill it\nor "
                      "the burner drive might be left unusable "
                      "until reboot")
                msg_line_INFO(m)

        self.cleanup_run()
        self.target.set_run_label()
        self.enable_panes(True, True)


    def do_run(self, target_dev):
        if self.target.get_cancel_mode():
            self.do_cancel()
            return

        if self.working():
            msg_line_WARN(_("Already busy!"))
            return

        self.get_stat_wnd().put_status(_T(""))

        if self.get_is_whole_backup():
            if self.get_is_dev_direct_target():
                if not target_dev:
                    m = _("Please set a target device (with disc) "
                          "and click the 'Check settings' button")
                    msg_line_ERROR(m)
                    self.dialog(m, _T("msg"))
                    return
                if not self.do_burn_pre_check():
                    m = _("Please be sure the source and target "
                          "do not change after the Check button")
                    msg_line_ERROR(m)
                    self.dialog(m, _T("msg"))
                    return

            self.enable_panes(False, False)
            self.target.set_cancel_label()
            if not self.do_dd_dvd_run(target_dev):
                self.enable_panes(True, True)
                self.target.set_run_label()
        elif self.get_is_hier_backup():
            self.enable_panes(False, False)
            self.target.set_cancel_label()
            if not self.do_cprec_run(target_dev):
                self.enable_panes(True, True)
                self.target.set_run_label()
        else:
            msg_line_ERROR(_("ERROR: internal inconsistency, not good"))

    def do_burn(self, ch_proc, dat = None):
        do_it = True

        if do_it and dat == None:
            dat = ch_proc.get_extra_data()
        if do_it and dat == None:
            do_it = False
        if do_it and dat[_T("in_burn")] == True:
            # this means burn was just done
            do_it = False

        if do_it and not self.do_burn_pre_check(dat):
            do_it = False

        if not do_it:
            return False

        typ = dat[_T("source_type")]

        if s_eq(typ, "hier"):
            if self.do_mkiso_blocks():
                do_it = self.do_burn_hier(ch_proc, dat)
            else:
                return False
        elif s_eq(typ, "whole"):
            do_it = self.do_burn_whole(ch_proc, dat)
        else:
            msg_line_ERROR(typ)
            return False

        if do_it:
            self.enable_panes(False, False)

        return do_it

    def get_speed_select_prompt(self, name = None):
        if self.target_data == None:
            return _("Select a speed or action from the list:")

        if name:
            pmt = _(
                "Select a speed or action from the list for {0}:\n"
                ).format(name)
        else:
            pmt = _(
                "Select a speed or action from the list for drive:\n")

        return pmt + self.get_drive_medium_info_string(_T("        "))

    def get_drive_medium_info_string(self, prefix = _T("")):
        if self.target_data == None:
            return _("Select a speed or action from the list:")

        d = self.target_data

        drv = d.get_data_item(_T("drive"))
        fw = drv[2]
        model = drv[1]
        drv = drv[0]

        b = d.get_data_item(_T("medium book"))
        if not b:
            b = _('[no medium book type found]')

        m = d.get_data_item(_T("medium"))
        if m:
            i = int(m[_T("id")].rstrip(_T("hH")), 16)
            ext = _T("")
            if m[_T("type_ext")]:
                ext = _T(" (%s)") % m[_T("type_ext")]
            m = _T('%s%s [%02X], booktype %s') % (m[_T("type")], ext, i, b)
        else:
            m = _('[no medium type description found]')

        mi = d.get_data_item(_T("medium id"))
        if not mi:
            mi = _('[no medium id found] - booktype {0}').format(b)

        medi = _T("%s - %s") % (mi, m)

        fr = d.get_data_item(_T("medium freespace"))

        ret = _(
            # TRANSLATORS: {pfx} is a prefix, probably just whitespace
            # for alignment of several lines,
            # {drv} is a drive manufacturer name,
            # {mdl} is drive model,
            # {fw} is firmware version,
            # {medi} is DVD blank medium description,
            # {frb} is free space in bytes
            # {fr} is free space in 2048 byte blocks
            "{pfx}{drv}, model {mdl} (firmware {fw})\n"
            "{pfx}{medi}\n"
            "{pfx}freespace {frb} bytes ({fr} blocks)\n"
            ).format(pfx = prefix,
                     drv = drv, mdl = model,
                     fw = fw, medi = medi,
                     frb = fr * 2048, fr = fr)

        return ret

    def get_burn_speed(self, procname):
        if self.target_data:
            name = self.target_data.name
            spds = self.target_data.get_write_speeds()

        if not name:
            name = _('target')

        if not self.target_data or len(spds) < 1:
            spds = (2.0, 4.0, 6.0, 8.0, 12.0, 16.0, 18.0, 24.0)
        chcs = []

        prec = 8
        for s in spds:
            chcs.append(_T("{flt:.{pr}} (~ {int}KB/s)").format(
                flt = s, int = int(s * 1385), pr = prec))

        nnumeric = len(chcs)
        ndefchoice = nnumeric / 2
        inc = 0

        chcs.append(_("{0} default").format(procname))
        def_idx = nnumeric + inc
        inc += 1
        chcs.append(_("Enter a speed"))
        ent_idx = nnumeric + inc
        inc += 1
        if self.last_burn_speed:
            chcs.append(_("Use same speed as last burn"))
            last_idx = nnumeric + inc
            inc += 1
        else:
            last_idx = -1
        chcs.append(_("Cancel burn"))
        cnc_idx = nnumeric + inc
        inc += 1

        m = self.get_speed_select_prompt(name)
        r = self.dialog(m, _T("choiceindex"), chcs)

        if r < 0:
            return False
        elif r < nnumeric:
            self.last_burn_speed = _T("%u") % spds[r]
        elif r == def_idx:
            self.last_burn_speed = None
        elif r == last_idx:
            return self.last_burn_speed
        elif r == ent_idx:
            title = _T("Enter the speed number you would like")
            sdef = self.last_burn_speed
            if not sdef:
                sdef = _T("%u") % spds[ndefchoice]
            mn = 1
            mx = 256
            m = _("Min {mn}, max {mx}:").format(mn = mn, mx = mx)
            self.last_burn_speed = self.dialog(title, _T("intinput"),
                (m, mn, mx, int(sdef)))
            if self.last_burn_speed < 1:
                self.last_burn_speed = _T("%u") % spds[ndefchoice]
        elif r == cnc_idx:
            return False
        else:
            self.last_burn_speed = _T("%u") % spds[ndefchoice]

        return self.last_burn_speed


    # command execution code
    #

    def get_cmd_path(self, cmd):
        cf = self.get_config()
        opth = cf.GetPath()
        cf.SetPath(_T("/main/settings/tools"))
        if cf.HasEntry(cmd):
            t = cf.Read(cmd).strip()
            if t:
                cmd = t
        cf.SetPath(opth)
        return cmd

    def do_burn_whole(self, ch_proc, dat):
        stmsg = self.get_stat_wnd()
        self.cur_task_items = {}

        try:
            outdev  = os.path.realpath(dat[_T("target_dev")])
        except:
            outdev  = dat[_T("target_dev")]
        srcfile = dat[_T("source_file")]
        dat[_T("in_burn")] = True

        msg_line_INFO(_(
            '\nburn from temporary file "{0}" to device {1}').format(
                srcfile, outdev))

        self.cur_out_file = None
        self.cur_task_items[_T("taskname")] = _T('growisofs-whole')
        self.cur_task_items[_T("taskfile")] = None
        self.cur_task_items[_T("taskdirect")] = False

        xcmd = self.get_cmd_path(_T('growisofs'))
        xcmdargs = []
        xcmdargs.append(xcmd)

        spd = self.get_burn_speed(xcmd)
        if spd == False:
            self.do_cancel()
            return False
        if spd:
            xcmdargs.append(_T("-speed=%s") % spd)

        xcmdargs.append(_T("-dvd-video"))
        xcmdargs.append(_T("-dvd-compat"))

        xcmdargs.append(_T("-Z"))
        xcmdargs.append(_T("%s=%s") % (outdev, srcfile))

        stmsg.put_status(_("Running {0} for {1}").format(xcmd, srcfile))

        parm_obj = ChildProcParams(xcmd, xcmdargs)
        ch_proc.reset_read_lists()
        ch_proc.get_status(True)
        ch_proc.set_command_params(parm_obj)
        ch_proc.set_growisofs()

        self.child_go(ch_proc)
        return True

    def do_burn_hier(self, ch_proc, dat):
        stmsg = self.get_stat_wnd()
        self.cur_task_items = {}

        try:
            outdev  = os.path.realpath(dat[_T("target_dev")])
        except:
            outdev  = dat[_T("target_dev")]
        srcdir = dat[_T("source_file")]
        dat[_T("in_burn")] = True

        msg_line_INFO(_(
            '\nburn from temporary directory "{0}" to {1}').format(
                srcdir, outdev))

        self.cur_out_file = None
        self.cur_task_items[_T("taskname")] = _T('growisofs-hier')
        self.cur_task_items[_T("taskfile")] = None
        self.cur_task_items[_T("taskdirect")] = False

        xcmd = self.get_cmd_path(_T('growisofs'))
        xcmdargs = []
        xcmdargs.append(xcmd)

        spd = self.get_burn_speed(xcmd)
        if spd == False:
            self.do_cancel()
            return False
        if spd:
            xcmdargs.append(_T("-speed=%s") % spd)

        xcmdargs.append(_T("-dvd-compat"))

        xcmdargs.append(_T("-Z"))
        xcmdargs.append(outdev)

        xcmdargs.append(_T("-dvd-video"))
        xcmdargs.append(_T("-gui"))
        xcmdargs.append(_T("-uid"))
        xcmdargs.append(_T("0"))
        xcmdargs.append(_T("-gid"))
        xcmdargs.append(_T("0"))
        xcmdargs.append(_T("-D"))
        xcmdargs.append(_T("-R"))

        xlst = dat[_T("vol_info")]
        keys, vmap, vvec = self.get_vol_datastructs()

        for i in vvec:
            k = i[0]
            if not k in xlst:
                if len(i[3]) > 0:
                    xcmdargs.append(i[2])
                    xcmdargs.append(i[3])
                continue
            s = xlst[k]
            lmax = i[1]
            while len(s) > lmax:
                m = _(
                    "Volume data field '{0}' has max length {1}\n"
                    "'{2}'\nhas length {3}\n"
                    "Edit field, or cancel burn?"
                    ).format(i[4], lmax, s, len(s))
                r = self.dialog(
                    m, _T("yesno"), wx.YES_NO|wx.CANCEL|wx.ICON_QUESTION)
                if r == wx.CANCEL:
                    self.do_cancel()
                    return
                elif r != wx.YES:
                    s = _T("")
                    continue
                m = _("Please make value length no more than {0}"
                    ).format(lmax)
                s = self.dialog(m, _T("input"), s)
                dic = {}
                dic[k] = s
                self.get_volinfo_ctl().set_source_info(dic, True)
            if not s:
                if len(i[3]) > 0:
                    xcmdargs.append(i[2])
                    xcmdargs.append(i[3])
                continue
            xcmdargs.append(i[2])
            xcmdargs.append(s)
            msg_line_INFO(_("add iso fs option {0} '{1}'").format(
                i[2], s))

        xcmdargs.append(srcdir)

        stmsg.put_status(_("Running {0} for {1}").format(xcmd, srcdir))

        parm_obj = ChildProcParams(xcmd, xcmdargs)
        ch_proc.reset_read_lists()
        ch_proc.get_status(True)
        ch_proc.set_command_params(parm_obj)
        ch_proc.set_growisofs()

        self.child_go(ch_proc)
        return True


    def do_cprec_run(self, target_dev, dev = None):
        stmsg = self.get_stat_wnd()
        self.cur_task_items = {}

        if not dev and self.source and self.source.dev:
            dev = self.source.dev

        if not dev:
            m = _("Select a mount point")
            msg_line_ERROR(m)
            stmsg.put_status(m)
            self.dialog(m, _T("msg"), wx.OK|wx.ICON_EXCLAMATION)
            return False

        origdev = dev
        realdev = os.path.realpath(dev)
        if realdev and s_ne(realdev, dev):
            dev = realdev
            msg_line_INFO(_(
                'using source mount "{0}" for "{1}"').format(
                    dev, origdev))

        st = x_lstat(dev, True)
        m = None
        if not st:
            m = _(
                "cannot get state of '{0}' ('{1}'), does it exist?"
                ).format(dev, origdev)
        elif not stat.S_ISDIR(st.st_mode):
            m = _(
                "Source selection of '{0}' ('{1}') "
                "is not a mount point directory."
                ).format(dev, origdev)

        if m:
            msg_line_ERROR(m)
            stmsg.put_status(m)
            self.dialog(m, _T("msg"), wx.OK|wx.ICON_ERROR)
            return False

        devname = os.path.split(origdev)[1]
        stmsg.put_status(_T(""))

        to_dev = self.get_is_dev_tmp_target()
        try:
            if to_dev:
                st = x_lstat(target_dev, True, False)
                rdev = raw_node_path(self.checked_input_devnode)
                ist = x_lstat(rdev, True, False)
                if st and ist and os.path.samestat(st, ist):
                    outf = target_dev
                else:
                    outf = self.check_target_dev(target_dev)
                if outf:
                    target_dev = outf
                    outf = self.get_tempdir()
            else:
                outf = self.get_outfile(target_dev)
                self.target.set_target_text(outf)
            if outf == False:
                return False
        except:
            return False

        msg_line_INFO(_('using target directory "{0}"').format(outf))

        self.cur_out_file = outf
        self.cur_task_items[_T("taskname")] = _T('cprec')
        self.cur_task_items[_T("taskfile")] = outf
        self.cur_task_items[_T("taskdirect")] = False

        xcmd = self.get_cmd_path(_T('cprec'))
        xcmdargs = []
        xcmdargs.append(_T("%s-%s") % (xcmd, devname))

        optl = (_T("block-read-count"), _T("retry-block-count"),
                _T("libdvdr"),
                _T("ignore-specials"), _T("ignore-hardlinks"),
                _T("ignore-symlinks"), _T("ignore-existing"))
        cf = self.get_config()
        opth = cf.GetPath()
        cf.SetPath(_T("/main/settings/advanced"))

        for opt in optl:
            if not cf.HasEntry(opt):
                continue
            if (s_eq(opt, "block-read-count") or
                s_eq(opt, "retry-block-count")):
                s = _T("--{opt}={val}").format(
                    opt = opt, val = cf.ReadInt(opt))
            elif s_eq(opt, "libdvdr"):
                s = _T("--{opt}={val}").format(
                    opt = opt, val = cf.Read(opt).strip())
            else:
                v = bool(cf.ReadInt(opt))
                if not v:
                    continue
                s = _T("--{opt}").format(opt = opt)

            xcmdargs.append(s)

        cf.SetPath(opth)

        xcmdargs.append(_T("-vvpfd0"))
        xcmdargs.append(_T("-n"))
        xcmdargs.append(dev)

        xlst = self.source.get_all_addl_items()
        for i in xlst:
            xcmdargs.append(i)

        xcmdargs.append(dev)
        xcmdargs.append(outf)
        xcmdenv = [
            (_T('CPREC_LINEBUF'), _T('true')), (_T('DDD_LINEBUF'), _T('true'))
            ]

        stmsg.put_status(_("Running {0} for {1}").format(xcmd, origdev))

        parm_obj = ChildProcParams(xcmd, xcmdargs, xcmdenv)
        ch_proc = ChildTwoStreamReader(parm_obj, self)

        if to_dev:
            """Set data so that writer may be run if this succeeds
            """
            dat = {}
            dat[_T("target_dev")] = target_dev
            dat[_T("source_file")] = outf
            dat[_T("source_type")] = _T("hier")
            dat[_T("in_burn")] = False
            dat[_T("vol_info")] = self.vol_wnd.get_fields()
            ch_proc.set_extra_data(dat)

        self.child_go(ch_proc)
        return True


    def do_dd_dvd_run(self, target_dev, dev = None):
        stmsg = self.get_stat_wnd()
        self.cur_task_items = {}

        if not dev and self.source and self.source.dev:
            dev = self.source.dev

        if not dev:
            m = _("Select a source device node or mount point")
            msg_line_ERROR(m)
            stmsg.put_status(m)
            self.dialog(m, _T("msg"), wx.OK|wx.ICON_EXCLAMATION)
            return False

        origdev = dev
        realdev = os.path.realpath(dev)
        if realdev and s_ne(realdev, dev):
            dev = realdev
            msg_line_INFO(_(
                'using source node "{0}" for "{1}"').format(
                    dev, origdev))

        st = x_lstat(dev, True)
        m = None
        if not st:
            m = _(
                "cannot get state of '{0}', does it exist?"
                ).format(dev)
        elif not (stat.S_ISDIR(st.st_mode) or
                stat.S_ISBLK(st.st_mode) or
                stat.S_ISCHR(st.st_mode)):
            m = _(
                "Source selection '{0}' "
                "is not a mount point directory, or a device node."
                ).format(dev)

        if m:
            msg_line_ERROR(m)
            stmsg.put_status(m)
            self.dialog(m, _T("msg"), wx.OK|wx.ICON_ERROR)
            return False

        devname = os.path.split(origdev)[1]
        stmsg.put_status(_T(""))

        to_dev = self.get_is_dev_tmp_target()
        is_direct = self.get_is_dev_direct_target()

        ofd = -1
        is_gr = True

        try:
            if to_dev:
                st = x_lstat(target_dev, True, False)
                rdev = raw_node_path(self.checked_input_devnode)
                ist = x_lstat(rdev, True, False)
                if st and ist and os.path.samestat(st, ist):
                    _dbg(_T("NO check_target_dev"))
                    outf = target_dev
                else:
                    _dbg(_T("YES check_target_dev"))
                    outf = self.check_target_dev(target_dev)
                if outf:
                    target_dev = outf
                    ofd, outf = self.get_tempfile()
            elif is_direct:
                outdev = self.check_target_dev(target_dev)
                if not outdev:
                    return False
                outf = self.get_outfile(target_dev)
            else:
                ofd, outf = self.get_outfile(target_dev)
                self.target.set_target_text(outf)
                is_gr = False
            if outf == False:
                return False
        except:
            return False

        if not is_direct:
            msg_line_INFO(_(
                'using target fs image file "{0}"').format(outf))
        else:
            msg_line_INFO(_(
                'target simultaneous ({0})').format(outf))

        self.cur_out_file = outf
        self.cur_task_items[_T("taskname")] = _T('dd-dvd')
        self.cur_task_items[_T("taskfile")] = outf

        xcmd = self.get_cmd_path(_T('dd-dvd'))
        xcmdargs = []
        xcmdargs.append(_T("%s-%s") % (xcmd, devname))

        optl = (_T("block-read-count"),
                _T("retry-block-count"), _T("libdvdr"))
        cf = self.get_config()
        opth = cf.GetPath()
        cf.SetPath(_T("/main/settings/advanced"))

        for opt in optl:
            if not cf.HasEntry(opt):
                continue
            if (s_eq(opt, "block-read-count") or
                s_eq(opt, "retry-block-count")):
                s = _T("--{opt}={val}").format(
                    opt = opt, val = cf.ReadInt(opt))
            elif s_eq(opt, "libdvdr"):
                s = _T("--{opt}={val}").format(
                    opt = opt, val = cf.Read(opt).strip())
            else:
                continue

            xcmdargs.append(s)

        cf.SetPath(opth)

        xcmdargs.append(_T("-vv"))
        xcmdargs.append(dev)
        if not is_direct:
            xcmdargs.append(outf)
        xcmdenv = [
            (_T('CPREC_LINEBUF'), _T('true')), (_T('DDD_LINEBUF'), _T('true'))
            ]

        stmsg.put_status(_(_T("Running {0} for {1}")).format(xcmd, dev))

        if not is_direct:
            self.cur_task_items[_T("taskdirect")] = False
            parm_obj = ChildProcParams(xcmd, xcmdargs, xcmdenv)
        else:
            self.cur_out_file = None
            self.cur_task_items[_T("taskname")] = _T('growisofs-direct')
            self.cur_task_items[_T("taskfile")] = None
            self.cur_task_items[_T("taskdirect")] = True

            inp_obj = ChildProcParams(xcmd, xcmdargs, xcmdenv)

            ycmd = self.get_cmd_path(_T('growisofs'))
            ycmdargs = []
            ycmdargs.append(ycmd)

            spd = self.get_burn_speed(ycmd)
            if spd == False:
                #self.do_cancel()
                return False
            if spd:
                ycmdargs.append(_T("-speed=%s") % spd)

            ycmdargs.append(_T("-dvd-video"))
            ycmdargs.append(_T("-dvd-compat"))

            ycmdargs.append(_T("-Z"))
            ycmdargs.append(_T("%s=%s") % (outdev, outf))

            stmsg.put_status(_(
                #TRANSLATORS: {cmd} is child program name,
                # {dev} is device node, {file} is input file:
                # the form {dev}={fil} represents the way these
                # parameters are set in a growisofs command line.
                "Running {cmd} for {dev}={fil}"
                ).format(cmd = ycmd, dev = outdev, fil = outf))
            parm_obj = ChildProcParams(ycmd, ycmdargs, xcmdenv, inp_obj)

        ch_proc = ChildTwoStreamReader(parm_obj, self)

        if is_gr:
            #ch_proc.set_growisofs()
            pass

        if to_dev:
            """Set data so that writer may be run if this succeeds
            """
            dat = {}
            dat[_T("target_dev")] = target_dev
            dat[_T("source_file")] = outf
            dat[_T("source_type")] = _T("whole")
            dat[_T("in_burn")] = False
            ch_proc.set_extra_data(dat)

        self.child_go(ch_proc)

        if ofd > -1:
            os.close(ofd)

        return True


    def child_go(self, ch_proc, is_check_op = False, cb = None):
        fpid, rfd = ch_proc.go()

        if not ch_proc.go_return_ok(fpid, rfd):
            if ((isinstance(rfd, str) or isinstance(rfd, unicode))
                 and isinstance(fpid, int)):
                ei = fpid
                es = rfd
                m = _(
                    "cannot execute child because '{0}' ({1})"
                    ).format(es, ei)
            else:
                m = _("ERROR: child process failure")

            msg_line_ERROR(m)
            self.dialog(m, _T("msg"), wx.OK|wx.ICON_EXCLAMATION)
            return

        if cb == None:
            cb = self.read_child_in_thread

        try:
            thr = AChildThread(
                self.topwnd, self.topwnd_id, cb,
                (fpid, rfd, ch_proc))
            thr.start()
            self.ch_thread = thr
            self.in_check_op = is_check_op
        except:
            # USR1 is handle specially in child obj class
            ch_proc.kill_wait(signal.SIGUSR1, 3)
            msg_line_ERROR(_("ERROR: could not make or run thread"))


    def do_blank(self, dev, blank_async = False):
        stmsg = self.get_stat_wnd()
        outdev  = os.path.realpath(dev)

        msg_line_INFO(_(
            'blanking disc in "{0}" ({1})').format(dev, outdev))

        xcmd = self.get_cmd_path(_T('dvd+rw-format'))
        xcmdargs = []
        xcmdargs.append(xcmd)

        xcmdargs.append(_T("-blank"))
        xcmdargs.append(outdev)

        stmsg.put_status(_("Running {0} for {1}").format(xcmd, outdev))

        parm_obj = ChildProcParams(xcmd, xcmdargs)
        ch_proc = ChildTwoStreamReader(parm_obj, self)

        if blank_async:
            self.cur_task_items = {}
            self.cur_task_items[_T("taskname")] = _T('blanking')
            self.child_go(ch_proc)
            return True

        is_ok = ch_proc.go_and_read()

        if not is_ok:
            m = _(
                "Failed media blank of {0} with {1}").format(
                    outdev, xcmd)
            msg_line_ERROR(m)
            stmsg.put_status(m)
            return False
        else:
            stmsg.put_status(_("Waiting for {0}").format(xcmd))

        ch_proc.wait()
        is_ok, is_sig = ch_proc.get_status()
        rlin1, rlin2, rlinx = ch_proc.get_read_lists()

        m = _T("")
        for l in rlinx:
            ok, l, dat = self.get_stat_data_line(l, ch_proc)
            if ok:
                m = _T("{pre}\n{lin}").format(pre = m, lin = l)
                is_ok = max(is_ok, dat[1])

        if is_ok == 0:
            msg_INFO(m)
            m = _("{0} succeeded blanking {1}").format(xcmd, outdev)
            msg_line_GOOD(m)
            stmsg.put_status(m)
        else:
            msg_ERROR(m)
            m = _(
                "Failed media blank of {0} with {1} - status {2}"
                ).format(outdev, xcmd, is_ok)
            msg_line_ERROR(m)
            stmsg.put_status(m)
            return False

        return True


    def do_target_medium_check(self, target_dev, retry_num = 0):
        stmsg = self.get_stat_wnd()
        self.target_data = None

        if self.working():
            stmsg.put_status(_("Already busy!"))
            return False

        if retry_num:
            pr_stat = lambda s: True
            pr_GOOD = msg_line_GOOD
            pr_INFO = lambda s: True
            pr_WARN = lambda s: True
            pr_ERR  = lambda s: True
            ms_GOOD = msg_GOOD
            ms_INFO = lambda s: True
            ms_WARN = lambda s: True
            ms_ERR  = lambda s: True
        else:
            pr_stat = stmsg.put_status
            pr_GOOD = msg_line_GOOD
            pr_INFO = msg_line_INFO
            pr_WARN = msg_line_WARN
            pr_ERR  = msg_line_ERROR
            ms_GOOD = msg_GOOD
            ms_INFO = msg_INFO
            ms_WARN = msg_WARN
            ms_ERR  = msg_ERROR

        xcmd = self.get_cmd_path(_T('dvd+rw-mediainfo'))
        xcmdargs = []
        xcmdargs.append(xcmd)
        xcmdargs.append(target_dev)
        xcmdenv = []

        m = _("Checking {0} with {1}").format(target_dev, xcmd)
        pr_WARN(m)
        pr_stat(m)

        parm_obj = ChildProcParams(xcmd, xcmdargs, xcmdenv)
        ch_proc = ChildTwoStreamReader(parm_obj, self)

        is_ok = ch_proc.go_and_read()

        if not is_ok:
            m = _(
                "Failed media check of {0} with {1}"
                ).format(target_dev, xcmd)
            pr_ERR(m)
            pr_stat(m)
            return False
        else:
            pr_stat(_("Waiting for {0}").format(xcmd))

        ch_proc.wait()
        is_ok, is_sig = ch_proc.get_status()
        rlin1, rlin2, rlinx = ch_proc.get_read_lists()

        m = _T("")
        for l in rlinx:
            ok, l, dat = self.get_stat_data_line(l, ch_proc)
            if ok:
                m = _T("{pre}\n{lin}").format(pre = m, lin = l)
                is_ok = max(is_ok, dat[1])

        if is_ok:
            ms_ERR(m)
            m = _(
                "{0} failed status {1} for {2}"
                ).format(xcmd, is_ok, target_dev)
            pr_ERR(m)
            is_ok = False
        else:
            ms_INFO(m)
            m = _("{0} succeeded for {1}").format(xcmd, target_dev)
            pr_INFO(m)
            is_ok = True

        pr_stat(m)

        l1, l2, lx = ch_proc.get_read_lists()
        self.target_data = MediaDrive(target_dev)

        for lin in l2:
            lin = lin.rstrip()
            self.target_data.rx_add(lin)
            pr_WARN(lin)

        e = self.target_data.get_data_item(_T("presence"))
        if e:
            m = _(
                "Failed: {0} says \"{1}\" for {2}"
                ).format(xcmd, e, target_dev)
            pr_ERR(m)
            pr_stat(m)
            self.target_data = None
            return False

        for lin in l1:
            lin = lin.rstrip()
            self.target_data.rx_add(lin)
            if is_ok:
                pr_GOOD(lin)
            else:
                pr_ERR(lin)

        if not is_ok:
            self.target_data = None
        else:
            self.checked_media_blocks = self.target_data.get_data_item(
                _T("medium freespace"))
            pr_INFO(_("Medium free blocks: {0}").format(
                self.checked_media_blocks))
            self.checked_output_devnode = os.path.realpath(target_dev)
            st = x_lstat(self.checked_output_devnode)
            self.checked_output_devstat = st

        return is_ok

    def do_mkiso_blocks(self, srcdir = None, verbose = True):
        stmsg = self.get_stat_wnd()

        if not srcdir:
            srcdir = self.cur_tempfile

        if not srcdir:
            if verbose:
                msg_line_WARN(_("No directory for iso blocks check"))
            return False

        st = x_lstat(srcdir, True, False)
        if not st:
            if verbose:
                msg_line_ERROR(_("stat({d}) failed").format(d = srcdir))
            return False

        if not stat.S_ISDIR(st.st_mode):
            if verbose:
                msg_line_ERROR(_(
                    "{d} is not a directory").format(d = srcdir))
            return False


        xcmd = self.get_cmd_path(_T('mkisofs'))
        xcmdargs = []
        xcmdargs.append(xcmd)

        xcmdargs.append(_T("-dvd-video"))
        xcmdargs.append(_T("-gui"))
        xcmdargs.append(_T("-uid"))
        xcmdargs.append(_T("0"))
        xcmdargs.append(_T("-gid"))
        xcmdargs.append(_T("0"))
        xcmdargs.append(_T("-D"))
        xcmdargs.append(_T("-R"))

        xcmdargs.append(_T("-print-size"))
        xcmdargs.append(_T("-quiet"))

        xcmdargs.append(srcdir)

        m = _("Running {0} for {1}").format(xcmd, srcdir)
        stmsg.put_status(m)
        if verbose:
            msg_line_INFO(m)

        parm_obj = ChildProcParams(xcmd, xcmdargs)
        ch_proc = ChildTwoStreamReader(parm_obj, self)

        is_ok = ch_proc.go_and_read()

        if not is_ok:
            m = _(
                "Failed iso blocks check of {0} with {1}"
                ).format(srcdir, xcmd)
            if verbose:
                msg_line_ERROR(m)
            stmsg.put_status(m)
            return False
        else:
            stmsg.put_status(_("Waiting for {0}").format(xcmd))

        ch_proc.wait()
        is_ok, is_sig, sstr = ch_proc.get_status_string(False)
        rlin1, rlin2, rlinx = ch_proc.get_read_lists()

        ms = _T("")
        for l in rlinx:
            ok, l, dat = self.get_stat_data_line(l, ch_proc)
            if ok:
                sstr = dat[3]
                ms = _T("{pre}\n{lin}").format(pre = m, lin = l)
                is_ok = max(is_ok, dat[1])

        m = _(
            "{process} has {stat} for {testdir}"
            ).format(process = xcmd, stat = sstr, testdir = srcdir)

        if is_ok:
            msg_ERROR(ms)
            if verbose:
                msg_line_ERROR(m)
            is_ok = False
        else:
            msg_INFO(ms)
            if verbose:
                msg_line_INFO(m)
            is_ok = True

        stmsg.put_status(m)

        if verbose:
            for lin in rlin2:
                lin = lin.rstrip()
                msg_line_WARN(lin)

        blks = 0
        rx = re.compile('^\s*([0-9]+)\s*$')

        for lin in rlin1:
            m = rx.match(lin)
            if m:
                blks = int(m.group(1))
                break

        if not blks:
            m = _(
                "{process} found no size for {fsdir} fs!"
                ).format(process = xcmd, fsdir = srcdir)
            if verbose:
                msg_line_ERROR(m)
            stmsg.put_status(m)
            return False
        else:
            m = _(
                "{process} found {sz} blocks needed for {fsdir} fs!"
                ).format(process = xcmd, sz = blks, fsdir = srcdir)
            if verbose:
                msg_line_INFO(m)
            stmsg.put_status(m)

        got = self.checked_media_blocks
        if blks > got:
            m = _(
                "need {blk} blocks for fs, only {got} free on medium!"
                ).format(blk = blks, got = got)
            if verbose:
                msg_line_ERROR(m)
            stmsg.put_status(m)
            return False

        return True


    def do_dd_dvd_check(self, dev = None):
        stmsg = self.get_stat_wnd()

        if self.working():
            stmsg.put_status(_("Already busy!"))
            return False

        if not dev and self.source and self.source.dev:
            dev = self.source.dev

        if not dev:
            m = _("Select a device node or mount point")
            msg_line_ERROR(m)
            stmsg.put_status(m)
            self.dialog(m, _T("msg"), wx.OK|wx.ICON_EXCLAMATION)
            self.checked_input_arg = _T('')
            return False

        self.checked_input_arg = origdev = dev
        realdev = os.path.realpath(dev)
        if realdev and s_ne(realdev, dev):
            dev = realdev
            msg_line_INFO(_(
                'using source node "{0}" for "{1}"'
                ).format(dev, origdev))

        st = x_lstat(dev, True)
        m = None
        if not st:
            m = _(
                "cannot get state of '{0}', does it exist?"
                ).format(dev)
        elif not (stat.S_ISDIR(st.st_mode) or
                stat.S_ISBLK(st.st_mode) or
                stat.S_ISCHR(st.st_mode)):
            m = _(
                "Source selection '{0}' "
                "is not a mount point directory, or a device node."
                ).format(dev)

        if m:
            msg_line_ERROR(m)
            stmsg.put_status(m)
            self.dialog(m, _T("msg"), wx.OK|wx.ICON_ERROR)
            return False

        devname = os.path.split(origdev)[1]

        xcmd = self.get_cmd_path(_T('dd-dvd'))
        xcmdargs = []
        xcmdargs.append(_T("%s-%s") % (xcmd, devname))

        optl = (_T("block-read-count"),
            _T("retry-block-count"), _T("libdvdr"))
        cf = self.get_config()
        opth = cf.GetPath()
        cf.SetPath(_T("/main/settings/advanced"))

        for opt in optl:
            if not cf.HasEntry(opt):
                continue
            if (s_eq(opt, "block-read-count") or
                s_eq(opt, "retry-block-count")):
                s = _T("--{opt}={val}").format(
                    opt = opt, val = cf.ReadInt(opt))
            elif s_eq(opt, "libdvdr"):
                s = _T("--{opt}={val}").format(
                    opt = opt, val = cf.Read(opt).strip())
            else:
                continue

            xcmdargs.append(s)

        cf.SetPath(opth)

        xcmdargs.append(_T("-vvn"))
        xcmdargs.append(dev)

        xcmdenv = []
        xcmdenv.append( (_T('CPREC_LINEBUF'), _T('true')) )
        xcmdenv.append( (_T('DDD_LINEBUF'), _T('true')) )

        stmsg.put_status(_("Checking {0} with {1}").format(dev, xcmd))

        parm_obj = ChildProcParams(xcmd, xcmdargs, xcmdenv)
        ch_proc = ChildTwoStreamReader(parm_obj, self)

        self.child_go(ch_proc, True, self.read_child_in_thread)
        return True

    # child thread callback -- don't invoke directly
    def read_child_in_thread(self, pid_fd_tuple):
        fpid, rfd, ch_proc = pid_fd_tuple

        r = ch_proc.read_curchild(rfd, self.cb_go_and_read)
        if r:
            ch_proc.wait()
            return 0
        else:
            ch_proc.kill_wait()

        return 1

    def read_check_inp_op_result(self, ch_proc):
        # to use message object methods
        msgo = self.get_msg_wnd()

        dev  = self.source.dev
        nod  = dev
        xcmd = ch_proc.xcmd

        # lines with these tokens in rlin2 (below)
        # are excluded from output
        excl = (
            _T('DVDVersion'), _T('output <standard output>'),
            _T('total bad blocks'), _T('device name instead')
        )

        msg_line_INFO(_("\nChecked device '{0}':\n").format(dev))

        stat, sig = ch_proc.get_status()

        if stat > -1:
            # print what is available even if stat > 0
            rlin1, rlin2, rlinx = ch_proc.get_read_lists()
            for l in rlin2:
                cont = False
                for tok in excl:
                    if tok in l:
                        cont = True
                        break

                if cont:
                    continue

                self.mono_message(
                    prefunc = lambda : msg_INFO(_("VIDEO data, ops:")),
                    monofunc = lambda : msg_(_T(" %s") % l))

            voldict = {}

            self.checked_input_mountpt = _T('')

            for l in rlin1:
                lbl, sep, val = l.partition(_T('|'))

                if val:
                    val = val.rstrip(_T(' \n\r\t'))

                m = val
                if s_eq(lbl, 'input_arg'):
                    mnt, sep, nod = val.partition(_T('|'))
                    lbl = _('device node')
                    self.checked_input_arg = dev
                    if dev == nod:
                        m = _("{0}: {1}").format(lbl, nod)
                    else:
                        if dev == mnt:
                            m = _(
                                "{0}: {1} is {2}"
                                ).format(lbl, dev, nod)
                        else:
                            m = _(
                                "{0}: {1} ({2}) is {3}"
                                ).format(lbl, mnt, dev, nod)
                        self.checked_input_mountpt = mnt
                else:
                    voldict[lbl] = val
                    if s_eq(lbl, 'filesystem_block_count'):
                        self.checked_input_blocks = int(val.strip())

                    if s_eq(m, ""):
                        m = _("[field is not set]")

                    m = _T("{0}: {1}").format(lbl, m)

                self.mono_message(
                    prefunc = lambda : msg_GOOD(_("DVD volume info:")),
                    monofunc = lambda : msg_(_T(" ") + m + _T("\n")))

            # give volume info pane new data
            self.vol_wnd.set_source_info(voldict)

            for l in rlinx:
                ok, l, dat = self.get_stat_data_line(l, ch_proc)
                if ok:
                    if dat[1]:
                        msg_ERROR(l)
                    else:
                        msg_INFO(l)
                else:
                    msg_WARN(_("AUXILIARY OUTPUT: '{0}'").format(l))

            if stat == 0:
                self.checked_input_devnode = nod
                st = x_lstat(self.checked_input_devnode)
                self.checked_input_devstat = st

        elif stat >= 60:
            msg_line_ERROR(_(
                "!!! execution of '{0}' FAILED").format(xcmd))
        else:
            msg_line_ERROR(_(
                "!!! check of '{0}' FAILED code {1}").format(
                    dev, stat))


class TheAppClass(wx.App):
    def __init__(self, dummy):
        wx.App.__init__(self)

    def OnExit(self):
        config = self.get_config()
        if config:
            config.Flush()

        return 0

    def OnInit(self):
        config = self.get_config()
        config.SetPath(_T('/main'))

        self.core_ld = ACoreLogiDat(self)

        # pos is repeated later in frame's conf_rd() -- w/o
        # both, vertical position is off.
        if config.HasEntry(_T("x")) and config.HasEntry(_T("y")):
            pos = wx.Point(
                x = max(config.ReadInt(_T("x"), 0), 0),
                y = max(config.ReadInt(_T("y"), 0), 0)
            )
        else:
            pos = wx.DefaultPosition

        w = config.ReadInt(_T("w"), -1)
        h = config.ReadInt(_T("h"), -1)
        if w < 100 or h < 100:
            w = 800
            h = 600

        self.frame = AFrame(
            None, self.core_ld.get_new_idval(), PROG, self.core_ld,
            pos, wx.Size(800, 600))
        self.SetTopWindow(self.frame)

        self.frame.SetSize((w, h))

        if pos == wx.DefaultPosition:
            self.frame.Centre(wx.BOTH)

        i = config.ReadInt(_T("iconized") , 0)
        if i:
            self.frame.Iconize(True)
        m = config.ReadInt(_T("maximized"), 0)
        if m:
            self.frame.Maximize(True)

        self.frame.Show(True)

        self.core_ld.set_gauge_wnd(self.frame)
        self.core_ld.set_ready_topwnd(self.frame)

        return True

    def get_config(self):
        try:
            return self.config
        except:
            try:
                tr = PROG.rindex(_T(".py"))
            except:
                tr = len(PROG)

            # Phoenix: wx.CONFIG_USE_LOCAL_FILE is missing, although
            # mentioned in core classes Config docs.  Since this
            # program is Unix/POSIX only it is equivalent to use
            # wx.FileConfig, but if we could run under MSW, this would
            # be wrong
            if phoenix:
                self.config = wx.FileConfig(
                    PROG[:tr],
                    _T("GPLFreeSoftwareApplications"))
            else:
                cfsty = wx.CONFIG_USE_LOCAL_FILE
                cfsty |= wx.CONFIG_USE_GLOBAL_FILE
                self.config = wx.Config(
                    PROG[:tr],
                    _T("GPLFreeSoftwareApplications"),
                    style = cfsty)
        return self.config

    def get_msg_obj(self):
        return self.GetTopWindow().get_msg_obj()


def __main():
    app = TheAppClass(0)
    app.MainLoop()

# __main() called as below, but at end, after all large data decls.
#if __name__ == '__main__':
#    __main()

# The program licence, encoded as:
# CHUNK = 64
# buf = base64.b64encode(zlib.compress(f_in.read(), 9))
# while buf:
#   f_out.write(buf[:CHUNK] + "\n")
#   buf = buf[CHUNK:]
_licence_data = """
eNqdXFtz4zayfg7q/AiUX8au4ijx5OwlcSpVsi2PtWvLjiTPxG9LSZDFHYrUEqQ9
+venv24ABHWZ5GxqsxObZKPR6MvXF8x332n65+PoSX8cjAbj/p1+fLq8G15p+ncw
mgzUd/wC/fPJVDYrC/0h0f9oCqPPf/rpXCl9VW62VfayqvXp1Rn98u8/JfxI31TG
6Em5rN/SyuibsikWaU0EEj0s5j3FNP/yk56a9SY3+jFP5ybRkyarjf7xxx8SfVna
Gm/f97X+4cP5+fn78x9/+JvWT5O+0oNXU21L4iKzemOqdVbXZqHrUs+JHZ0WC73I
bF1ls4bI0bszWnqNh5mxSpdLXa/oyzybm8IavSjnzdoUdaLpfT1fpcVLVrzorAb5
oqx1muflm1n0FImD5fFYmXQ9yw0JQE9XxlOyellWek2ca+t3jn8XxmYvhXBYp1/o
l2/pVm/LplJLEtOiXOOJXfH7xDyzQJure1pfbonvoq5SS/zVtBYflilMleb6sZnR
0urObYTYzYraFAtZ6qVJq5R+NryU/tZSeKY8z+/f0ytr8Gkbeg2Lhu3QEniXN0pi
IR6tbizpRg+SyKzqsqY9a+lmk5PwsTjLh8/AdLVEtVryzkYSLHg3abHVJX1T6U1V
vlTpWr+tSlBu6lVZWZLSmvSA3lSNleMjlk4n5dq4z45pZGdz85LUhcQ32yov7Lts
VqXVVh/ZWVbY2qSL3pnWz2Wj52nBm91qYYZF7zi2dIJl2YPWfF6ZQr+RYDcm/QJp
sFQ9JwkegaPKLE1VYTskAXeACXRSbSpan3b4QOQPc2b3dC8+07SGVqhV+ionHGlH
ZDtiMnv86VOnO9ULq4JieyI1eKWldbYEaf2W2dVZEpaivcxN9goiTTUH6QWdTMUC
ezFka7XyH5LS0o/Rp3jHaWpHG+lzUj5NPM6FSxApdGHehF8v9wtRIk/uS1G+BbqL
EjQtKJOcLZ/OtMSntZnXYjrs4SyfSmEiWVYGkppDi6yQJ2HMsoUiZYV7gjBNwabu
FhFKYBwqbb/IoxKnUsFwK96gvNVTU/mmswqZtM3TmonPTVWntGF6Y0MPs1mWZ3Xm
/BAoi0TVwRONJZmAIyf+dbnIllBfFsUNPTBfU3jpxL9xkJxt5iudepGTrFYGZqfo
pzrjHbPP0EtDhHidhvzAS+b0j7QjI1IFCQd+pZUCyxVmpKGrPbEy/nZHnemTLRtY
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
DvxdF+rw33WxX9r8P3d/dKk=
"""

#----------------------------------------------------------------------
wxdvdbackup_16 = PyEmbeddedImage(
"""
iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlw
SFlzAAAG7AAABuwBHnU4NQAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoA
AALXSURBVDiNnZJPTNNQAMbfe33703YrbFMYjAlEhhgdJhpREDUmLkr8l5gYUTQc1IMJHkSj
xhsao0avCAcNkqCJntSDCirRKImigAQkKMJgm7OTdQy6vrbb2nrSxKN85+/7Xb4fvHzjHG8r
/knAIkIieTRmvbFEyYFXjsUAwk82JzGkdBkAABcDgJQuY4h00tryrkKROYyQZixxT5CGpkPf
ENKMN0+b3UN9hwvqTzaOu4u+yPdb7/kKi4el6u1t/IP2u+WqkGMgknZkSMqJj5+ve3fk1MH3
fMjPfh3eCcWkmwz1NeQBALXxz7vMAIDkr+gKGmNFvH3teQU2EbKjpuUTno5ttCOkZXsfXfTE
Y8tzWfus6PO/nHnY1rHelTcVh9AAs7wPJ4VlqipzuP/1sZJy/4uZ3Q1nR6I9G8woIZbSFqso
KbJdU2UOma1EGu3fz0RDlUvWbekcpLCSmo97LV8G9tgQ0rIAGNmaQOsnAEASIEOkvNUXzrg8
kz/rTzZ2x3kfFQ1VeiNT6/N03YwnRgKlC3OenEyaNSGki4jKqlwuLwz2HV25trZrgITyDVjb
LMQsNlEyWyQyP1dYQNsSiazKME2XNrVirOh82M913Hx82rk0OGV38MKBE8e726/0Hst1hvlA
5fXXcN+lj70Mk9aqpk3UVjTxI/y9anWppKpeSdNMSTtnIEMfozmHxMmS3R2czikdDU3mZ7Qu
y6qidWWdH2FkzUhP4VhFLcxg+s+/uikjpyomP8S39Q1QhDYzwWUFrrdVdShtZv92LOlUsObD
M4zTJgXo8B+RDKxJav7sV4owKZilEMxgFhhQ/8ciHQKTYlXgrd69gTKvkC6/2uSnfxQsNQu5
Trxgc1ES66JkqxNAQ9cYWciyJJHlRCHtmhNISeTXeMvN0fC3IiuGwEhIZUEydOfMq/92ecLD
YIAMAQCg/vcYAACRLuPMPBuP969azB4osw7xN+nST7zu6AufAAAAAElFTkSuQmCC
"""
)
getwxdvdbackup_16Data = wxdvdbackup_16.GetData
getwxdvdbackup_16Image = wxdvdbackup_16.GetImage
getwxdvdbackup_16Bitmap = wxdvdbackup_16.GetBitmap
getwxdvdbackup_16Icon = wxdvdbackup_16.GetIcon

#----------------------------------------------------------------------
wxdvdbackup_24 = PyEmbeddedImage(
"""
iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAABHNCSVQICAgIfAhkiAAAAAlw
SFlzAAAKYQAACmEB/MxKJQAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoA
AASKSURBVEiJvZVrbBRVFMfPnbkzu/PYbrvPPpc+QFKaRmhKiwTBqICCiQgoxqBC6of64PFB
YqIkBuMHE6MJ+IDEhGBSSVALi0GhbQKCBYOglEBopbTsbrfdbndnO7uzM7s7Tz+YJhjaCGo9
327O/5zfubn3nIP2vP/OOEFrNMyCmSqlYYQNunFXBzEbgOsfv2BhgjQKAGACAPqvAQRp6BiR
Zh4A9Bk0/wqKSNOcAqj3G3tvAANhhI0cABTuJ/CeqyBNEiPCzFsAub/T/kMAxog0lZGhFtzf
t8Y/5WBYUfOUDmYDcy9mOEdSAwDIy8X43KkdcxAgVD6nL93QHEwCANy8tsoVurm0pKr2sli/
6IRgmhj93NNeKWc9tJWy5TGBDfnimbb6/itPzeMcCdnlDaVFIVAkpf18iTc02b770dMYF8zO
g/tbhweWBwAA/BX9iYbmYAQA4EL3a4tGhheXs3zq0lh4IRn8cl+LEK91LWg6Mdjg7RohEGko
0dvNPgCApmVfXX1p58aehubjNwAA1LyDIgg923tyZ9nwwPJAWeBqlCR1IxmvKzEMOmdZSImP
NrgBAGKRRv7QR8GVObmEfmbLtq4Nbe0XaFrJYEn1m5JY6gQA6O3atqT31PYllkUQdjad3dT+
8vFoqIk6d3JHq82ezW14pb2nY++RtaIQ8A3deITFuGCoBdYGADDQt6beVz4Q3bz9+S7OkVAB
AAhsYBwSWtwAAHYmI63bsu1YIc/jsyfeXJFK1FScDr79YEqo9hkGTVXVXf792qX1PpLUVQCA
4f4VbgDLAgAo9kRiiuQpTsbrSvuvrC1uXn4o9OcjGyQeT9eXAwA43dExhpsUxWTArcguDgBA
FKqKM6lyH8OKohCv8wrxWq+u22gAgNHQQp9lkgQAwNwFp/vmNpyJdB7c/2LXN++ty+ccR5et
/mQAYQNQ6/ZcWtPtRVM/CFP5HMtNCsXukVhkqGUxw4qpV99dsY+3ixp/q5oNT9Q7Pzty4A0b
I6VNA2NNZbhN7Vv3PtDYHR+8ttLfefDzNl2zsw89fuDb+dSPv6FPf9j4esWTFyg2XGmv7Fhf
w4yWFtFJF0+JTo4SizhK4nlS4jisMCxYBAEAYJGGYXCKrPOyrBVls7ozI6suMat6UrJcG56M
bP06pDkz+lh3q4a6d3/4VtPZh1exw4FqZBJ3T1XCMuXqkUiuaixR8CcyVMZhpyc8TnvM57HH
fKXTNZhJ6Wq2/tbQT892fo9SNaEeGyDfTN2YeKz3lytf7Do/nW/p6sNP84M1tTPFpl2T19G5
PR9snn9+yVpmtLQMLDTdXrCU6uhIwZsUC14hSxiYoBMu3h7zu+0xX9l0iS3S1JWaSOTXTUeD
qCPc1MwFxiu4W9VMWfCJCtuEh6MnnSyWeAZLPEvKDEMqDIsMEv8lCaWpBpvP6Zys6A45pxdJ
ilqSyeUrxzLR574bVb0pTRn1xtAxq3weANTMdM0psyXcmL0dYExKM5XacF5zSsYM0jsHYxjP
ILrLCl5BL3gF6R6k1p2HWdnF/ysAA0AGAMZmKX/6D1Z7+8SbucfAAAAAAElFTkSuQmCC
"""
)
getwxdvdbackup_24Data = wxdvdbackup_24.GetData
getwxdvdbackup_24Image = wxdvdbackup_24.GetImage
getwxdvdbackup_24Bitmap = wxdvdbackup_24.GetBitmap
getwxdvdbackup_24Icon = wxdvdbackup_24.GetIcon

#----------------------------------------------------------------------
wxdvdbackup_32 = PyEmbeddedImage(
"""
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
"""
)
getwxdvdbackup_32Data = wxdvdbackup_32.GetData
getwxdvdbackup_32Image = wxdvdbackup_32.GetImage
getwxdvdbackup_32Bitmap = wxdvdbackup_32.GetBitmap
getwxdvdbackup_32Icon = wxdvdbackup_32.GetIcon

#----------------------------------------------------------------------
wxdvdbackup_48 = PyEmbeddedImage(
"""
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
"""
)
getwxdvdbackup_48Data = wxdvdbackup_48.GetData
getwxdvdbackup_48Image = wxdvdbackup_48.GetImage
getwxdvdbackup_48Bitmap = wxdvdbackup_48.GetBitmap
getwxdvdbackup_48Icon = wxdvdbackup_48.GetIcon

#----------------------------------------------------------------------
wxdvdbackup_64 = PyEmbeddedImage(
"""
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
AABJRU5ErkJggg==
"""
)
getwxdvdbackup_64Data = wxdvdbackup_64.GetData
getwxdvdbackup_64Image = wxdvdbackup_64.GetImage
getwxdvdbackup_64Bitmap = wxdvdbackup_64.GetBitmap
getwxdvdbackup_64Icon = wxdvdbackup_64.GetIcon

if __name__ == '__main__':
    __main()
