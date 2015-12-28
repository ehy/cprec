#! /usr/bin/env python
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
DVD Backup fronted for cprec and dd-dvd
"""

import collections
import errno
eintr = errno.EINTR
import math
import os
import select
import signal
import stat
import string
import sys
import tempfile
import threading
import time
import wx
import wx.lib.mixins.listctrl as listmix
from wx.lib.embeddedimage import PyEmbeddedImage

"""
    Global data
"""

PROG = os.path.split(sys.argv[0])[1]

_fdbg = None
#_fdbg_name = "/tmp/_DBG_dd"
#_fdbg = open(_fdbg_name, "w", 0)

def _dbg(msg):
    if not _fdbg:
        return
    _fdbg.write("%u: %s\n" % (time.time(), msg))

_dbg("debug file opened")

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
    Global procedures
"""

def msg_(msg, clr = wx.BLACK):
    if _msg_obj_init_is_done == True:
        if clr == None:
            _msg_obj.AppendText(msg)
        else:
            _msg_obj.AppendTextColored(msg, clr)
    else:
        sys.stdout.write(msg)

def err_(msg, clr = None):
    if _msg_obj_init_is_done == True:
        if clr == None:
            _msg_obj.AppendTextColored(msg, wx.RED)
        else:
            _msg_obj.AppendTextColored(msg, clr)
    else:
        sys.stderr.write(msg)

def msg_red(msg):
    msg_(msg, wx.RED)

def msg_green(msg):
    msg_(msg, wx.Colour(0, 227, 0))
    #msg_(msg, wx.GREEN)

def msg_blue(msg):
    msg_(msg, wx.BLUE)

def msg_yellow(msg):
    msg_(msg, wx.Colour(227, 227, 0))


def msg_ERROR(msg):
    msg_red(msg)

def msg_WARN(msg):
    msg_yellow(msg)

def msg_GOOD(msg):
    msg_green(msg)

def msg_INFO(msg):
    msg_blue(msg)


def msg_line_(msg, clr = wx.BLACK):
    if _msg_obj_init_is_done == True:
        msg_("\n" + msg, clr)
    else:
        msg_(msg + "\n", clr)

def err_line_(msg, clr = None):
    m = "%s: %s" % (PROG, msg)
    if _msg_obj_init_is_done == True:
        err_("\n" + m, clr)
        sys.stderr.write(m + "\n")
    else:
        err_(m + "\n", clr)

def msg_line_red(msg):
    msg_line_(msg, wx.RED)

def msg_line_green(msg):
    msg_line_(msg, wx.Colour(0, 227, 0))
    #msg_line_(msg, wx.GREEN)

def msg_line_blue(msg):
    msg_line_(msg, wx.BLUE)

def msg_line_yellow(msg):
    msg_line_(msg, wx.Colour(227, 227, 0))


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
    except OSError, (errno, strerror):
        if not quiet:
            msg_line_ERROR(
                "Error: cannot stat '%s': '%s' (errno %d)"
                % (path, strerror, errno))
        return None


"""
    Classes
"""


"""
Parameter holding object to simplify interface to child-proc classes
"""
class ChildProcParams:
    def __init__(
        self, cmd = None, cmdargs = None, cmdenv = None, stdin_fd = None
        ):
        self.xcmd = cmd

        if cmdargs != None:
            self.xcmdargs = cmdargs
        else:
            self.xcmdargs = []

        if cmdenv != None:
            self.xcmdenv = cmdenv
        else:
            self.xcmdenv = []

        self.infd_opened = False
        if isinstance(stdin_fd, str):
            self.infd = os.open(stdin_fd, os.O_RDONLY)
            self.infd_opened = True
        elif isinstance(stdin_fd, int):
            self.infd = stdin_fd
        else:
            self.infd = os.open(os.devnull, os.O_RDONLY)
            self.infd_opened = True

    def __del__(self):
        if self.infd_opened and self.infd > -1:
            os.close(self.infd)

    def close_infd(self):
        if self.infd_opened and self.infd > -1:
            os.close(self.infd)
        self.infd_opened = False
        self.infd = -1


"""
Exec a child process, when both its stdout and stderr are wanted --
    class ChildProcParams for child parameters.
Method go() (see comment there) returns read fd on which child
    stdout lines have prefix "1: " and stderr has "2: " and anything
    else is a message from an auxiliary child (none at present)
Method ForkItRead() (see comment there) invokes go() and reads and
    stores lines of outputs in three arrays which can be retrieved
    with get_read_lists() -- after which reset_read_lists() can be
    called if object is to be used again.
See method comments in class definition
"""
class ChildTwoStreamReader:
    prefix1 = "1: "
    prefix2 = "2: "

    fork_err_status = 69
    exec_err_status = 66
    exec_wtf_status = 67

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

    def __init__(self, child_params = None,
                 gist = None, line_rdsize = 4096):
        # I've read that file.readline(*size*) requires a non-zero
        # *size* arg to reliably return "" *only* on EOF
        # (which is needed)
        self.szlin = line_rdsize

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

        self.extra_data = None
        self.error_tuple = None
        self.prockilled = False
        self.procstat = -1
        self.curchild = -1

        self.rlin1 = []
        self.rlin2 = []
        self.rlinx = []


    def __del__(self):
        """FPO
        """
        pass


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
        _dbg("handler pid %d, child pid %d with signal %d" %
            (os.getpid(), self.curchild, sig))
        if self.curchild > 0:
            # USR1 used by this prog
            if sig == signal.SIGUSR1:
                self.kill(signal.SIGINT)
            else:
                self.kill(sig)
        if sig in self._exit_sigs:
            _dbg("handler:exit pid %d, child pid %d with signal %d" %
                (os.getpid(), self.curchild, sig))
            os._exit(1)

    """
    public: kill (signal) current child
    """
    def kill(self, sig = 0):
        _dbg("kill pid %d with signal %d" % (self.curchild, sig))
        if self.curchild > 0:
            try:
                os.kill(self.curchild, sig)
                return 0
            except:
                _dbg("kill exception pid %d -- signal %d" %
                    (self.curchild, sig))
                return -1

        return -1

    """
    public: wait on current child, mx trys maximum, sleep nsl in loop
    -- note that for non-blocking, call as wait(1, 0) -- see opts
    """
    def wait(self, mx = 1, nsl = 1, fpid = None):
        if fpid == None:
            fpid = self.curchild

        if fpid in (-1, 0):
            return -1

        _dbg("wait pid %d with mx %d" % (fpid, mx))

        opts = 0
        if nsl < 1:
            opts = opts | os.WNOHANG

        while mx > 0:
            mx = mx - 1
            try:
                pid, stat = os.waitpid(fpid, opts)
                if os.WIFSIGNALED(stat):
                    cooked = os.WTERMSIG(stat)
                    if fpid == self.curchild:
                        self.curchild = -1
                        self.prockilled = True
                        self.procstat = cooked
                    _dbg("wait signalled %d with  %d" %
                        (fpid, cooked))
                    return cooked

                if os.WIFEXITED(stat):
                    cooked = os.WEXITSTATUS(stat)
                    if fpid == self.curchild:
                        self.curchild = -1
                        self.prockilled = False
                        self.procstat = cooked
                    _dbg("wait exited %d with  %d" %
                        (fpid, cooked))
                    return cooked

            except OSError, (errno, strerror):
               return -1

            if mx > 0:
                _dbg("wait sleep(%u) pid %d with mx %d"
                    % (nsl, fpid, mx))
                time.sleep(nsl)

        _dbg("wait pid %d FAILURE" % fpid)
        return -1

    """
    public: do kill and wait on current child
    """
    def kill_wait(self, sig = 0, mx = 1, nsl = 1):
        if self.kill(sig) != 0:
            return -1
        return self.wait(mx, nsl)

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
    command may be set after object init
    """
    def set_command(self, cmd, cmdargs, cmdenv = None, l_rdsize = 4096):
        self.params = None

        self.szlin = l_rdsize
        self.xcmd = cmd
        self.xcmdargs = cmdargs
        self.xcmdenv = self.params.xcmdenv


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
        del self.rlin1[:]
        del self.rlin2[:]
        del self.rlinx[:]


    """
    get child status, or -1 if called before child process has been
    run -- if child has been run, this resets internal status to -1
    so that object may be used again; hence this method can be called
    once per child run, or if running async e.g. in new thread then
    other thread may call this to poll until return is not -1
    """
    def get_status(self, reset = False):
        ret = self.procstat
        if reset:
            self.procstat = -1
        return ret


    """
    simple helper for caller of go() below: it returns a 2 tuple
    on success or error: on success both elements are ints -- pid
    and read descriptor -- on error one element will not be and int
    -- presently the only error return is that the tuple will be
    errno, strerror from OSError object, make the second element
    a str (but this may change)
    """
    def go_return_ok(self, fpid, rfd):
        if isinstance(rfd, str):
            return False
        return True

    """
    fork() and return tuple (child_pid, read_fd),
    or on OSError (errno, strerror), or on other error (0, "message")
    -- caller must wait on pid -- this object will know nothing more
    about it
    """
    def go(self):
        if self.xcmd == None:
            self.error_tuple = (0, "Internal: no child command arg")
            return self.error_tuple

        is_path = os.path.split(self.xcmd)
        if len(is_path[0]) > 0:
            is_path = True
        else:
            is_path = False

        try:
            rfd, wfd = os.pipe()
        except OSError, (errno, strerror):
            self.error_tuple = (errno, strerror)
            return self.error_tuple

        fpid = -1

        try:
            self.curchild = fpid = os.fork()
        except OSError, (errno, strerror):
            os.close(rfd)
            os.close(wfd)
            self.curchild = -1
            self.error_tuple = (errno, strerror)
            return self.error_tuple

        if fpid == 0:
            self._child_sigs_setup()

            os.close(rfd)

            exrfd1, exwfd1 = os.pipe()
            exrfd2, exwfd2 = os.pipe()

            try:
                self.curchild = fpid = os.fork()
            except OSError, (errno, strerror):
                os._exit(self.fork_err_status)

            if fpid == 0:
                os.close(exrfd1)
                os.close(exrfd2)
                os.close(wfd)

                # do stdin if param is present
                if self.params != None and self.params.infd > -1:
                    os.dup2(self.params.infd, 0)
                    self.params.close_infd()
                os.dup2(exwfd1, 1)
                os.dup2(exwfd2, 2)
                os.close(exwfd1)
                os.close(exwfd2)

                try:
                    for envtuple in self.xcmdenv:
                        os.environ[envtuple[0]] = envtuple[1]
                    if is_path:
                        os.execv(self.xcmd, self.xcmdargs)
                    else:
                        os.execvp(self.xcmd, self.xcmdargs)
                    os._exit(self.exec_wtf_status)
                except OSError, (errno, strerror):
                    os._exit(self.exec_err_status)

            else:
                os.close(exwfd1)
                os.close(exwfd2)
                # The FILE* equivalents are opened with 0 third arg to
                # disable buffering, to work in concert with poll(),
                # and provide parent timely info
                fr1 = os.fdopen(exrfd1, "r", 0)
                fr2 = os.fdopen(exrfd2, "r", 0)
                fw  = os.fdopen(wfd, "w", 0)

                flist = []
                flist.append(exrfd1)
                flist.append(exrfd2)

                errbits = select.POLLERR|select.POLLHUP|select.POLLNVAL
                pl = select.poll()
                pl.register(flist[0], select.POLLIN|errbits)
                pl.register(flist[1], select.POLLIN|errbits)

                #eintr = errno.EINTR
                global eintr

                while True:
                    try:
                        rl = pl.poll(None)
                    except select.error, (errno, strerror):
                        if errno == eintr:
                            continue
                        else:
                            break

                    if len(rl) == 0:
                        break

                    for fd, bits in rl:
                        lin = ""
                        if fd == exrfd1:
                            if bits & select.POLLIN:
                                tlin = fr1.readline(self.szlin)
                                if len(tlin) > 0:
                                    lin = self.prefix1 + tlin
                                else:
                                    flist.remove (exrfd1)
                                    pl.unregister(exrfd1)
                            else:
                                pl.unregister(exrfd1)
                                flist.remove(exrfd1)
                        elif fd == exrfd2:
                            if bits & select.POLLIN:
                                tlin = fr2.readline(self.szlin)
                                if len(tlin) > 0:
                                    lin = self.prefix2 + tlin
                                else:
                                    flist.remove (exrfd2)
                                    pl.unregister(exrfd2)
                            else:
                                pl.unregister(exrfd2)
                                flist.remove(exrfd2)

                        if len(lin) > 0:
                            fw.write(lin)

                    if len(flist) == 0:
                        break

                fw.close()

                _dbg("In go() before wait")
                stat = self.wait(mx = 25, nsl = 2)
                _dbg("In go() after wait")

                if stat < 0:
                    # bad failure, like pid n.g.
                    os._exit(1)
                else:
                    if self.prockilled == True:
                        # want to provide same status to parent, so
                        # suicide with same signal -- python does not
                        # seem to have {os,signal}.raise() so os.kill()
                        self._child_sigs_defaults()
                        _dbg("In go() do self-signal %d"
                            % self.procstat)
                        os.kill(os.getpid(), self.procstat)
                        signal.pause()
                        # should not reach here!
                        os._exit(1)
                    else:
                        _dbg("In go() do exit %d"  % self.procstat)
                        os._exit(self.procstat)

        else:
            os.close(wfd)
            self.error_tuple = None
            return (fpid, rfd)


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
        return self.read(self.curchild, rfd, cb)

    def read(self, fpid, rfd, cb = None):
        if not self.go_return_ok(fpid, rfd):
            return False

        fr = os.fdopen(rfd, "r", 0)

        flens = (len(self.prefix1), len(self.prefix2))

        if cb == None:
            cb = self.null_cb_go_and_read

        while True:
            lin = fr.readline(self.szlin + 3)

            if len(lin) > 0:
                if lin.find(self.prefix1, 0, flens[0]) == 0:
                    l = lin[flens[0]:]
                    self.rlin1.append(l)
                    self.kill_for_cb_go_and_read(fpid, cb(1, l))
                elif lin.find(self.prefix2, 0, flens[1]) == 0:
                    l = lin[flens[1]:]
                    self.rlin2.append(l)
                    self.kill_for_cb_go_and_read(fpid, cb(2, l))
                else:
                    self.rlinx.append(lin)
                    self.kill_for_cb_go_and_read(fpid, cb(-1, l))
            else:
                break

        return True


"""
AMsgWnd -- a text output window to appear within the ASashWnd
"""
class AMsgWnd(wx.TextCtrl):
    def __init__(self, parent, wi, hi, id = -1):
        wx.TextCtrl.__init__(self,
            parent, id, "", wx.DefaultPosition, (wi, hi),
            wx.TE_MULTILINE | wx.SUNKEN_BORDER | wx.TE_RICH |
            wx.VSCROLL | wx.HSCROLL
            )

        self.parent = parent

        self.scroll_end = False
        self.scroll_end_user_set = False
        self.showpos = 0

        self.default_text_style = self.GetDefaultStyle()
        self.orig_font = self.default_text_style.GetFont()
        self.mono_font = wx.Font(
            self.orig_font.GetPointSize(),
            wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL
        )
        self.get_msg_obj().SetValue("Message window.")
        self.showpos = self.GetLastPosition()

        global _msg_obj
        _msg_obj = self
        global _msg_obj_init_is_done
        _msg_obj_init_is_done = True

        # Scroll top/bottom are not working -- apparently
        # only for scrolled windows and scroll bars --
        # but leave code in place in case this changes,
        # or some workaround presents itself.
        #self.Bind(wx.EVT_SCROLL_TOP, self.on_scroll_top)
        #self.Bind(wx.EVT_SCROLL_BOTTOM, self.on_scroll_bottom)
        self.Bind(wx.EVT_SCROLLWIN_TOP, self.on_scroll_top)
        self.Bind(wx.EVT_SCROLLWIN_BOTTOM, self.on_scroll_bottom)


    #private
    def on_scroll_top(self, event):
        if event.GetOrientation() == wx.HORIZONTAL:
            return
        self.scroll_end = False
        self.scroll_end_user_set = False
        self.showpos = 0
        #sys.stdout.write("Scroll TOP\n")

    def on_scroll_bottom(self, event):
        if event.GetOrientation() == wx.HORIZONTAL:
            return
        self.scroll_end = True
        self.scroll_end_user_set = False
        self.showpos = self.GetLastPosition()
        #sys.stdout.write("Scroll BOTTOM\n")

    # end private
    def set_mono_font(self):
        self.default_text_style.SetFont(self.mono_font)
        self.SetDefaultStyle(self.default_text_style)


    def set_default_font(self):
        self.default_text_style.SetFont(self.orig_font)
        self.SetDefaultStyle(self.default_text_style)


    def conditional_scroll_adjust(self):
        if self.scroll_end == True:
            self.SetInsertionPointEnd()
            self.showpos = self.GetLastPosition()

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
    def __init__(self, parent, gist, id = -1):
        wx.ListCtrl.__init__(self,
            parent, id,
            wx.DefaultPosition, wx.DefaultSize,
            wx.LC_REPORT|wx.LC_HRULES|wx.LC_VRULES)

        self.parent = parent
        self.logger = gist.get_msg_wnd

        li = wx.ListItem()
        li.SetImage(-1)
        li.SetText("Name")
        self.InsertColumnItem(0, li)
        self.SetColumnWidth(0, 192)
        li.SetText("Full Path")
        li.SetAlign(wx.LIST_FORMAT_LEFT)
        self.InsertColumnItem(1, li)
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
                msg_line_WARN("Warning:")
                msg_(" '%s' is a symlink;"
                    " symlinks are recreated, not followed." % p)
                idx = self.add_slink(p, idx) + 1
            elif stat.S_ISDIR(st.st_mode):
                if p == "/":
                    msg_line_ERROR(
                        "Error: '/' is the root directory;"
                        " you must be joking.")
                    continue
                idx = self.add_dir(p, idx) + 1
            elif stat.S_ISCHR(st.st_mode):
                msg_line_WARN("Warning:")
                msg_(" '%s' is a raw device node;"
                    " it will be copied, but do you"
                    " really want it?" % p)
                idx = self.add_spcl(p, idx) + 1
            elif stat.S_ISBLK(st.st_mode):
                msg_line_WARN("Warning:")
                msg_(" '%s' is a block device node;"
                    " it will be copied, but do you"
                    " really want it?" % p)
                idx = self.add_spcl(p, idx) + 1
            elif stat.S_ISFIFO(st.st_mode):
                msg_line_WARN("Warning:")
                msg_(" '%s' is a FIFO pipe;"
                    " it will be copied, but do you"
                    " really want it?" % p)
                idx = self.add_spcl(p, idx) + 1
            elif stat.S_ISSOCK(st.st_mode):
                msg_line_ERROR(
                    "Error: '%s' is a unix domain socket;"
                    " it will not be copied." % p)
                continue
            elif stat.S_ISREG(st.st_mode):
                idx = self.add_file(p, idx) + 1
            else:
                msg_line_WARN("Warning:")
                msg_(" '%s' is an unknown fs object type;"
                    " a copy will be attempted if it is not removed"
                    " from the list" % p)
                idx = self.add_file(p, idx) + 1

        return idx

    def add_dir(self, path, idx = -1):
        if idx < 0:
            idx = self.GetItemCount()
        return self.add_item_color(path, idx, wx.BLUE)

    def add_slink(self, path, idx = -1):
        if idx < 0:
            idx = self.GetItemCount()
        return self.add_item_color(path, idx, wx.Colour(0, 227, 0))

    def add_spcl(self, path, idx = -1):
        if idx < 0:
            idx = self.GetItemCount()
        return self.add_item_color(path, idx, wx.Colour(227, 227, 0))


    def add_multi_dirs(self, paths, idx = -1):
        if idx < 0:
            idx = self.GetItemCount()

        for p in paths:
            idx = self.add_dir(p, idx) + 1

        return idx

    def add_item_color(self, path, idx, color = wx.BLACK):
        nm = os.path.basename(path)

        im = self.itemDataMap_ix + 1
        self.itemDataMap_ix = im
        self.itemDataMap[im] = (nm, path)

        ii = self.InsertStringItem(idx, nm)
        self.SetItemTextColour(ii, color)
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
        menu.Append(self.sel_all_id, "Select All")
        menu.AppendSeparator()
        menu.Append(self.rm_item_id, "Remove Selected Items")
        menu.Append(self.empty_list, "Remove All")
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
"""
class ABasePane(wx.ScrolledWindow):
    def __init__(self, parent, gist, wi, hi, id = -1):
        wx.ScrolledWindow.__init__(self, parent, id)
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

    def add_child_wnd(self, wnd):
        if not wnd in self.child_wnds:
            self.child_wnds.append(wnd)

    # call wx Window->Enable(benabled) on all of self.child_wnds
    # that are not excluded by presence in tuple not_these
    def enable_all(self, benabled = True, not_these = ()):
        for c in self.child_wnds:
            self.child_wnds_prev_state[c] = c.IsEnabled()
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

        self.SetMinSize(wx.Size(self.sz.width, self.sz.height / 4))
        self.panel = AVolInfPanePanel(self, gist, self.sz)
        self.SetVirtualSize(self.sz)

    def get_panel(self):
        return self.panel

"""
AVolInfPanePanel -- Panel window for operation volume info fields setup
"""
class AVolInfPanePanel(wx.Panel):
    def __init__(self, parent, gist, size, id = -1):
        size.height *= 2
        wx.Panel.__init__(self, parent, id, wx.DefaultPosition, size)
        self.parent = parent
        self.parent.attach_methods(self)

        self.core_ld = gist
        self.core_ld.set_vol_wnd(self)

        self.SetMinSize(wx.Size(size.width, size.height / 4))
        self.SetMaxSize(size)

        self.ctls = []

        inf_keys, inf_map, inf_vec = self.core_ld.get_vol_datastructs()

        # top level sizer
        self.bSizer1 = wx.FlexGridSizer(0, 1, 0, 0)
        self.bSizer1.SetMinSize(size)
        self.bSizer1.AddGrowableCol(0)
        self.bSizer1.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_ALL)

        type_optChoices = []
        type_optChoices.append("copy from source")
        type_optChoices.append("hand edit")

        self.type_opt = wx.RadioBox(
            self, wx.ID_ANY, "select field content",
            wx.DefaultPosition, wx.DefaultSize, type_optChoices, 1,
            wx.RA_SPECIFY_ROWS)
        self.type_opt.SetToolTip(
            wx.ToolTip(
            "Select the "
            ))
        self.add_child_wnd(self.type_opt)

        # type opt in top level sizer
        self.bSizer1.Add(self.type_opt, 0, wx.ALL, 5)

        rn = 1
        for key, flen, opt, deflt, label in inf_keys:
            box = wx.StaticBoxSizer(
                wx.StaticBox(
                    self, wx.ID_ANY,
                    "%s (%u characters maximum)" % (label, flen)),
                wx.VERTICAL
                )

            sty = 0
            if flen > 60:
                sty = sty | wx.TE_MULTILINE

            txt = wx.TextCtrl(
                self, wx.ID_ANY, "", wx.DefaultPosition, wx.DefaultSize,
                sty, wx.DefaultValidator, key)
            txt.SetMaxLength(flen)
            txt.SetValue(deflt)
            box.Add(txt, 1, wx.ALL|wx.EXPAND, 2)
            self.ctls.append(txt)
            self.add_child_wnd(txt)

            if flen > 80:
                self.bSizer1.Add(box, 1, wx.ALL|wx.EXPAND, 3)
                self.bSizer1.AddGrowableRow(rn, 2)
            else:
                self.bSizer1.Add(box, 1, wx.ALL|wx.EXPAND, 3)

            rn = rn + 1


        self.dict_source = {}
        self.dict_user = {}

        self.SetSizer(self.bSizer1)
        self.Layout()

        self.type_opt.Bind(
            wx.EVT_RADIOBOX, self.on_type_opt)

        self.type_opt.SetSelection(0)
        self.do_on_type_opt(0)


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
                    c.SetValue('')
                #c.Enable(False)
        elif idx == 1:
            for c in self.ctls:
                #c.Enable(True)
                l = c.GetName()
                if l in dict_user:
                    c.SetValue(dict_user[l])
                else:
                    c.SetValue('')

    def set_source_info(self, voldict):
        self.dict_source = {}
        dict_source = self.dict_source
        idx = self.type_opt.GetSelection()

        for key in voldict:
            c = self.FindWindowByName(key)
            if not c:
                continue

            val = voldict[key]
            dict_source[key] = val
            if idx == 0:
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

        #self.SetMinSize(size)
        #self.SetMaxSize(size)

        # top level sizer
        self.bSizer1 = wx.FlexGridSizer(0, 1, 0, 0)
        self.bSizer1.AddGrowableCol(0)

        self.set_select = []

        type_optChoices = []
        type_optChoices.append("file/directory")
        type_optChoices.append("burner device")
        type_optChoices.append("direct to burner")

        self.type_opt = wx.RadioBox(
            self, wx.ID_ANY, "select destination",
            wx.DefaultPosition, wx.DefaultSize, type_optChoices, 1,
            wx.RA_SPECIFY_ROWS)
        self.type_opt.SetToolTip(
            wx.ToolTip(
            "Select the output target of the backup. "
            "The first option 'file/directory' will simply put a "
            "filesystem image (an .iso) or a directory hierarchy "
            "on your hard drive. "
            "The second option 'burner device' will write a temporary "
            "file or directory and then prompt you to make sure "
            "the burner is ready with a disc. "
            "The third option 'direct to burner' may be used if you "
            "have two devices: one to read and one to write. This "
            "option attempts to write the backup disc as it is read "
            "from the source drive.\n"
            "WARNING: this option is not reliable and is likely "
            "to fail and ruin the target disc."
            ))
        self.add_child_wnd(self.type_opt)

        self.box_whole = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "backup target:"),
            wx.VERTICAL
            )

        self.select_label = wx.StaticText(
            self, wx.ID_ANY,
            "select output file, directory, or burner device node:",
            wx.DefaultPosition, wx.DefaultSize, 0)
        self.select_label.Wrap(-1)
        self.box_whole.Add(self.select_label, 0, wx.ALL, 5)

        self.fgSizer_node_whole = wx.FlexGridSizer(2, 1, 0, 0)
        self.fgSizer_node_whole.AddGrowableCol(0)
        self.fgSizer_node_whole.AddGrowableRow(0, 1)
        self.fgSizer_node_whole.AddGrowableRow(1, 2)
        self.fgSizer_node_whole.SetFlexibleDirection(wx.BOTH)
        self.fgSizer_node_whole.SetNonFlexibleGrowMode(
            wx.FLEX_GROWMODE_SPECIFIED)

        self.input_select_node = wx.TextCtrl(
            self, wx.ID_ANY, "",
            wx.DefaultPosition, wx.DefaultSize,
            wx.TE_PROCESS_ENTER|wx.TE_PROCESS_TAB)
        self.fgSizer_node_whole.Add(
            self.input_select_node, 1,
            wx.ALIGN_CENTER|wx.ALL|wx.EXPAND, 2)
        self.add_child_wnd(self.input_select_node)
        self.set_select.append(self.input_select_node)

        nodbuttsz = wx.BoxSizer(wx.HORIZONTAL)

        self.button_select_node = wx.Button(
            self, wx.ID_ANY,
            "Select Target",
            wx.DefaultPosition, wx.DefaultSize, 0)
        nodbuttsz.Add(
            self.button_select_node, 1,
            wx.ALIGN_CENTER|wx.ALL, 1)
        self.add_child_wnd(self.button_select_node)
        self.set_select.append(self.button_select_node)

        self.fgSizer_node_whole.Add(
            nodbuttsz, 5,
            wx.ALIGN_CENTER_HORIZONTAL|wx.EXPAND, 1)

        self.box_whole.Add(
            self.fgSizer_node_whole, 1,
            wx.ALIGN_CENTER_HORIZONTAL|wx.EXPAND, 1)

        # begin vol info panel
        self.box_volinfo = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "target volume info fields:"),
            wx.VERTICAL
            )

        self.panel_volinfo = AVolInfPane(
            self, self.core_ld, size.width - 40, size.height - 40)
        self.add_child_wnd(self.panel_volinfo)

        self.box_volinfo.Add(
            self.panel_volinfo, 1,
            wx.ALIGN_CENTER_HORIZONTAL|wx.EXPAND, 1)
        # end vol info panel

        self.box_check = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "check settings:" ),
            wx.VERTICAL
            )

        self.fgSizer1 = wx.FlexGridSizer(1, 2, 0, 0)
        self.fgSizer1.AddGrowableCol(0)
        self.fgSizer1.AddGrowableCol(1)
        self.fgSizer1.AddGrowableRow(0)
        self.fgSizer1.SetFlexibleDirection(wx.HORIZONTAL)
        self.fgSizer1.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_NONE)

        self.check_button = wx.Button(
            self, wx.ID_ANY,
            "Check settings", wx.DefaultPosition, wx.DefaultSize, 0)
        self.fgSizer1.Add(
            self.check_button, 0,
            wx.ALIGN_CENTER|wx.EXPAND|wx.ALL, 5)
        self.add_child_wnd(self.check_button)

        self.run_label = "Run it"
        self.cancel_label = "Cancel"
        self.cancel_mode = False
        self.run_button = wx.Button(
            self, wx.ID_ANY,
            self.run_label, wx.DefaultPosition, wx.DefaultSize, 0)
        self.fgSizer1.Add(
            self.run_button, 0,
            wx.ALIGN_CENTER|wx.EXPAND|wx.ALL, 5)
        self.run_button.Enable(False)
        self.add_child_wnd(self.run_button)

        self.box_check.Add(
            self.fgSizer1, 1,
            wx.ALIGN_CENTER_HORIZONTAL|wx.EXPAND, 5)


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
            self.box_check, 1,
            wx.EXPAND|wx.ALL|wx.BOTTOM, 5)

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


    def on_select_node(self, event):
        self.dev = self.input_select_node.GetValue()
        msg_line_INFO("set target to %s" % self.dev)

    def on_button_select_node(self, event):
        typ = self.type_opt.GetSelection()
        tit = "Select burner device node"
        tdr = ""
        sty = 0

        # to fs:
        if typ == 0:
            if self.core_ld.get_is_whole_backup():
                tit = "Select file name for filesystem image"
            else:
                tit = "Select directory name for hierarchy"
            # wx.FD_OVERWRITE_PROMPT removed: manager object prompts
            #sty = wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT
            sty = wx.FD_SAVE
        # to device
        else:
            tdr = "/dev"
            sty = wx.FD_OPEN|wx.FD_FILE_MUST_EXIST

        pw = wx.GetApp().GetTopWindow()
        file_dlg = wx.FileDialog(pw, tit, tdr, "", "*", sty)

        r = file_dlg.ShowModal()

        if r == wx.ID_OK:
            fil = file_dlg.GetPath()
            self.input_select_node.SetValue(fil)
            self.on_select_node(None)

    def do_opt_id_change(self, t_id):
        pass

    def on_type_opt(self, event):
        t_id = event.GetEventObject().GetSelection()
        self.do_opt_id_change(t_id)
        self.core_ld.target_opt_id_change(t_id)

    def on_check_button(self, event):
        self.do_dd_dvd_check()

    def on_run_button(self, event):
        self.dev = self.input_select_node.GetValue()
        self.core_ld.do_run(self.dev)

    def do_dd_dvd_check(self, dev = None):
        self.core_ld.do_dd_dvd_check(dev)

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

    def set_target_text(self, target_text):
        self.input_select_node.SetValue(target_text)
        self.on_select_node(None)



"""
ASourcePane -- Pane window for operation source setup
"""
class ASourcePane(ABasePane):
    def __init__(self, parent, gist, wi, hi, id = -1):
        ABasePane.__init__(self, parent, gist, wi, hi, id)
        self.panel = ASourcePanePanel(self, gist, self.sz)

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
        self.bSizer1 = wx.FlexGridSizer(3, 1, 0, 0)
        self.bSizer1.AddGrowableCol(0)
        self.bSizer1.AddGrowableRow(2)
        self.bSizer1.SetMinSize(size)

        type_optChoices = []
        type_optChoices.append("whole filesystem")
        type_optChoices.append("filesystem hierarchy")

        self.type_opt = wx.RadioBox(
            self, wx.ID_ANY, "backup type",
            wx.DefaultPosition, wx.DefaultSize, type_optChoices, 1,
            wx.RA_SPECIFY_ROWS)
        self.type_opt.SetToolTip(
            wx.ToolTip(
            "Select the type of backup to perform: the first option "
            "will make a backup copy of the disk filesystem, and the "
            "second will copy files recursively from the disc "
            "mount point, allowing additional files and directories "
            "to be added to the backup."
            ))
        self.add_child_wnd(self.type_opt)


        self.box_whole = wx.StaticBoxSizer(
            wx.StaticBox(
                self, wx.ID_ANY, "backup source:"
                ),
            wx.VERTICAL
            )

        staticText3 = wx.StaticText(
            self, wx.ID_ANY,
            "select DVD device node or mount point:",
            wx.DefaultPosition, wx.DefaultSize, 0)
        staticText3.Wrap(-1)
        self.box_whole.Add(staticText3, 0, wx.ALL, 5)

        self.fgSizer_node_whole = wx.FlexGridSizer(2, 1, 0, 0)
        self.fgSizer_node_whole.AddGrowableCol(0)

        self.input_node_whole = wx.TextCtrl(
            self, wx.ID_ANY, "",
            wx.DefaultPosition, wx.DefaultSize,
            wx.TE_PROCESS_ENTER|wx.TE_PROCESS_TAB)
        self.fgSizer_node_whole.Add(
            self.input_node_whole, 1,
            wx.ALIGN_CENTER|wx.ALL|wx.EXPAND, 2)
        self.add_child_wnd(self.input_node_whole)

        nodbuttsz = wx.BoxSizer(wx.HORIZONTAL)

        self.button_node_whole = wx.Button(
            self, wx.ID_ANY,
            "Select Node",
            wx.DefaultPosition, wx.DefaultSize, 0)
        nodbuttsz.Add(
            self.button_node_whole, 1,
            wx.ALIGN_CENTER|wx.ALL, 1)
        self.add_child_wnd(self.button_node_whole)
        self.set_whole.append(self.button_node_whole)

        self.button_dir_whole = wx.Button(
            self, wx.ID_ANY,
            "Select Mount",
            wx.DefaultPosition, wx.DefaultSize, 0)
        nodbuttsz.Add( self.button_dir_whole, 1,
            wx.ALIGN_CENTER|wx.ALL, 1)
        self.add_child_wnd(self.button_dir_whole)

        self.fgSizer_node_whole.Add(
            nodbuttsz, 5,
            wx.ALIGN_CENTER_HORIZONTAL|wx.EXPAND, 1)

        self.box_whole.Add(
            self.fgSizer_node_whole, 1,
            wx.ALIGN_CENTER_HORIZONTAL|wx.EXPAND, 1)

        self.box_hier = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY,
                "extra files and directories for "
                "hierarchy (optional):"),
            wx.VERTICAL
            )

        self.fgSizer_extra_hier = wx.FlexGridSizer(1, 1, 0, 0)
        self.fgSizer_extra_hier.AddGrowableCol(0)
        self.fgSizer_extra_hier.AddGrowableRow(0)
        self.fgSizer_extra_hier.SetFlexibleDirection(wx.BOTH)
        self.fgSizer_extra_hier.SetNonFlexibleGrowMode(
            wx.FLEX_GROWMODE_SPECIFIED)

        self.addl_list_ctrl = AFileListCtrl(self, gist)
        self.add_child_wnd(self.addl_list_ctrl)

        self.fgSizer_extra_hier.Add(
            self.addl_list_ctrl, 50,
            wx.ALIGN_CENTER_HORIZONTAL|wx.EXPAND, 5)
        self.set_hier.append(self.addl_list_ctrl)

        lstbuttsz = wx.BoxSizer(wx.HORIZONTAL)

        self.button_addl_files = wx.Button(
            self, wx.ID_ANY,
            "Add Files",
            wx.DefaultPosition, wx.DefaultSize, 0)
        lstbuttsz.Add(
            self.button_addl_files, 1,
            wx.EXPAND, 2)
        self.set_hier.append(self.button_addl_files)
        self.add_child_wnd(self.button_addl_files)

        self.button_addl_dirs = wx.Button(
            self, wx.ID_ANY,
            "Add Directories",
            wx.DefaultPosition, wx.DefaultSize, 0)
        lstbuttsz.Add(
            self.button_addl_dirs, 1,
            wx.EXPAND, 2)
        self.set_hier.append(self.button_addl_dirs)
        self.add_child_wnd(self.button_addl_dirs)

        self.fgSizer_extra_hier.Add(lstbuttsz, 1, wx.EXPAND, 5)

        lstbuttsz2 = wx.BoxSizer(wx.HORIZONTAL)

        self.button_addl_rmsel = wx.Button(
            self, wx.ID_ANY,
            "Remove Selected",
            wx.DefaultPosition, wx.DefaultSize, 0)
        lstbuttsz2.Add(self.button_addl_rmsel, 1,  wx.EXPAND, 2)
        self.set_hier.append(self.button_addl_rmsel)
        self.add_child_wnd(self.button_addl_rmsel)

        self.button_addl_clear = wx.Button(
            self, wx.ID_ANY,
            "Clear List",
            wx.DefaultPosition, wx.DefaultSize, 0)
        lstbuttsz2.Add(self.button_addl_clear, 1, wx.EXPAND, 2)
        self.set_hier.append(self.button_addl_clear)
        self.add_child_wnd(self.button_addl_clear)

        self.fgSizer_extra_hier.Add(lstbuttsz2, 1, wx.EXPAND, 5)

        self.box_hier.Add(
            self.fgSizer_extra_hier, 17,
            wx.ALIGN_CENTER|wx.EXPAND, 5)

        # type opt in top level sizer
        self.bSizer1.Add(self.type_opt, 0, wx.ALL, 5)

        # whole image dev select in top level sizer
        self.bSizer1.Add(
            self.box_whole, 20,
            wx.EXPAND|wx.ALL|wx.TOP, 5)

        # hierarchy copy dev select in top level sizer
        self.bSizer1.Add(
            self.box_hier, 23,
            wx.EXPAND|wx.ALL|wx.TOP, 5)

        self.SetSizer(self.bSizer1)
        self.Layout()

        # Connect Events
        self.type_opt.Bind(
            wx.EVT_RADIOBOX, self.on_type_opt)
        self.input_node_whole.Bind(
            wx.EVT_TEXT_ENTER, self.on_nodepick_whole)
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
        self.file_dlg = wx.FileDialog(
            self.parent, "Select File",
            "", "", "*",
            wx.FD_OPEN|wx.FILE_MUST_EXIST
            )

        self.dir_dlg = wx.DirDialog(
            self.parent, "Select Mount Point",
            "", wx.DD_DIR_MUST_EXIST
            )


    def do_opt_id_change(self, t_id):
        if t_id == 0:
            set_off = self.set_hier
            set_on  = self.set_whole
        else:
            set_on  = self.set_hier
            set_off = self.set_whole

        for c in set_off:
            c.Enable(False)
        for c in set_on:
            c.Enable(True)

        self.core_ld.source_opt_id_change(t_id)

    def on_type_opt(self, event):
        self.do_opt_id_change(event.GetEventObject().GetSelection())

    def on_nodepick_whole(self, event):
        self.dev = self.input_node_whole.GetValue()
        msg_line_INFO("set source device to %s" % self.dev)

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
            "Select Additional Files",
            "", "", "*",
            wx.FD_OPEN|wx.FD_MULTIPLE|wx.FILE_MUST_EXIST
        )
        #    wx.FD_OPEN|wx.FILE_MUST_EXIST|
        #    wx.FD_MULTIPLE|wx.FD_PREVIEW

        if dlg.ShowModal() != wx.ID_OK:
            return

        self.addl_list_ctrl.add_multi_files(dlg.GetPaths())


    def on_button_addl_dirs(self, event):
        dlg = wx.DirDialog(
            self.parent,
            "Select Additional Directories",
            "",
            wx.DD_DIR_MUST_EXIST
        )

        if dlg.ShowModal() != wx.ID_OK:
            return

        self.addl_list_ctrl.add_multi_files([dlg.GetPath()])


    def on_button_addl_rmsel(self, event):
        self.addl_list_ctrl.rm_selected()


    def on_button_addl_clear(self, event):
        self.addl_list_ctrl.rm_all()

    def get_all_addl_items(self):
        return self.addl_list_ctrl.get_all_items()


"""
AChildSashWnd -- adjustable child of adjustable child of top frame

                 see ASashWnd class below
"""
class AChildSashWnd(wx.SashWindow):
    def __init__(self, parent, sz, logobj, ID, title, gist):
        wx.SashWindow.__init__(self, parent, ID)

        self.core_ld = gist

        self.pane_minw = 40
        szw1 = wx.GetApp().GetTopWindow().GetClientSize()
        szw2 = sz.width / 2

        self.swnd = []
        self.swnd.append(
            wx.SashLayoutWindow(
                self, -1, wx.DefaultPosition, (240, 30),
                wx.NO_BORDER|wx.SW_3D
            ))
        self.swnd[0].SetDefaultSize((szw2, 1000))
        self.swnd[0].SetOrientation(wx.LAYOUT_VERTICAL)
        self.swnd[0].SetAlignment(wx.LAYOUT_LEFT)
        self.swnd[0].SetBackgroundColour(wx.Colour(240, 240, 240))
        self.swnd[0].SetSashVisible(wx.SASH_RIGHT, True)
        self.swnd[0].SetExtraBorderSize(1)

        self.swnd.append(
            wx.SashLayoutWindow(
                self, -1, wx.DefaultPosition, (240, 30),
                wx.NO_BORDER|wx.SW_3D
            ))
        self.swnd[1].SetDefaultSize((szw2, 1000))
        self.swnd[1].SetOrientation(wx.LAYOUT_VERTICAL)
        self.swnd[1].SetAlignment(wx.LAYOUT_LEFT)
        self.swnd[1].SetBackgroundColour(wx.Colour(240, 240, 240))
        self.swnd[1].SetSashVisible(wx.SASH_RIGHT, True)
        self.swnd[1].SetExtraBorderSize(1)

        w_adj = 20
        h_adj = 20
        self.child1_maxw = szw2
        self.child1_maxh = sz.height

        self.child2_maxw = szw2
        self.child2_maxh = sz.height

        self.child1 = ASourcePane(
            self.swnd[0], gist,
            self.child1_maxw - w_adj, self.child1_maxh - h_adj
            )
        self.child2 = ATargetPane(
            self.swnd[1], gist,
            self.child2_maxw - w_adj, self.child2_maxh - h_adj
            )

        self.remainingSpace = self.swnd[1]

        ids = []
        ids.append(self.swnd[0].GetId())
        ids.append(self.swnd[1].GetId())
        ids.sort()

        self.Bind(
            wx.EVT_SASH_DRAGGED_RANGE, self.on_sash_drag,
            id =ids[0], id2=ids[len(ids) - 1]
            )

        self.Bind(wx.EVT_SIZE, self.OnSize)


    def on_sash_drag(self, event):
        if event.GetDragStatus() == wx.SASH_STATUS_OUT_OF_RANGE:
            msg_line_WARN('sash drag is out of range')
            return

        eobj = event.GetEventObject()

        if eobj is self.swnd[0]:
            wi = min(event.GetDragRect().width, self.child1_maxw)
            self.swnd[0].SetDefaultSize((wi, self.child1_maxh))

        elif eobj is self.swnd[1]:
            wi = min(event.GetDragRect().width, self.child2_maxw)
            self.swnd[1].SetDefaultSize((wi, self.child2_maxh))

        wx.LayoutAlgorithm().LayoutWindow(self, self.remainingSpace)
        self.remainingSpace.Refresh()

    def OnSize(self, event):
        sz  = self.swnd[0].GetSize()
        sz1 = self.swnd[1].GetSize()

        wx.LayoutAlgorithm().LayoutWindow(self, self.remainingSpace)

        if sz1.width < self.pane_minw:
            w0 = sz.width - (self.pane_minw - sz1.width)
            if w0 >= self.pane_minw:
                self.swnd[0].SetDefaultSize((w0, sz.height))
            else:
                self.swnd[0].SetDefaultSize((self.pane_minw, sz.height))
            wx.LayoutAlgorithm().LayoutWindow(self, self.remainingSpace)

        elif sz.width < self.pane_minw:
            self.swnd[0].SetDefaultSize((self.pane_minw, sz.height))
            wx.LayoutAlgorithm().LayoutWindow(self, self.remainingSpace)

        elif sz1.width > self.child2_maxw:
            w0 = min(sz.width + (sz1.width - self.child2_maxw),
                self.child1_maxw)
            if sz.width < w0:
                self.swnd[0].SetDefaultSize((w0, sz.height))
                wx.LayoutAlgorithm().LayoutWindow(
                    self, self.remainingSpace)


    def get_msg_obj(self):
        return self.swnd[1].get_msg_obj()


"""
ASashWnd -- adjustable child of top frame
"""
class ASashWnd(wx.SashWindow):
    def __init__(self, parent, ID, title, gist):
        wx.SashWindow.__init__(self, parent, ID)

        self.core_ld = gist

        self.msg_minh = 40
        self.msg_inith = 100
        sz = wx.GetApp().GetTopWindow().GetClientSize()
        sz.height -= self.msg_inith

        self.swnd = []
        self.swnd.append(
            wx.SashLayoutWindow(
                self, -1, wx.DefaultPosition, (30, 30),
                wx.NO_BORDER|wx.SW_3D
            ))
        self.swnd[0].SetDefaultSize((sz.width, sz.height))
        self.swnd[0].SetOrientation(wx.LAYOUT_HORIZONTAL)
        self.swnd[0].SetAlignment(wx.LAYOUT_TOP)
        self.swnd[0].SetBackgroundColour(wx.Colour(240, 240, 240))
        self.swnd[0].SetSashVisible(wx.SASH_BOTTOM, True)
        self.swnd[0].SetExtraBorderSize(1)

        self.swnd.append(
            wx.SashLayoutWindow(
                self, -1, wx.DefaultPosition, (30, 30),
                wx.NO_BORDER|wx.SW_3D
            ))
        self.swnd[1].SetDefaultSize((sz.width, self.msg_inith))
        self.swnd[1].SetOrientation(wx.LAYOUT_HORIZONTAL)
        self.swnd[1].SetAlignment(wx.LAYOUT_TOP)
        self.swnd[1].SetBackgroundColour(wx.Colour(240, 240, 240))
        self.swnd[1].SetSashVisible(wx.SASH_BOTTOM, True)
        self.swnd[1].SetExtraBorderSize(1)

        self.child1_maxw = 16000
        self.child1_maxh = 16000

        self.child2_maxw = 16000
        self.child2_maxh = 16000

        self.w0adj = 20
        sz1 = wx.Size(sz.width, sz.height - 20)
        self.child1 = AChildSashWnd(
            self.swnd[0], sz1, parent, -1,
            "Source and Destination", gist
            )
        self.child2 = AMsgWnd(self.swnd[1], 400, self.msg_inith)
        self.core_ld.set_msg_wnd(self.child2)
        self.child2.set_scroll_to_end(True)

        self.remainingSpace = self.swnd[1]

        ids = []
        ids.append(self.swnd[0].GetId())
        ids.append(self.swnd[1].GetId())
        ids.sort()

        self.Bind(
            wx.EVT_SASH_DRAGGED_RANGE, self.on_sash_drag,
            id=ids[0], id2=ids[len(ids) - 1]
            )

        self.Bind(wx.EVT_SIZE, self.OnSize)

    def on_sash_drag(self, event):
        if event.GetDragStatus() == wx.SASH_STATUS_OUT_OF_RANGE:
            msg_line_WARN('sash drag is out of range')
            return

        eobj = event.GetEventObject()

        if eobj is self.swnd[0]:
            hi = min(self.child1_maxh, event.GetDragRect().height)
            self.swnd[0].SetDefaultSize((self.child1_maxw, hi))

        elif eobj is self.swnd[1]:
            hi = min(self.child2_maxh, event.GetDragRect().height)
            self.swnd[1].SetDefaultSize((self.child2_maxw, hi))

        wx.LayoutAlgorithm().LayoutWindow(self, self.remainingSpace)
        self.remainingSpace.Refresh()
        self.child2.conditional_scroll_adjust()

    def OnSize(self, event):
        ssz = self.GetSize()
        sz  = self.swnd[0].GetSize()
        sz1 = self.swnd[1].GetSize()
        h1 = sz.height

        wx.LayoutAlgorithm().LayoutWindow(self, self.remainingSpace)

        sz.width   += self.w0adj
        ssz.height -= self.msg_minh

        if sz.height > ssz.height:
            if ssz.height >= self.msg_minh:
                self.swnd[0].SetDefaultSize((sz.width, ssz.height))
            else:
                self.swnd[0].SetDefaultSize((sz.width, self.msg_inith))
            wx.LayoutAlgorithm().LayoutWindow(self, self.remainingSpace)
        elif h1 > sz.height:
            self.swnd[0].SetDefaultSize((sz.width, h1))
            wx.LayoutAlgorithm().LayoutWindow(self, self.remainingSpace)

        self.child2.conditional_scroll_adjust()

    def get_msg_obj(self):
        return self.child2


class AFrame(wx.Frame):
    def __init__(self,
            parent, ID, title, gist,
            pos = wx.DefaultPosition, size = wx.DefaultSize):
        wx.Frame.__init__(self, parent, ID, title, pos, size)

        self.core_ld = gist

        self.CreateStatusBar()
        self.Centre(wx.BOTH)

        self.sash_wnd = ASashWnd(self, -1, "The Sash Window", gist)

        self.Bind(wx.EVT_IDLE, self.on_idle)
        self.Bind(wx.EVT_CLOSE, self.on_quit)
        # Custom event from chald handler threads
        self.Bind(EVT_CHILDPROC_MESSAGE, self.on_chmsg, id=self.GetId())

    def on_idle(self, event):
        self.core_ld.do_idle(event)

    def on_quit(self, event):
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
    def __init__(self, topwnd, topwnd_id, cb, args):
        threading.Thread.__init__(self)

        self.topwnd = topwnd
        self.destid = topwnd_id
        self.cb = cb
        self.args = args

        self.status = -1
        self.got_quit = False

        self.per_th = APeriodThread(topwnd, topwnd_id)

    def run(self):
        tid = threading.current_thread().ident
        t = "tid %d" % tid
        self.per_th.start()

        m = 'enter run'
        wx.PostEvent(self.topwnd, AChildProcEvent(m, t, self.destid))

        r = self.cb(self.args)
        self.status = r
        self.per_th.do_stop()
        if self.got_quit:
            return

        self.per_th.join()

        m = 'exit run'
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
    # to be created (by python, not here), and sleep ain't doin' dat
    th_sleep_ok = ("FreeBSD", "OpenBSD")

    def __init__(self, topwnd, topwnd_id, interval = 1):
        threading.Thread.__init__(self)

        self.topwnd = topwnd
        self.destid = topwnd_id
        self.got_stop = False
        self.intvl = interval
        self.tid = 0
        self.tmsg = None

        if os.name == 'posix':
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
        self.tmsg = "tid %d" % self.tid
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
        m = 'time period'
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
        global T_EVT_CHILDPROC_MESSAGE

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
        'opt_values',
        ['s_whole', 's_hier', 't_disk', 't_dev', 't_direct'])(
        0, 1, 0, 1, 2)

    work_msg_interval = 5
    work_msg_last_int = 0
    work_msg_last_idx = 0
    work_msgs = (
        "Working", "Still working", "Yet more working",
        "Be patient", "You know, this is time consuming . . .",
        ". . . I mean, a long process . . .",
        ". . . even for the fastest optical drives . . .",
        ". . . it's a lot of data", "So, working", "and working",
        "No, not hung up . . .", "wait patiently", "Go get a beer",
        "and a whiskey", "or water with a pinch of . . .",
        ". . . ergot of Tuna, or whatever", "Relax",
        "The next statement will be false!",
        "The previous statement was true!",
        "[still seeking Second Foundation]", "Patience please . . .",
        ". . . because I'm still . . .", "[at Alice's Restaurant]"
        )

    def __init__(self):
        self.source = None
        self.target = None

        self.msg_wnd = None
        self.statwnd = None
        self.vol_wnd = None

        # set by app object after top window is ready by call to method
        # set_ready_topwnd() -- at which point other data members must
        # have been set
        self.topwnd = None
        self.topwnd_id = -1

        self.target_force_idx = -1

        self.cur_tempfile = None
        self.all_tempfile = []

        self.ch_thread = None

        self.in_check_op = False

        self.tid = threading.current_thread().ident

        self.uname = os.uname()
        sys = self.uname[0]

        global PROG
        # tuple of tuples each item being:
        # key printed to stdout by dd-dvd -vn re. DVD volume info,
        # length (space padded) of the field,
        # a {mk,gen,grow}isofs option char to set the field,
        # a default value for the field,
        # a label for a GUI interface object
        #  minus some not wanted here
        self.v_inf_keys = (
          ("system_id",          32, "-sysid", sys, "System ID"),
          ("volume_id",          32, "-V", "", "Volume ID"),
          ("volume_set_id",     128, "-volset", "", "Volume Set ID"),
          ("publisher_id",      128, "-publisher", "", "Publisher"),
          ("data_preparer_id",  128, "-p", "", "Data Preparer"),
          ("application_id",    128, "-A", PROG, "Application ID"),
          ("copyright_id",       37, "-copyright", "", "Copyright"),
          ("abstract_file_id",   37, "-abstract", "", "Abstract File"),
          ("bibliographical_id", 37,
           "-biblio", "", "Bibliographical ID")
          )
        self.v_inf_map = {}
        self.v_inf_vec = []
        for i in range(len(self.v_inf_keys)):
            it = self.v_inf_keys[i]
            self.v_inf_map[it[0]] = i
            self.v_inf_vec.append(it)


    def enable_panes(self, benable, rest = False):
        non = (self.target.run_button, None)

        if rest:
            self.source.restore_all(non)
            self.target.restore_all(non)
        else:
            self.source.enable_all(benable, non)
            self.target.enable_all(benable, non)

    def set_ready_topwnd(self, wnd):
        ov = self.opt_values
        self.topwnd = wnd
        self.topwnd_id = wnd.GetId()

        self.source.type_opt.SetSelection(ov.s_whole)
        self.source.do_opt_id_change(ov.s_whole)

    def target_opt_id_change(self, t_id):
        self.target_force_idx = -1

    def source_opt_id_change(self, s_id):
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
                msg_line_WARN("Warning:")
                msg_INFO(
                    " The destination has"
                    " been changed from 'burner device'"
                    " to 'direct to burner' (as it was earlier)."
                    )

        elif s_id == ov.s_hier:
            if t_id == ov.t_direct:
                self.target.type_opt.SetSelection(ov.t_dev)
                self.target.do_opt_id_change(ov.t_dev)
                self.target_force_idx = ov.t_direct
                msg_line_WARN("Warning:")
                msg_INFO(
                    " filesystem hierarchy type backup"
                    " cannot be direct to burner; a temporary"
                    " directory is necessary --\n\tthe destination"
                    " has been changed to 'burner device'."
                    )

            self.target.type_opt.EnableItem(ov.t_direct, False)
            self.get_volinfo_wnd().Enable(True)


    def get_new_idval(self):
        return wx.NewId()

    def get_vol_datastructs(self):
        """provide data structs prepared in _init_ for volume info panel
        """
        return (self.v_inf_keys, self.v_inf_map, self.v_inf_vec)

    def set_source_wnd(self, wnd):
        self.source = wnd

    def set_target_wnd(self, wnd):
        self.target = wnd

    def set_msg_wnd(self, wnd):
        self.msg_wnd = wnd

    def set_vol_wnd(self, wnd):
        self.vol_wnd = wnd

    def get_msg_wnd(self):
        return self.msg_wnd

    def get_stat_wnd(self):
        if self.statwnd == None:
            self.statwnd = wx.GetApp().GetTopWindow()

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

    def working(self):
        if self.ch_thread != None:
            return True
        return False

    def working_msg(self, stat_wnd = None):
        if not self.working():
            return

        if stat_wnd == None:
            stat_wnd = self.get_stat_wnd()

        idx = self.work_msg_last_idx
        stat_wnd.put_status(self.work_msgs[idx])
        idx = (idx + 1) % len(self.work_msgs)
        self.work_msg_last_idx = idx

    def update_working_msg(self, stat_wnd = None):
        last = self.work_msg_last_int
        cur = time.time()
        per = cur - last

        if per >= self.work_msg_interval:
            self.work_msg_last_int = cur
            self.working_msg(stat_wnd)

    def do_idle(self, event):
        pass

    def do_quit(self, event):
        try:
            self.ch_thread.set_quit()
        except:
            pass
        self.do_cancel(True)

    def cb_go_and_read(self, n, s):
        """Callback for ChildTwoStreamReader.go_and_read()
        invoked from temporary thread
        """
        if not self.working():
            return -1

        e = AChildProcEvent("l%d" % n, s, self.topwnd_id)
        wx.PostEvent(self.topwnd, e)

        return 0

    # called with status of a child process
    def do_child_status(self, stat, chil):
        self.target.set_run_label()

        if self.in_check_op:
            self.do_read_child_result(chil)
            if stat == 0:
                self.target.run_button.Enable(True)
            else:
                self.target.run_button.Enable(False)
            self.in_check_op = False
        elif stat == 0 and chil.get_extra_data():
            """With success of read task, ready for burn task:
            chil.get_extra_data() returns None if user option
            was backup to local storage, else it returns a dict
            with data needed to proceed with burn.
            """
            d = chil.get_extra_data()
            outf = d["target_dev"]
            if d["in_burn"] == True:
                # this means burn was just done
                m = "Burn succeeded!. Would you like to burn another? "
                m = m + "If yes, put a new burnable blank in "
                m = m + "the burner addressed by node '%s'." % outf
                r = self.dialog(
                    m, "sty",
                    wx.YES_NO|wx.ICON_QUESTION)
                if r == wx.YES:
                    d["in_burn"] = False
                    self.do_burn(chil, d)
                    return
                else:
                    #self.rm_temp(d["source_file"])
                    self.cleanup_run()
            else:
                m = "Prepared to burn backup. "
                m = m + "Make sure a writable blank disc is ready in "
                m = m + "the burner addressed by node '%s'." % outf
                r = self.dialog(
                    m, "sty",
                    wx.OK|wx.CANCEL|wx.ICON_INFORMATION)
                if r == wx.OK:
                    self.do_burn(chil, d)
                    return
                self.cleanup_run()
        elif stat != 0 and chil.get_extra_data():
            #d = chil.get_extra_data()
            #self.rm_temp(d["source_file"])
            self.cleanup_run()
        else:
            self.cleanup_run()

        self.enable_panes(True, True)

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

        m = ''
        try:
            m = dat.rstrip(' \n\r\t')
        except:
            pass

        if mth and typ == 'time period':
            if not self.in_check_op:
                #msg_line_ERROR(m)
                self.update_working_msg(slno)

        elif mth and typ == 'l1':
            if not self.in_check_op:
                msg_line_INFO('1:')
                msgo.set_mono_font()
                msg_(" %s" % m)
                msgo.set_default_font()

        elif mth and typ == 'l2':
            if not self.in_check_op:
                msg_line_WARN('2:')
                msgo.set_mono_font()
                msg_(" %s" % m)
                msgo.set_default_font()

        elif mth and typ == 'l-1':
            if not self.in_check_op:
                msg_line_ERROR('ERROR')
                msgo.set_mono_font()
                msg_(" %s" % m)
                msgo.set_default_font()

        elif mth and typ == 'enter run':
            self.target.set_cancel_label()
            m = "New thread %s started for child processes" % m
            msg_line_INFO(m)
            slno.put_status(m)

        elif typ == 'exit run':
            # thread join() can throw
            j_ok = True
            try:
                self.ch_thread.join()
            except:
                j_ok = False

            ch = self.get_child_from_thread()
            st = self.ch_thread.get_status()
            stat = ch.get_status()
            bsig = ch.prockilled

            if mth:
                ms = "status"
                if bsig:
                    ms = "cancelled, signal"

                m = ("Child thread %s status %d, process %s %d"
                    % (m, st, ms, stat))
                msg_line_INFO(m)

                if not j_ok:
                    m = "Thread join() fail"
                    msg_line_ERROR(m)
                    #slno.put_status(m)

            #del self.ch_thread
            self.ch_thread = None
            self.work_msg_last_idx = 0
            if st == 0:
                slno.put_status("Success!")
            else:
                slno.put_status(m)

            self.do_child_status(stat, ch)

        elif mth:
            msg_line_ERROR("unknown thread event '%s'" % typ)

    def dialog(self, msg, typ = "msg", sty = None):
        global PROG

        if typ == "msg":
            if sty == None:
                sty = wx.OK | wx.ICON_INFORMATION
            return wx.MessageBox(msg, PROG, sty, self.topwnd)

        if typ == "yesno":
            if sty == None:
                sty = wx.YES_NO | wx.ICON_QUESTION
            return wx.MessageBox(msg, PROG, sty, self.topwnd)

        if typ == "sty":
            # just use 'sty' argument
            return wx.MessageBox(msg, PROG, sty, self.topwnd)

        if typ == "input":
            # use 'sty' argument as default text
            return wx.GetTextFromUser(msg, PROG, sty, self.topwnd)

    def do_cancel(self, quiet = False):
        if self.working():
            ch = self.get_child_from_thread()
            ch.kill(signal.SIGUSR1)

            if not quiet:
                msg_line_INFO("Operation cancelled")

        self.cleanup_run()
        self.target.set_run_label()
        self.enable_panes(True, True)


    #
    # Utilities to help with files and directories
    #

    def get_tempfile(self):
        try:
            ofd, outf = tempfile.mkstemp('.iso', 'dd-dvd-')
            self.cur_tempfile = outf
            return (ofd, outf)
        except OSError, (errno, strerror):
            m = "%s: '%s' (errno %d)" % (
                "Error making temporary file",
                strerror, errno)
            msg_line_ERROR(m)
            self.get_stat_wnd().put_status(m)
            m = "Failed -- " + m
            self.dialog(m, "msg", wx.OK|wx.ICON_EXCLAMATION)
            return False

    # not *the* temp dir like /tmp. but a temporary directory
    def get_tempdir(self):
        try:
            outf = tempfile.mkdtemp('-iso', 'cprec-')
            self.cur_tempfile = outf
            return outf
        except OSError, (errno, strerror):
            m = "%s: '%s' (errno %d)" % (
                "Error making temporary directory",
                strerror, errno)
            msg_line_ERROR(m)
            self.get_stat_wnd().put_status(m)
            m = "Failed -- " + m
            self.dialog(m, "msg", wx.OK|wx.ICON_EXCLAMATION)
            return False

    def get_openfile(self, outf, fl = os.O_WRONLY|os.O_CREAT|os.O_EXCL):
        try:
            ofd = os.open(outf, fl, 0666)
            return (ofd, outf)
        except OSError, (errno, strerror):
            m = "%s: '%s' (errno %d)" % (
                "Error opening file %s" % outf,
                strerror, errno)
            msg_line_ERROR(m)
            self.get_stat_wnd().put_status(m)
            m = "Failed -- " + m
            self.dialog(m, "msg", wx.OK|wx.ICON_EXCLAMATION)
        except AttributeError:
            msg_line_ERROR("Internal error opening %s" % outf)
        except:
            msg_line_ERROR("UNKNOWN EXCEPTION opening %s" % outf)

        return False

    # must call this in try: block, it return single, tuple or False
    def get_outfile(self, outf):
        if self.get_is_fs_target() and self.get_is_whole_backup():
            if not outf:
                ttf = self.cur_tempfile
                try:
                    tfd, tnam = self.get_tempfile()
                    m = "No output file given!\nUse '%s'?" % tnam
                    r = self.dialog(m, "yesno", wx.YES_NO)
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

            self.rm_temp(self.cur_tempfile)
            self.cur_tempfile = None
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
                        m = "%s is a symbolic link to %s."
                        m = m % (outf, outreg)
                        if nsl > 0:
                            m = "%s (with %u symlinks between.)" % (
                                m, nsl)
                        self.dialog(m, "msg", wx.OK|wx.ICON_ERROR)
                        return False

                    m = "%s is a symbolic link to file %s."
                    m = m % (outf, outreg)
                    if nsl > 0:
                        m = "%s (with %u symlinks between.)" % (m, nsl)
                    m = "%s\nShould you overwrite %s?"% (m, outreg)
                    r = self.dialog(m, "yesno", wx.YES_NO)
                    if r != wx.YES:
                        return False
                    return self.get_openfile(
                        outreg, os.O_WRONLY|os.O_TRUNC)

                if sym:
                    m = "%s is a symbolic link to non-existing %s."
                    m = m % (outf, outreg)
                    m = "%s\nUse the name '%s'?" % (
                        m, outreg)
                    r = self.dialog(m, "yesno", wx.YES_NO)
                    if r != wx.YES:
                        return False

                    return self.get_openfile(outreg)

                if reg:
                    m = "%s is an existing file.\nReplace it?" % outf
                    r = self.dialog(m, "yesno", wx.YES_NO)
                    if r != wx.YES:
                        return False

                if not ext:
                    return self.get_openfile(outf)

                if not reg:
                    m = "%s is an existing non-regular file." % outf
                    m = "%s\nProvide a new target or remove %s." % (
                        m, outf)
                    self.dialog(m, "msg", wx.OK|wx.ICON_INFORMATION)
                    return False

                return self.get_openfile(outf, os.O_WRONLY|os.O_TRUNC)

            # not empty string, and not extant
            return self.get_openfile(outf)

        if self.get_is_fs_target() and self.get_is_hier_backup():
            if not outf:
                ttf = self.cur_tempfile
                try:
                    tnam = self.get_tempdir()
                    m = "No output directory given!\nUse '%s'?" % tnam
                    r = self.dialog(m, "yesno", wx.YES_NO)
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

            self.rm_temp(self.cur_tempfile)
            self.cur_tempfile = None
            st = x_lstat(outf, True)

            if st and not stat.S_ISDIR(st.st_mode):
                m = "%s exists. Please choose another directory name."
                m = m % outf
                self.dialog(m, "msg", wx.OK|wx.ICON_ERROR)
                return False

            if st:
                m = "Directory %s exists. Remove and replace (lose) it?"
                m = m % outf
                r = self.dialog(m, "yesno", wx.YES_NO)
                if r == wx.YES:
                    self.rm_temp(outf)
                else:
                    return False

            try:
                os.mkdir(outf, 0777)
            except OSError, (errno, strerror):
                m = "%s: '%s' (errno %d)" % (
                    "Error creating directory %s" % outf,
                    strerror, errno)
                msg_line_ERROR(m)
                self.get_stat_wnd().put_status(m)
                m = "Failed -- " + m
                self.dialog(m, "msg", wx.OK|wx.ICON_EXCLAMATION)
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
            os.chmod(tmp, 0700)
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
        self.rm_temp(self.cur_tempfile)
        self.cur_tempfile = None


    def check_target_dev(self, target_dev):
        st = x_lstat(target_dev, False, False)
        if not st or not (
                stat.S_ISCHR(st.st_mode) or
                stat.S_ISBLK(st.st_mode)):
            m = "Please enter the target DVD burner device node"
            m = m + " in the 'backup target' field"
            msg_line_ERROR(m)
            self.get_stat_wnd().put_status(m)
            r = self.dialog(m, "input", target_dev)
            if len(r) > 0 and r != target_dev:
                target_dev = r
                self.target.set_target_text(r)
                return self.check_target_dev(target_dev)
            return False

        return target_dev

    #
    # Procedures to run the work tasks
    #

    def do_run(self, target_dev):
        if self.target.get_cancel_mode():
            self.do_cancel()
            return

        if self.working():
            # Should not happen -- button should be in cancel mode
            stmsg.put_status("Already busy!")
            return

        if self.get_is_whole_backup():
            self.do_dd_dvd_run(target_dev)
        elif self.get_is_hier_backup():
            self.do_cprec_run(target_dev)
        else:
            msg_line_ERROR("ERROR: internal inconsistency, not good")

    def do_burn(self, dd_child, dat = None):
        if dat == None:
            dat = dd_child.get_extra_data()
        if dat == None:
            return
        if dat["in_burn"] == True:
            # this means burn was just done
            return

        typ = dat["source_type"]

        if typ == "hier":
            self.do_burn_hier(dd_child, dat)
        elif typ == "whole":
            self.do_burn_whole(dd_child, dat)
        else:
            msg_line_ERROR(typ)

    def do_burn_whole(self, dd_child, dat):
        stmsg = self.get_stat_wnd()
        outdev  = dat["target_dev"]
        srcfile = dat["source_file"]
        dat["in_burn"] = True

        msg_line_INFO('\nburn from temporary fs image "%s" to %s' % (
            srcfile, outdev))

        xcmd = 'growisofs'
        xcmdargs = []
        xcmdargs.append(xcmd)
        xcmdargs.append("-speed=6")
        xcmdargs.append("-dvd-video")
        xcmdargs.append("-dvd-compat")

        xcmdargs.append("-Z")
        xcmdargs.append("%s=%s" % (outdev, srcfile))

        stmsg.put_status("Running %s for %s" % (xcmd, srcfile))

        parm_obj = ChildProcParams(xcmd, xcmdargs)
        dd_child.reset_read_lists()
        dd_child.get_status(True)
        dd_child.set_command_params(parm_obj)

        self.child_go(dd_child)

    def do_burn_hier(self, dd_child, dat):
        stmsg = self.get_stat_wnd()
        outdev = dat["target_dev"]
        srcdir = dat["source_file"]
        dat["in_burn"] = True

        msg_line_INFO('\nburn from temporary directory "%s" to %s' % (
            srcdir, outdev))

        xcmd = 'growisofs'
        xcmdargs = []
        xcmdargs.append(xcmd)
        xcmdargs.append("-speed=6")
        xcmdargs.append("-dvd-compat")

        xcmdargs.append("-Z")
        xcmdargs.append(outdev)

        xcmdargs.append("-dvd-video")
        xcmdargs.append("-gui")
        xcmdargs.append("-uid")
        xcmdargs.append("0")
        xcmdargs.append("-gid")
        xcmdargs.append("0")
        xcmdargs.append("-D")
        xcmdargs.append("-R")

        xlst = dat["vol_info"]
        keys, vmap, vvec = self.get_vol_datastructs()

        for i in vvec:
            k = i[0]
            if not k in xlst:
                if len(i[3]) > 0:
                    xcmdargs.append(i[2])
                    xcmdargs.append(i[3])
                continue
            xcmdargs.append(i[2])
            xcmdargs.append(xlst[k])
            msg_line_INFO("add iso fs option %s '%s'" % (
                i[2], xlst[k]))

        xcmdargs.append(srcdir)

        stmsg.put_status("Running %s for %s" % (xcmd, srcdir))

        parm_obj = ChildProcParams(xcmd, xcmdargs)
        dd_child.reset_read_lists()
        dd_child.get_status(True)
        dd_child.set_command_params(parm_obj)

        self.child_go(dd_child)


    def do_cprec_run(self, target_dev, dev = None):
        self.enable_panes(False, False)
        stmsg = self.get_stat_wnd()

        if not dev and self.source and self.source.dev:
            dev = self.source.dev

        if not dev:
            m = "Select a mount point"
            msg_line_ERROR(m)
            stmsg.put_status(m)
            self.dialog(m, "msg", wx.OK|wx.ICON_EXCLAMATION)
            self.enable_panes(True, True)
            return

        origdev = dev
        realdev = os.path.realpath(dev)
        if realdev and realdev != dev:
            dev = realdev
            msg_line_INFO('using source mount "%s" for "%s"' % (
                dev, origdev))

        st = x_lstat(dev, True)
        m = None
        if not st:
            m = "cannot get state of '%s' ('%s'), %s" % (
                dev, origdev, "does it exist?")
        elif not stat.S_ISDIR(st.st_mode):
            m = "Source selection '%s' ('%s') %s" % (
                dev, origdev, "is not a mount point directory.")

        if m:
            msg_line_ERROR(m)
            stmsg.put_status(m)
            self.dialog(m, "msg", wx.OK|wx.ICON_ERROR)
            self.enable_panes(True, True)
            return

        devname = os.path.split(origdev)[1]
        stmsg.put_status("")

        to_dev = self.get_is_dev_tmp_target()
        try:
            if to_dev:
                outf = self.check_target_dev(target_dev)
                if outf:
                    target_dev = outf
                    outf = self.get_tempdir()
            else:
                outf = self.get_outfile(target_dev)
                self.target.set_target_text(outf)
            if outf == False:
                self.enable_panes(True, True)
                return
        except:
            self.enable_panes(True, True)
            return

        msg_line_INFO('using target directory "%s"' % outf)

        xcmd = 'cprec'
        xcmdargs = []
        xcmdargs.append("%s-%s" % (xcmd, devname))
        xcmdargs.append("-vvpfd0")
        xcmdargs.append("-n")
        xcmdargs.append(dev)

        xlst = self.source.get_all_addl_items()
        for i in xlst:
            xcmdargs.append(i)

        xcmdargs.append(dev)
        xcmdargs.append(outf)
        xcmdenv = []
        xcmdenv.append( ('CPREC_LINEBUF', 'true') )
        xcmdenv.append( ('DDD_LINEBUF', 'true') )

        stmsg.put_status("Running %s for %s" % (xcmd, origdev))

        parm_obj = ChildProcParams(xcmd, xcmdargs, xcmdenv)
        dd_child = ChildTwoStreamReader(parm_obj, self)

        if to_dev:
            """Set data so that writer may be run if this succeeds
            """
            dat = {}
            dat["target_dev"] = target_dev
            dat["source_file"] = outf
            dat["source_type"] = "hier"
            dat["in_burn"] = False
            dat["vol_info"] = self.vol_wnd.get_fields()
            dd_child.set_extra_data(dat)

        self.child_go(dd_child)


    def do_dd_dvd_run(self, target_dev, dev = None):
        self.enable_panes(False, False)
        stmsg = self.get_stat_wnd()

        if not dev and self.source and self.source.dev:
            dev = self.source.dev

        if not dev:
            m = "Select a source device node or mount point"
            msg_line_ERROR(m)
            stmsg.put_status(m)
            self.dialog(m, "msg", wx.OK|wx.ICON_EXCLAMATION)
            self.enable_panes(True, True)
            return

        origdev = dev
        realdev = os.path.realpath(dev)
        if realdev and realdev != dev:
            dev = realdev
            msg_line_INFO('using source node "%s" for "%s"' % (
                dev, origdev))

        st = x_lstat(dev, True)
        m = None
        if not st:
            m = "cannot get state of '%s', %s" % (
                dev, "does it exist?")
        elif not (stat.S_ISDIR(st.st_mode) or
                stat.S_ISBLK(st.st_mode) or
                stat.S_ISCHR(st.st_mode)):
            m = "Source selection '%s' %s" % (
                dev,
                "is not a mount point directory, or a device node.")

        if m:
            msg_line_ERROR(m)
            stmsg.put_status(m)
            self.dialog(m, "msg", wx.OK|wx.ICON_ERROR)
            self.enable_panes(True, True)
            return

        devname = os.path.split(dev)[1]
        stmsg.put_status("")

        to_dev = self.get_is_dev_tmp_target()
        try:
            if to_dev:
                outf = self.check_target_dev(target_dev)
                if outf:
                    target_dev = outf
                    ofd, outf = self.get_tempfile()
            else:
                ofd, outf = self.get_outfile(target_dev)
                self.target.set_target_text(outf)
            if outf == False:
                self.enable_panes(True, True)
                return
        except:
            self.enable_panes(True, True)
            return

        msg_line_INFO('using target fs image file "%s"' % outf)

        xcmd = 'dd-dvd'
        xcmdargs = []
        xcmdargs.append("%s-%s" % (xcmd, devname))
        xcmdargs.append("-vv")
        xcmdargs.append(dev)
        xcmdargs.append(outf)
        xcmdenv = []
        xcmdenv.append( ('CPREC_LINEBUF', 'true') )
        xcmdenv.append( ('DDD_LINEBUF', 'true') )

        stmsg.put_status("Running %s for %s" % (xcmd, dev))

        parm_obj = ChildProcParams(xcmd, xcmdargs, xcmdenv)
        dd_child = ChildTwoStreamReader(parm_obj, self)

        if to_dev:
            """Set data so that writer may be run if this succeeds
            """
            dat = {}
            dat["target_dev"] = target_dev
            dat["source_file"] = outf
            dat["source_type"] = "whole"
            dat["in_burn"] = False
            dd_child.set_extra_data(dat)

        self.child_go(dd_child)

        if ofd > -1:
            os.close(ofd)


    def child_go(self, dd_child):
        fpid, rfd = dd_child.go()

        if not dd_child.go_return_ok(fpid, rfd):
            if isinstance(rfd, str) and isinstance(fpid, int):
                ei = fpid
                es = rfd
                m = "cannot execute child because '%s' (%d)" % (es, ei)
            else:
                m = "ERROR: child process failure"

            msg_line_ERROR(m)
            self.dialog(m, "msg", wx.OK|wx.ICON_EXCLAMATION)
            self.enable_panes(True, True)
            return

        try:
            thr = AChildThread(
                self.topwnd, self.topwnd_id,
                self.read_child_in_thread,
                (fpid, rfd, dd_child))
            thr.start()
            self.ch_thread = thr
            self.in_check_op = False
        except:
            # USR1 is handle specially in child obj class
            dd_child.kill_wait(signal.SIGUSR1, 3)
            msg_line_ERROR("ERROR: could not make or run thread")


    def do_dd_dvd_check(self, dev = None):
        self.enable_panes(False, False)
        stmsg = self.get_stat_wnd()

        if self.working():
            stmsg.put_status("Already busy!")
            self.enable_panes(True, True)
            return

        if not dev and self.source and self.source.dev:
            dev = self.source.dev

        if not dev:
            m = "Select a device node or mount point"
            msg_line_ERROR(m)
            stmsg.put_status(m)
            self.dialog(m, "msg", wx.OK|wx.ICON_EXCLAMATION)
            self.enable_panes(True, True)
            return

        devname = os.path.split(dev)[1]

        st = x_lstat(dev, True)
        m = None
        if not st:
            m = "cannot get state of '%s', %s" % (
                dev, "does it exist?")
        elif not (stat.S_ISDIR(st.st_mode) or
                stat.S_ISBLK(st.st_mode) or
                stat.S_ISCHR(st.st_mode)):
            m = "Source selection '%s' %s" % (
                dev,
                "is not a mount point directory, or a device node.")

        if m:
            msg_line_ERROR(m)
            stmsg.put_status(m)
            self.dialog(m, "msg", wx.OK|wx.ICON_ERROR)
            self.enable_panes(True, True)
            return

        xcmd = 'dd-dvd'
        xcmdargs = []
        xcmdargs.append("%s-%s" % (xcmd, devname))
        xcmdargs.append("-vvn")
        xcmdargs.append(dev)
        xcmdenv = []
        xcmdenv.append( ('CPREC_LINEBUF', 'true') )
        xcmdenv.append( ('DDD_LINEBUF', 'true') )

        stmsg.put_status("Checking %s with %s" % (dev, xcmd))

        parm_obj = ChildProcParams(xcmd, xcmdargs, xcmdenv)
        dd_child = ChildTwoStreamReader(parm_obj, self)

        fpid, rfd = dd_child.go()
        if not dd_child.go_return_ok(fpid, rfd):
            if isinstance(rfd, str) and isinstance(fpid, int):
                ei = fpid
                es = rfd
                m = "cannot execute child because '%s' (%d)" % (es, ei)
            else:
                m = "ERROR: child process failure"

            msg_line_ERROR(m)
            self.dialog(m, "msg", wx.OK|wx.ICON_EXCLAMATION)
            self.enable_panes(True, True)
            return

        try:
            thr = AChildThread(
                self.topwnd, self.topwnd_id,
                self.read_child_in_thread,
                (fpid, rfd, dd_child))
            thr.start()
            self.ch_thread = thr
            self.in_check_op = True
        except:
            # USR1 is handle specially in child obj class
            dd_child.kill_wait(signal.SIGUSR1, 3)
            msg_line_ERROR("ERROR: could not make or run thread")

    # child thread callback -- don't invoke directly
    def read_child_in_thread(self, pid_fd_tuple):
        fpid, rfd, dd_child = pid_fd_tuple

        r = dd_child.read_curchild(rfd, self.cb_go_and_read)
        if r:
            dd_child.wait(4, 20)
            return 0
        else:
            dd_child.kill_wait(4, 20)

        return 1

    def do_read_child_result(self, dd_child):
        # to use message object methods
        msgo = self.get_msg_wnd()

        dev  = self.source.dev
        xcmd = dd_child.xcmd

        # lines with these tokens in rlin2 (below)
        # are excluded from output
        excl = (
            'DVDVersion', 'output <standard output>', 'total bad blocks'
        )

        msg_line_("\nChecked device '%s':\n" % dev)

        stat = dd_child.get_status()

        if stat < 60 and stat > -1:
            # print what is available even if stat > 0
            rlin1, rlin2, rlinx = dd_child.get_read_lists()
            for l in rlin2:
                cont = False
                for tok in excl:
                    if tok in l:
                        cont = True
                        break

                if cont:
                    continue
                msg_INFO("VIDEO data, ops:")
                msgo.set_mono_font()
                msg_(" %s" % l)
                msgo.set_default_font()

            tmpdev = dev + "\n"
            voldict = {}

            for l in rlin1:
                lbl, sep, val = l.partition('|')

                if lbl == 'input_arg':
                    mnt, sep, nod = val.partition('|')
                    lbl = 'device node'
                    if tmpdev == nod:
                        val = nod
                    else:
                        val = '%s is %s' % (dev, nod)
                else:
                    voldict[lbl] = val.rstrip(' \n\r\t')

                if val == "\n":
                    val = "[field is not set]\n"

                msg_GOOD("DVD volume info:")
                msgo.set_mono_font()
                msg_(" %s: %s" % (lbl, val))
                msgo.set_default_font()

            # give volume info pane new data
            self.vol_wnd.set_source_info(voldict)

            for l in rlinx:
                msg_ERROR("AUXILIARY OUTPUT: '%s'" % l)

            if stat != 0:
                msg_line_ERROR(
                    "!!! %s check of '%s' FAILED code %d"
                    % (xcmd, dev, stat))

        elif stat >= 60:
            msg_line_ERROR(
                "!!! execution of '%s' FAILED" % xcmd)
        else:
            msg_line_ERROR(
                "!!! check of '%s' FAILED code %d"
                % (dev, stat))


class TheAppClass(wx.App):
    def __init__(self, dummy):
        wx.App.__init__(self)
        self.frame = None

    def OnInit(self):
        global PROG

        self.core_ld = ACoreLogiDat()

        self.frame = AFrame(
            None, -1, PROG, self.core_ld,
            wx.DefaultPosition, wx.Size(840, 600)
            )

        self.frame.Show(True)
        self.SetTopWindow(self.frame)
        self.core_ld.set_ready_topwnd(self.frame)

        return True

    def get_msg_obj(self):
        return self.GetTopWindow().get_msg_obj()

if __name__ == '__main__':
    app = TheAppClass(0)
    app.MainLoop()

