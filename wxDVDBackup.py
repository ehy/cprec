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
# use errno.ECONSTANT in a exception handler, and get:
#UnboundLocalError: local variable 'errno' referenced before assignment
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
# from wxPython samples
import wx.lib.mixins.listctrl as listmix
from wx.lib.embeddedimage import PyEmbeddedImage
try:
    import wx.lib.agw.multidirdialog as MDD
except:
    pass
_ = wx.GetTranslation
# end from wxPython samples


"""
    Development hacks^Wsupport
"""

PROG = os.path.split(sys.argv[0])[1]

if "-XGETTEXT" in sys.argv:
    try:
        # argv[0] is unreliable, but this is not for general use.
        _xgt = "xgettext"
        _xgtargs = (_xgt, "-o", "-", "-L", "Python",
                "--keyword=_", "--add-comments", sys.argv[0])
        os.execvp(_xgt, _xgtargs)
    except OSError, (err, serr):
        sys.stderr.write("Exec {0} {p}: {1} ({2})\n".format(
            _xgt, serr, err, p = sys.argv[0]))
        exit(1)


if "-DBG" in sys.argv:
    _ofd, _fdbg_name = tempfile.mkstemp(".dbg", "_DBG_wxDVDBackup-py")
    _fdbg = os.fdopen(_ofd, "w", 0)
else:
    _fdbg = None

def _dbg(msg):
    if not _fdbg:
        return
    _fdbg.write("{0}: {1}\n".format(time.time(), msg))

_dbg("debug file opened")


"""
    Global data
"""

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

msg_red_color = wx.RED
msg_green_color = wx.Colour(0, 227, 0)
msg_blue_color = wx.BLUE
#msg_yellow_color = wx.Colour(227, 227, 0)
msg_yellow_color = wx.Colour(202, 145, 42)

def msg_(msg, clr = wx.BLACK):
    if _msg_obj_init_is_done == True:
        if clr == None:
            _msg_obj.AppendText(msg)
        else:
            _msg_obj.AppendTextColored(msg, clr)
    else:
        sys.stdout.write(msg)

def err_(msg, clr = None):
    _dbg(msg)
    if _msg_obj_init_is_done == True:
        if clr == None:
            _msg_obj.AppendTextColored(msg, msg_red_color)
        else:
            _msg_obj.AppendTextColored(msg, clr)
    else:
        sys.stderr.write(msg)

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


def msg_line_(msg, clr = wx.BLACK):
    if _msg_obj_init_is_done == True:
        msg_("\n" + msg, clr)
    else:
        msg_(msg + "\n", clr)

def err_line_(msg, clr = None):
    m = "{0}: {1}".format(PROG, msg)
    if _msg_obj_init_is_done == True:
        err_("\n" + m, clr)
        sys.stderr.write(m + "\n")
    else:
        err_(m + "\n", clr)

def msg_line_red(msg):
    msg_line_(msg, msg_red_color)

def msg_line_green(msg):
    msg_line_(msg, msg_green_color)
    #msg_line_(msg, wx.GREEN)

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
    except OSError, (errno, strerror):
        m = _("Error: cannot stat '{0}': '{1}' (errno {2})").format(
            path, strerror, errno)
        _dbg(m)
        if not quiet:
            msg_line_ERROR(m)
        return None


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
        parm_obj = ChildProcParams(cmd, cmdargs, cmdenv, parm_obj)
    except ChildProcParams.BadParam, strmsg:
        PutMsgLineERROR("Exception '%s'" % strmsg)
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
            raise ChildProcParams.BadParam, _("cmdargs is wrong type")

        if (isinstance(cmdenv, list) or
            isinstance(cmdenv, dict) or
            isinstance(cmdenv, tuple)):
            self.xcmdenv = cmdenv
        elif cmdenv == None:
            self.xcmdenv = []
        else:
            self.__except_init()
            raise ChildProcParams.BadParam, _("cmdenv is wrong type")

        if isinstance(stdin_fd, str):
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
            raise ChildProcParams.BadParam, _("stdin_fd is wrong type")

    def __del__(self):
        if self.infd_opened and self.infd > -1:
            os.close(self.infd)

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
    prefix1 = "1: "
    prefix2 = "2: "

    fork_err_status = 69
    exec_err_status = 66
    exec_wtf_status = 67
    pgrp_err_status = 68

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

        self.extra_data = None
        self.error_tuple = None
        self.prockilled = False
        self.procstat = -1
        # careful with curchild: -1 uninited, but < -1 pgid
        self.curchild = -1
        self.ch_pgrp = []
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
        _dbg("handler pid %d, with signal %d" % (mpid, sig))
        # are we 1st child. grouper leader w/ children?
        if self.ch_pgrp:
            # USR1 used by this prog
            if sig == signal.SIGUSR1:
                sig = signal.SIGINT
                for p in self.ch_pgrp:
                    _dbg("handler kill %d, with signal %d" % (p, sig))
                    self.kill(sig, p)
            else:
                self.kill(sig)
            return
        if sig in self._exit_sigs:
            _dbg("handler:exit pid %d, with signal %d" % (mpid, sig))
            os._exit(1)

    """
    public: kill (signal) current child
    """
    def kill(self, sig = 0, pid = None):
        if not isinstance(pid, int):
            pid = self.curchild
        if pid > 0 or pid < -1:
            try:
                os.kill(pid, sig)
                return 0
            except OSError, (errno, strerror):
                _dbg("kill exception pid %d -- signal %d -- %s" %
                    (pid, sig, "error '%s' (%d)" (strerror, errno)))
                self.error_tuple = (pid, sig, errno, strerror)

        return -1

    """
    public: wait on current child, mx trys maximum, sleep nsl in loop
    -- note that for non-blocking, call as wait(1, 0) -- see opts
    """
    def wait(self, mx = 1, nsl = 1, fpid = None):
        wpid = fpid
        if not isinstance(wpid, int):
            wpid = self.curchild

        if wpid in (-1, 0):
            return -1

        _dbg("wait pid %d with mx %d" % (wpid, mx))

        opts = 0
        if nsl < 1:
            opts = opts | os.WNOHANG

        global eintr, echild, efault, einval

        # a return val, may be modified
        cooked = 0

        # What are we waiting for? if array self.ch_pgrp
        # is empty then just self.curchild, else any in
        # self.ch_pgrp, so just use self.ch_pgrp
        if not self.ch_pgrp:
            p = wpid
            _dbg("wait adding pid %d to ch_pgrp" % p)
            self.ch_pgrp.append(p)
        else:
            p = wpid
            _dbg("wait with pid %d to len ch_pgrp == %d" %
                (p, len(self.ch_pgrp)))

        while mx > 0:
            mx -= 1
            try:
                pid, stat = os.waitpid(wpid, opts)
                if os.WIFSIGNALED(stat):
                    cooked = os.WTERMSIG(stat)
                    if pid in self.ch_pgrp:
                        self.curchild = -1
                        self.prockilled = True
                        self.procstat = cooked
                        self.ch_pgrp.remove(pid)
                        _dbg("wait signalled known pid %d with %d" %
                            (pid, cooked))
                    else:
                        _dbg("wait signalled unknown pid %d with %d" %
                            (pid, cooked))
                    if len(self.ch_pgrp) == 0:
                        return cooked
                    else:
                        continue

                if os.WIFEXITED(stat):
                    cooked = os.WEXITSTATUS(stat)
                    if pid in self.ch_pgrp:
                        self.curchild = -1
                        self.prockilled = False
                        self.procstat = cooked
                        self.ch_pgrp.remove(pid)
                        _dbg("wait exited known pid %d with %d" %
                            (pid, cooked))
                    else:
                        _dbg("wait exited unknown pid %d with %d" %
                            (pid, cooked))
                    if len(self.ch_pgrp) == 0:
                        return cooked
                    else:
                        continue

            except OSError, (errno, strerror):
                if errno  == eintr:
                    continue
                if errno  == einval:
                    opts = 0
                    continue
                if errno  == echild:
                    # id children to wait on > 1, cooked is last
                    self.curchild = -1
                    self.procstat = cooked
                    _dbg("wait exiting ECHILD %d with %d (%d remain)" %
                        (wpid, cooked, len(self.ch_pgrp)))
                    return cooked
                return -1

            if mx > 0:
                _dbg("wait sleep(%u) pid %d with mx %d"
                    % (nsl, wpid, mx))
                time.sleep(nsl)

        _dbg("wait pid %d FAILURE" % wpid)
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
            self.error_tuple = (0, _("Internal: no child command arg"))
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
            # start new group
            mpid = os.getpid()
            try:
                pgrp = os.getpgrp()
                if pgrp != mpid:
                    os.setpgrp()
                pgrp = os.getpgrp()
            except OSError, (errno, strerror):
                os._exit(self.pgrp_err_status)

            # success?
            if mpid != pgrp:
                os._exit(self.pgrp_err_status)

            self._child_sigs_setup()

            os.close(rfd)

            exrfd1, exwfd1 = os.pipe()
            exrfd2, exwfd2 = os.pipe()

            # do stdin, making pipeline as needed
            if self.params != None:
                fd = self.params.infd
                lastparams = self.params

                # ChildProcParams may be a linked list with
                # member infd as the next-pointer, but they
                # need to be handled tail-first, so collect
                # them in a list[] using .insert(0,) to reverse
                pipelist = []
                while isinstance(fd, ChildProcParams):
                    pipelist.insert(0, fd)
                    lastparams = fd
                    fd = fd.infd

                if isinstance(fd, int) and fd > 0:
                    os.dup2(fd, 0)
                    lastparams.close_infd()

                for fd in pipelist:
                    ifd = self._mk_input_proc(fd, exwfd1, exwfd2)
                    if ifd < 0:
                        os._exit(self.exec_err_status)
                    if ifd != 0:
                        os.dup2(ifd, 0)
                        os.close(ifd)

            try:
                self.curchild = fpid = os.fork()
                if fpid > 0:
                    self.ch_pgrp.append(fpid)
                    _dbg("go %d add pid %d, inp len %d" %
                        (os.getpid(), fpid, len(self.ch_pgrp)))
            except OSError, (errno, strerror):
                os._exit(self.fork_err_status)

            if fpid == 0:
                os.close(exrfd1)
                os.close(exrfd2)
                os.close(wfd)

                if exwfd1 != 1:
                    os.dup2(exwfd1, 1)
                    os.close(exwfd1)
                if exwfd2 != 2:
                    os.dup2(exwfd2, 2)
                    os.close(exwfd2)

                self._child_sigs_defaults()
                try:
                    self._putenv_cntnr(self.xcmdenv)
                    if is_path:
                        os.execv(self.xcmd, self.xcmdargs)
                    else:
                        os.execvp(self.xcmd, self.xcmdargs)
                    os._exit(self.exec_wtf_status)
                except OSError, (errno, strerror):
                    os._exit(self.exec_err_status)

            else:
                # we setpgid, and will deal w/ kids in new pgrp,
                # as stored in self.ch_pgrp[]
                self.curchild = 0 - mpid

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

                global eintr

                while True:
                    try:
                        rl = pl.poll(None)
                    except select.error, (errno, strerror):
                        if errno == eintr:
                            continue
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
                    _dbg("In go() do stat < 0 exit %d"  % self.procstat)
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


    def _mk_input_proc(self, paramobj, fd1, fd2):
        parms = paramobj
        xcmd = parms.xcmd
        xcmdargs = parms.xcmdargs
        xcmdenv = parms.xcmdenv

        is_path = os.path.split(xcmd)
        if len(is_path[0]) > 0:
            is_path = True
        else:
            is_path = False

        try:
            rfd, wfd = os.pipe()
        except OSError, (errno, strerror):
            self.error_tuple = (errno, strerror)
            return -1

        try:
            fpid = os.fork()
            if fpid > 0:
                self.ch_pgrp.append(fpid)
                _dbg("_mk_input_proc %d add pid %d, inp len %d" %
                    (os.getpid(), fpid, len(self.ch_pgrp)))
        except OSError, (errno, strerror):
            os.close(rfd)
            os.close(wfd)
            return -1

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
            except OSError, (errno, strerror):
                os._exit(self.exec_err_status)

        # parent
        else:
            os.close(wfd)

        return rfd

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
    bugstr = ('Home Directory', 'Home directory', 'Desktop')

    def __init__(self,
                 parentwnd,
                 prompt = _("Choose one or more directories:"),
                 tit = _("Browse For Directories:"),
                 defpath = '/',
                 wxstyle = wx.DD_DEFAULT_STYLE,
                 agwstyle = (MDD.DD_DIR_MUST_EXIST|
                             MDD.DD_MULTIPLE),
                 locus = wx.DefaultPosition,
                 dims = wx.DefaultSize,
                 tag = "repaired_mddialog"):
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

    # Protected: override MDD.MultiDirDialog method
    def CreateButtons(self):
        import wx.lib.buttons as buttons

        if self.agwStyle == 0:
            self.newButton = buttons.ThemedGenBitmapTextButton(
                self, wx.ID_NEW, MDD._new.GetBitmap(),
                _("Make New Folder"), size=(-1, 28))
        else:
            self.newButton = wx.StaticText(
                self, wx.ID_NEW, "/\\_o0o_/\\",
                wx.DefaultPosition, wx.DefaultSize, 0)

        self.okButton = buttons.ThemedGenBitmapTextButton(
            self, wx.ID_OK, MDD._ok.GetBitmap(),
            _("OK"), size=(-1, 28))
        self.cancelButton = buttons.ThemedGenBitmapTextButton(
            self, wx.ID_CANCEL, MDD._cancel.GetBitmap(),
            _("Cancel"), size=(-1, 28))

    # Private: fix the tree control
    def __repair_tree(self):
        if "HOME" in os.environ:
            init_dir = os.environ["HOME"]
        else:
            # Give up right here
            return

        bug = self.bugstr
        dir_ctrl = self.dirCtrl
        treectrl = dir_ctrl.GetTreeCtrl()

        item_id = treectrl.GetFirstVisibleItem()

        # WTF?
        wtfstr = 'Sections'
        wtflen = len(wtfstr)
        if treectrl.GetItemText(item_id)[:wtflen] == wtfstr:
            (item_id, cookie) = treectrl.GetFirstChild(item_id)

        rm_items = []

        while item_id:
            lbl = treectrl.GetItemText(item_id)
            if lbl == 'Desktop':
                rm_items.insert(0, item_id)
            elif lbl in bug:
                treectrl.SetItemText(item_id, init_dir)
            item_id = treectrl.GetNextSibling(item_id)

        for item_id in rm_items:
            treectrl.DeleteChildren(item_id)
            treectrl.Delete(item_id)

        treectrl.UnselectAll()
        self.folderText.SetValue('')


    # Use in place of GetPaths()
    def GetRepairedPaths(self):
        if "HOME" in os.environ:
            init_dir = os.environ["HOME"]
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
        str_machd = 'Macintosh HD'
        dir_machd = str_machd + '/'
        len_machd = len(str_machd)
        rm_idx = []
        for i in range(len(pts)):
            p = pts[i]
            if p[:2] == '//':
                p = p.replace('//', '/')
            # the 'Macintosh HD' stuff is *untested*!
            elif p[:len_machd] == str_machd:
                if p == str_machd or p == dir_machd:
                    rm_idx.insert(0, i)
                    continue
                if p[len_machd] == '/':
                    p = p[len_machd:]
            else:
                for misguided in bug:
                    if p[:len(misguided)] == misguided:
                        if init_dir:
                            p = p.replace(misguided, init_dir)
                        else:
                            m = _(
                              "'HOME' env. var. needed; but not found")
                            raise RepairedMDDialog.Unfixable, m
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
        self.get_msg_obj().SetValue(_("Message window."))
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


    def conditional_scroll_adjust(self, lastval = ""):
        subt = lastval.rfind("\n")
        if self.scroll_end == True and subt >= 0:
            self.SetInsertionPointEnd()
            self.showpos = self.GetLastPosition() - subt

        self.ShowPosition(self.showpos)

    def get_msg_obj(self):
        return self

    def set_scroll_to_end(self, true_or_false):
        if true_or_false == True or true_or_false == False:
            self.scroll_end = true_or_false
            self.scroll_end_user_set = True

    def SetValue(self, val):
        wx.TextCtrl.SetValue(self, val)
        self.conditional_scroll_adjust(val)

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
        self.conditional_scroll_adjust(val)

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
        # TRANSLATORS: 'name' is a file name
        li.SetText(_("Name"))
        self.InsertColumnItem(0, li)
        self.SetColumnWidth(0, 192)
        # TRANSLATORS: This is a full path with file name (if reg. file)
        li.SetText(_("Full Path"))
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
                msg_line_WARN(_("Warning:"))
                msg_(_(" '{0}' is a symlink;"
                    " symlinks are recreated, not followed."
                    ).format(p))
                idx = self.add_slink(p, idx) + 1
            elif stat.S_ISDIR(st.st_mode):
                if p == "/":
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
        _dbg("IN enable_all arg %d" % int(benabled))

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
        type_optChoices.append(_("copy from source"))
        type_optChoices.append(_("hand edit"))

        self.type_opt = wx.RadioBox(
            self, wx.ID_ANY, _("select field content"),
            wx.DefaultPosition, wx.DefaultSize, type_optChoices, 1,
            wx.RA_SPECIFY_ROWS)
        self.type_opt.SetToolTip(
            wx.ToolTip(_(
                "These fields allow editing of DVD volume "
                "information when the 'new filesystem' backup "
                "type is selected. (With the 'simple' backup type "
                "volume information is copied as is.)\n"
                "\n"
                "Select whether to use DVD volume information "
                "as found on the source DVD with \"copy from source\","
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
        self.bSizer1.Add(self.type_opt, 0, wx.ALL, 5)

        rn = 1
        for key, flen, opt, deflt, label in inf_keys:
            box = wx.StaticBoxSizer(
                wx.StaticBox(
                    self, wx.ID_ANY,
                    _("{0} ({1} characters maximum)").format(
                        label, flen)),
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
        type_optChoices.append(_("file/directory"))
        type_optChoices.append(_("burner device"))
        type_optChoices.append(_("direct to burner"))

        self.type_opt = wx.RadioBox(
            self, wx.ID_ANY, _("output target:"),
            wx.DefaultPosition, wx.DefaultSize, type_optChoices, 1,
            wx.RA_SPECIFY_ROWS)
        self.type_opt.SetToolTip(wx.ToolTip(_(
            "Select the output type of the backup. "
            "The first option 'file/directory' will simply put a "
            "filesystem image (an .iso) or a directory hierarchy "
            "on your hard drive."
            "\n\n"
            "The second option 'burner device' will write a temporary "
            "file or directory and then prompt you to make sure "
            "the burner is ready with a disc."
            "\n\n"
            "The third option 'direct to burner' may be used if you "
            "have two devices: one to read and one to write. This "
            "option attempts to write the backup disc as it is read "
            "from the source drive. This option is only available "
            "if the \"simple\" backup type is selected"
            "\n\n"
            "WARNING: the third 'direct' option is the least reliable "
            "and might fail and waste the target disc. If you "
            "use this option try a slow burn speed when prompted, "
            "and ensure that your computer is not busy with many tasks."
            )))
        self.add_child_wnd(self.type_opt)

        ttip = _(
            "If you select the \"file/directory\" option, then "
            "provide a path and name for the hard drive output."
            "\n\n"
            "If you select \"burner device\" or \"direct to burner\" "
            "then select the device node associated with the DVD "
            "burner you wish to use."
            "\n\n"
            "You may enter the path directly in the text field, or "
            "click the button to use a file selection dialog."
            )

        self.box_whole = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("output target:")),
            wx.VERTICAL
            )

        self.select_label = wx.StaticText(
            self, wx.ID_ANY,
            _("specify a name for 'file/directory', or burner device:"),
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
        self.input_select_node.SetToolTip(wx.ToolTip(ttip))
        self.fgSizer_node_whole.Add(
            self.input_select_node, 1,
            wx.ALIGN_CENTER|wx.ALL|wx.EXPAND, 2)
        self.add_child_wnd(self.input_select_node)
        self.set_select.append(self.input_select_node)

        nodbuttsz = wx.BoxSizer(wx.HORIZONTAL)

        self.button_select_node = wx.Button(
            self, wx.ID_ANY,
            _("Select Target"),
            wx.DefaultPosition, wx.DefaultSize, 0)
        self.button_select_node.SetToolTip(wx.ToolTip(ttip))
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
            wx.StaticBox(self, wx.ID_ANY,
                _("target volume info fields (optional):")),
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
            wx.StaticBox(self, wx.ID_ANY,
                _("check first, then run:")),
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
            _("Check"), wx.DefaultPosition, wx.DefaultSize, 0)
        self.fgSizer1.Add(
            self.check_button, 0,
            wx.ALIGN_CENTER|wx.EXPAND|wx.ALL, 5)
        self.add_child_wnd(self.check_button)

        self.run_label = _("Run it")
        self.cancel_label = _("Cancel")
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
        self.core_ld.target_select_node(self.dev)
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
        tdr = ""
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
        self.core_ld.do_check(None)

    def on_run_button(self, event):
        self.dev = self.input_select_node.GetValue()
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

    def set_target_text(self, target_text):
        self.input_select_node.SetValue(target_text)
        self.dev = target_text
        msg_line_INFO(_("set target to {0}").format(self.dev))



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
        type_optChoices.append(_("simple"))
        type_optChoices.append(_("new filesystem"))

        self.type_opt = wx.RadioBox(
            self, wx.ID_ANY, _("backup type:"),
            wx.DefaultPosition, wx.DefaultSize, type_optChoices, 1,
            wx.RA_SPECIFY_ROWS)
        self.type_opt.SetToolTip(
            wx.ToolTip(_(
            "Select the type of backup to perform: the first option "
            "will make an exact backup copy of the disc."
            "\n\n"
            "The second option will copy files from the disc into a "
            "new directory, allowing additional files and directories "
            "to be added to the backup.  This new directory will "
            "be the backup. This requires that the disc be mounted, "
            "while the first \"simple\" option does not."
            )))
        self.add_child_wnd(self.type_opt)


        self.box_whole = wx.StaticBoxSizer(
            wx.StaticBox(
                self, wx.ID_ANY, _("backup source:")
                ),
            wx.VERTICAL
            )

        ttip = _(
            "If you're using \"new filesystem\", the "
            "second option, use the 'Select Mount' button to "
            "use a directory selector dialog to specify the mount "
            "point. You may place the mount point in the text field "
            "by hand (and then press enter/return)."
            "\n\n"
            "For the \"simple\" option use 'Select Node' to select "
            "the device node with a file selector dialog, or place "
            "the device node path in the text field "
            "by hand (and then press enter/return)."
            )

        staticText3 = wx.StaticText(
            self, wx.ID_ANY,
            _("use 'Select Node' for \"simple\", "
                "otherwise 'Select Mount':"),
            wx.DefaultPosition, wx.DefaultSize, 0)
        staticText3.Wrap(-1)
        self.box_whole.Add(staticText3, 0, wx.ALL, 5)

        self.fgSizer_node_whole = wx.FlexGridSizer(2, 1, 0, 0)
        self.fgSizer_node_whole.AddGrowableCol(0)

        self.input_node_whole = wx.TextCtrl(
            self, wx.ID_ANY, "",
            wx.DefaultPosition, wx.DefaultSize,
            wx.TE_PROCESS_ENTER|wx.TE_PROCESS_TAB)
        self.input_node_whole.SetToolTip(wx.ToolTip(ttip))
        self.fgSizer_node_whole.Add(
            self.input_node_whole, 1,
            wx.ALIGN_CENTER|wx.ALL|wx.EXPAND, 2)
        self.add_child_wnd(self.input_node_whole)

        nodbuttsz = wx.BoxSizer(wx.HORIZONTAL)

        self.button_node_whole = wx.Button(
            self, wx.ID_ANY,
            _("Select Node"),
            wx.DefaultPosition, wx.DefaultSize, 0)
        self.button_node_whole.SetToolTip(wx.ToolTip(ttip))
        nodbuttsz.Add(
            self.button_node_whole, 1,
            wx.ALIGN_CENTER|wx.ALL, 1)
        self.add_child_wnd(self.button_node_whole)
        self.set_whole.append(self.button_node_whole)

        self.button_dir_whole = wx.Button(
            self, wx.ID_ANY,
            _("Select Mount"),
            wx.DefaultPosition, wx.DefaultSize, 0)
        self.button_dir_whole.SetToolTip(wx.ToolTip(ttip))
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
                _("optional extras for \"new filesystem\" option:")),
            wx.VERTICAL
            )

        self.fgSizer_extra_hier = wx.FlexGridSizer(1, 1, 0, 0)
        self.fgSizer_extra_hier.AddGrowableCol(0)
        self.fgSizer_extra_hier.AddGrowableRow(0)
        self.fgSizer_extra_hier.SetFlexibleDirection(wx.BOTH)
        self.fgSizer_extra_hier.SetNonFlexibleGrowMode(
            wx.FLEX_GROWMODE_SPECIFIED)

        self.addl_list_ctrl = AFileListCtrl(self, gist)
        self.addl_list_ctrl.SetToolTip(
            wx.ToolTip(_(
                "If the \"new filesystem\" backup type is selected, "
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
            self.addl_list_ctrl, 50,
            wx.ALIGN_CENTER_HORIZONTAL|wx.EXPAND, 5)
        self.set_hier.append(self.addl_list_ctrl)

        lstbuttsz = wx.BoxSizer(wx.HORIZONTAL)

        self.button_addl_files = wx.Button(
            self, wx.ID_ANY,
            _("Add Files"),
            wx.DefaultPosition, wx.DefaultSize, 0)
        lstbuttsz.Add(
            self.button_addl_files, 1,
            wx.EXPAND, 2)
        self.set_hier.append(self.button_addl_files)
        self.add_child_wnd(self.button_addl_files)

        self.button_addl_dirs = wx.Button(
            self, wx.ID_ANY,
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
            self, wx.ID_ANY,
            _("Remove Selected"),
            wx.DefaultPosition, wx.DefaultSize, 0)
        lstbuttsz2.Add(self.button_addl_rmsel, 1,  wx.EXPAND, 2)
        self.set_hier.append(self.button_addl_rmsel)
        self.add_child_wnd(self.button_addl_rmsel)

        self.button_addl_clear = wx.Button(
            self, wx.ID_ANY,
            _("Clear List"),
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
            self.parent, _("Select File"),
            "", "", "*",
            wx.FD_OPEN|wx.FILE_MUST_EXIST
            )

        self.dir_dlg = wx.DirDialog(
            self.parent, _("Select Mount Point"),
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
        msg_line_INFO(_("set source device to {0}").format(self.dev))

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
            "", "", "*",
            wx.FD_OPEN|wx.FD_MULTIPLE|wx.FILE_MUST_EXIST
        )
        #    wx.FD_OPEN|wx.FILE_MUST_EXIST|
        #    wx.FD_MULTIPLE|wx.FD_PREVIEW

        if dlg.ShowModal() != wx.ID_OK:
            return

        self.addl_list_ctrl.add_multi_files(dlg.GetPaths())


    def on_button_addl_dirs(self, event):
        if "HOME" in os.environ:
            init_dir = os.environ["HOME"]
        else:
            init_dir = "/"

        try:
            dlg = RepairedMDDialog(
                self.parent,
                tit = _("Select Additional Directories"),
                defpath = init_dir
            )

            resp = dlg.ShowModal()

            if resp != wx.ID_OK:
                dlg.Destroy()
                return

            try:
                pts = dlg.GetRepairedPaths()
            except RepairedMDDialog.Unfixable, msg:
                msg_line_WARN(msg)
                dlg.Destroy()
                raise Exception, msg

            self.addl_list_ctrl.add_multi_files(pts)
            dlg.Destroy()

        except RepairedMDDialog.Unfixable, m:
            dlg.Destroy()
            raise Exception, m

        except Exception, m:
            msg_line_ERROR(_("MDDialog exception: '{0}'").format(m))

            dlg = wx.DirDialog(
                self.parent,
                _("Select Additional Directories"),
                init_dir,
                wx.DD_DIR_MUST_EXIST
            )

            resp = dlg.ShowModal()

            if resp != wx.ID_OK:
                dlg.Destroy()
                return

            self.addl_list_ctrl.add_multi_files([dlg.GetPath()])
            dlg.Destroy()


    def on_button_addl_rmsel(self, event):
        self.addl_list_ctrl.rm_selected()

    def on_button_addl_clear(self, event):
        self.addl_list_ctrl.rm_all()

    def get_all_addl_items(self):
        return self.addl_list_ctrl.get_all_items()


"""
AProgBarPanel -- small class for wxGauge progress bar
"""
class AProgBarPanel(wx.Panel):
    def __init__(self, parent, gist, ID = -1, rang = 1000):
        wx.Panel.__init__(self, parent, ID)

        self.gist = gist
        self.gauge = wx.Gauge(
            self, gist.get_new_idval(), rang,
            style = wx.GA_HORIZONTAL | wx.GA_SMOOTH)

        szr = wx.BoxSizer(wx.HORIZONTAL)
        szr.Add(self.gauge, 1, wx.EXPAND | wx.ALL, 1)
        self.SetSizer(szr)
        self.Layout()

    def get_gauge(self):
        return self.gauge


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
            msg_line_WARN(_('sash drag is out of range'))
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
                self, -1, wx.DefaultPosition, (30, 20),
                wx.NO_BORDER|wx.SW_3D
            ))
        self.swnd[1].SetDefaultSize((sz.width, 20))
        self.swnd[1].SetOrientation(wx.LAYOUT_HORIZONTAL)
        self.swnd[1].SetAlignment(wx.LAYOUT_TOP)
        self.swnd[1].SetBackgroundColour(wx.Colour(240, 240, 240))
        self.swnd[1].SetSashVisible(wx.SASH_BOTTOM, True)
        self.swnd[1].SetExtraBorderSize(0)

        self.swnd.append(
            wx.SashLayoutWindow(
                self, -1, wx.DefaultPosition, (30, 30),
                wx.NO_BORDER|wx.SW_3D
            ))
        self.swnd[2].SetDefaultSize((sz.width, self.msg_inith))
        self.swnd[2].SetOrientation(wx.LAYOUT_HORIZONTAL)
        self.swnd[2].SetAlignment(wx.LAYOUT_TOP)
        self.swnd[2].SetBackgroundColour(wx.Colour(240, 240, 240))
        self.swnd[2].SetSashVisible(wx.SASH_BOTTOM, True)
        self.swnd[2].SetExtraBorderSize(1)

        self.child1_maxw = 16000
        self.child1_maxh = 16000

        self.child2_maxw = 16000
        self.child2_maxh = 20

        self.child3_maxw = 16000
        self.child3_maxh = 16000

        self.w0adj = 20
        sz1 = wx.Size(sz.width, sz.height - 20)
        self.child1 = AChildSashWnd(
            self.swnd[0], sz1, parent, -1,
            _("Source and Destination"), gist
            )

        self.child2 = AProgBarPanel(self.swnd[1], gist)
        self.core_ld.set_gauge_wnd(self.child2)

        self.child3 = AMsgWnd(self.swnd[2], 400, self.msg_inith)
        self.core_ld.set_msg_wnd(self.child3)
        self.child3.set_scroll_to_end(True)

        self.remainingSpace = self.swnd[2]

        ids = []
        ids.append(self.swnd[0].GetId())
        ids.append(self.swnd[1].GetId())
        ids.append(self.swnd[2].GetId())
        ids.sort()

        self.Bind(
            wx.EVT_SASH_DRAGGED_RANGE, self.on_sash_drag,
            id=ids[0], id2=ids[len(ids) - 1]
            )

        self.Bind(wx.EVT_SIZE, self.OnSize)

    def on_sash_drag(self, event):
        if event.GetDragStatus() == wx.SASH_STATUS_OUT_OF_RANGE:
            msg_line_WARN(_('sash drag is out of range'))
            return

        eobj = event.GetEventObject()

        if eobj is self.swnd[0]:
            hi = min(self.child1_maxh, event.GetDragRect().height)
            self.swnd[0].SetDefaultSize((self.child1_maxw, hi))

        elif eobj is self.swnd[2]:
            hi = min(self.child3_maxh, event.GetDragRect().height)
            self.swnd[2].SetDefaultSize((self.child3_maxw, hi))

        wx.LayoutAlgorithm().LayoutWindow(self, self.remainingSpace)
        self.remainingSpace.Refresh()
        self.child3.conditional_scroll_adjust()

    def OnSize(self, event):
        ssz = self.GetSize()
        sz  = self.swnd[0].GetSize()
        sz1 = self.swnd[2].GetSize()
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

        self.child3.conditional_scroll_adjust()

    def get_msg_obj(self):
        return self.child3


class AFrame(wx.Frame):
    def __init__(self,
            parent, ID, title, gist,
            pos = wx.DefaultPosition, size = wx.DefaultSize):
        wx.Frame.__init__(self, parent, ID, title, pos, size)

        self.core_ld = gist

        self.CreateStatusBar()
        self.Centre(wx.BOTH)

        self.sash_wnd = ASashWnd(self, -1, _("The Sash Window"), gist)

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
    # to be created (by python, not here), and sleep is not.
    # Of course, python time.sleep() is not just a wrapped call
    # of libc sleep(3); in fact it will take a float argument.
    th_sleep_ok = ("FreeBSD", "OpenBSD")

    def __init__(self, topwnd, topwnd_id, interval = 1, msg = None):
        threading.Thread.__init__(self)

        self.topwnd = topwnd
        self.destid = topwnd_id
        self.got_stop = False
        self.intvl = interval
        self.tid = 0
        self.tmsg = msg

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
        if not self.tmsg:
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

    regx["drive"] = re.compile(
        '^\s*INQUIRY:\s*\[([^\]]+)\]'
        '\s*\[([^\]]+)\]'
        '\s*\[([^\]]+)\].*$',
        re_flags)
    regx["medium"] = re.compile(
        '^\s*Mounted\s+Media:\s*(\S+),\s+((\S+)(\s+(\S.*\S))?)\s*$',
        re_flags)
    regx["medium id"] = re.compile(
        '^\s*Media\s+ID:\s*(\S.*\S)\s*',
        re_flags)
    regx["medium book"] = re.compile(
        '^\s*Media\s+Book\s+Type:\s*'
        '(\S+),\s+(\S+)(\s+(\S.*\S))?\s*$',
        re_flags)
    regx["medium freespace"] = re.compile(
        '^\s*Free\s+Blocks:\s*(\S+)\s*\*.*$',
        re_flags)
    regx["write speed"] = re.compile(
        '^\s*Write\s+Speed\s*#?([0-9]+):\s*'
        '([0-9]+(\.[0-9]+)?)\s*x.*$',
        re_flags)
    regx["current write speed"] = re.compile(
        '^\s*Current\s+Write\s+Speed:\s*([0-9]+(\.[0-9]+)?)\s*x.*$',
        re_flags)
    regx["write performance"] = re.compile(
        '^\s*Write\s+Performance:\s*(\S.*\S)\s*',
        re_flags)
    regx["speed descriptor"] = re.compile(
        '^\s*Speed\s+Descriptor\s*#?([0-9]+):\s*'
        '([0-9]+)/[0-9]+\s+R@([0-9]+(\.[0-9]+)?)\s*x.*'
        '\sW@([0-9]+(\.[0-9]+)?)\s*x.*$',
        re_flags)
    regx["presence"] = re.compile(
        '((^\s*|.*\s)(no|non-DVD)\s+media)\s+mounted.*$',
        re_flags)

    def __init__(self, name = None):
        if name:
            self.name = name
        else:
            self.name = _("[no name]")

        self.data = {}

        self.data["drive"] = []
        for i in (1, 2, 3):
            self.data["drive"].append(_("unknown"))
        self.data["medium"] = {}
        self.data["medium id"] = ""
        self.data["medium book"] = ""
        self.data["medium freespace"] = 0
        self.data["write speed"] = []
        self.data["current write speed"] = -1
        self.data["write performance"] = ""
        self.data["speed descriptor"] = []
        self.data["presence"] = ""

    def rx_add(self, lin):
        for k in self.regx:
            m = self.regx[k].match(lin)
            if m:
                if k == "drive":
                    for i in (1, 2, 3):
                        if m.group(i):
                            self.data[k][i - 1] = m.group(i).strip()
                elif k == "medium id":
                    self.data[k] = m.group(1)
                elif k == "medium":
                    self.data[k]["id"] = m.group(1)
                    self.data[k]["type"] = m.group(3)
                    if m.group(5):
                        self.data[k]["type_ext"] = m.group(5)
                    else:
                        self.data[k]["type_ext"] = ""
                    self.data[k]["type_all"] = m.group(2)
                elif k == "medium book":
                    self.data[k] = m.group(2)
                elif k == "medium freespace":
                    self.data[k] = int(m.group(1))
                elif k == "write speed":
                    self.data[k].append(float(m.group(2)))
                elif k == "current write speed":
                    self.data[k] = float(m.group(1))
                elif k == "write performance":
                    self.data[k] = m.group(1)
                elif k == "presence":
                    self.data[k] = m.group(1)
                elif k == "speed descriptor":
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
        d = self.get_data_item("write speed")
        if d:
            for s in d:
                ra.append(s)
        else:
            d = self.get_data_item("speed descriptor")
            for s in d:
                ra.append(s[1])

        return ra


    def get_data(self):
        return self.data

    def get_data_item(self, key):
        if key in self.data:
            return self.data[key]
        return None


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
        _("Working"),
        ".",
        ". .",
        ". . .",
        ". . . .",
        ". . . . .",
        ". . . . . .",
        ". . . . . . .",
        ". . . . . . . .",
        ". . . . . . . . .",
        ". . . . . . . . . .",
        ". . . . . . . . . . .",
        ". . . . . . . . . . . .",
        ". . . . . . . . . . . . .",
        ". . . . . . . . . . . . . .",
        ". . . . . . . . . . . . . . .",
        ". . . . . . . . . . . . . . . .",
        "--------------------------------",
        ". . . . . . . . . . . . . . . .",
        ". . . . . . . . . . . . . . .",
        ". . . . . . . . . . . . . .",
        ". . . . . . . . . . . . .",
        ". . . . . . . . . . . .",
        ". . . . . . . . . . .",
        ". . . . . . . . . .",
        ". . . . . . . . .",
        ". . . . . . . .",
        ". . . . . . .",
        ". . . . . .",
        ". . . . .",
        ". . . .",
        ". . .",
        ". .",
        ".",
        "Hey Now!"
        )
    work_msgs_silly = (
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

        # settings per task
        self.checked_input_blocks  = 0
        self.checked_input_arg     = ''
        self.checked_input_devnode = ''
        self.checked_input_mountpt = ''
        self.checked_input_devstat = None
        self.target_data = None
        self.checked_media_blocks   = 0
        self.checked_output_arg     = ''
        self.checked_output_devnode = ''
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

    def target_select_node(self, node):
        if node != self.checked_output_arg:
            self.target_data = None
            self.checked_media_blocks  = 0
            self.checked_output_arg     = ''
            self.checked_output_devnode = ''
            self.checked_output_devstat = None

    def target_opt_id_change(self, t_id):
        self.target_force_idx = -1
        self.target.set_button_select_node_label()

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
                        " been changed from 'burner device'"
                        " to 'direct to burner' (as it was earlier)."
                        ))

        elif s_id == ov.s_hier:
            if t_id == ov.t_direct:
                self.target.type_opt.SetSelection(ov.t_dev)
                self.target.do_opt_id_change(ov.t_dev)
                self.target_force_idx = ov.t_direct
                if not quiet:
                    msg_line_WARN(_("Warning:"))
                    msg_INFO(_(
                        " filesystem hierarchy type backup"
                        " cannot be direct to burner; a temporary"
                        " directory is necessary --\n\tthe destination"
                        " has been changed to 'burner device'."
                        ))

            self.target.type_opt.EnableItem(ov.t_direct, False)
            self.get_volinfo_wnd().Enable(True)

        self.target.set_button_select_node_label()


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

    def set_gauge_wnd(self, wnd):
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

    # update_working* below are for busy updates to gauge
    # and status bar

    def update_working_gauge(self):
        if not self.cur_task_items:
            return

        g = self.get_gauge_wnd()

        try:
            nm = self.cur_task_items["taskname"]
            lamda_key = "lambda_" + nm
            try:
                self.cur_task_items[lamda_key](g)
            except:
                if nm == 'blanking':
                    l = lambda g: self.update_working_blanking(g)
                elif nm == 'cprec':
                    l = lambda g: self.update_working_cprec(g)
                elif nm == 'dd-dvd':
                    l = lambda g: self.update_working_dd_dvd(g)
                elif nm == 'growisofs-hier':
                    l = lambda g: self.update_working_growisofs_hier(g)
                elif nm == 'growisofs-whole':
                    l = lambda g: self.update_working_growisofs(g)
                elif nm == 'growisofs-direct':
                    l = lambda g: self.update_working_growisofs(g)
                else:
                    l = lambda g: g.Pulse()

                self.cur_task_items[lamda_key] = l
                self.cur_task_items[lamda_key](g)
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
            ln = self.cur_task_items["line"]
        except:
            g.Pulse()
            return

        try:
            rx = self.cur_task_items["growisofs-hier-rx"]
        except:
            rx = re.compile('^\s*([0-9]+\.[0-9]+)\s*%\s+.*$')
            self.cur_task_items["growisofs-hier-rx"] = rx

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
            ln = self.cur_task_items["line"]
        except:
            g.Pulse()
            return

        try:
            rx = self.cur_task_items["growisofs-rx"]
        except:
            rx = re.compile('^\s*([0-9]+)/([0-9]+)\s.*$')
            self.cur_task_items["growisofs-rx"] = rx

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
            ln = self.cur_task_items["line"]
        except:
            g.Pulse()
            return

        try:
            rx = self.cur_task_items["cprec-rx"]
        except:
            rx = re.compile('^\s*X\s+(\S.*\S)\s+size\s+([0-9]+)\s*$')
            self.cur_task_items["cprec-rx"] = rx

        m = rx.match(ln)

        if not m:
            g.Pulse()
            return

        fn = m.group(1)
        sz = int(m.group(2))
        # paranoia
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

        idx = self.work_msg_last_idx
        stat_wnd.put_status(self.work_msgs[idx])
        self.work_msg_last_idx = (idx + 1) % len(self.work_msgs)

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
            outdev = dat["target_dev"]
        else:
            outdev = self.checked_output_devnode

        if not outdev:
            self.do_target_check()
            outdev = self.checked_output_devnode

        if not outdev:
            return False

        eq = self.do_devstat_check(outdev, self.checked_output_devstat)
        if not eq:
            if not self.do_target_medium_check(outdev):
                m = _("Target medium check failed")
                msg_line_ERROR(m)
                stmsg.put_status(m)
                return False

        if not self.do_in_out_size_check():
            return False

        return True

    # compare input size to capacity *after* data members are set
    def do_in_out_size_check(self, blank_async = False):
        stmsg = self.get_stat_wnd()

        d = self.target_data
        mm = d.get_data_item("medium")
        if mm["type_ext"]:
            m = mm["type_ext"]
        else:
            m = mm["type"]
        dbl = re.search('(DL|Dual|Double)', m, re.I)

        m = mm["type"]
        if mm["type_ext"]:
            m = m + " " + mm["type_ext"]
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
                r = self.dialog(m, "yesno", wx.YES_NO)
                if r == wx.YES:
                    self.do_blank(d.name, blank_async)
                    if blank_async:
                        return True

                    self.do_target_check(reset = True)
                    if self.checked_output_arg:
                        return True

            return False

        if dbl:
            hbl = self.checked_media_blocks / 2
            if self.checked_input_blocks <= hbl:
                m = _(
                    "Target {0} capacity {1} blocks, only need {2}"\
                    " -- use a single layer DVD blank disc."
                    ).format(
                             m,
                             self.checked_media_blocks,
                             self.checked_input_blocks,
                             )
                msg_line_ERROR(m)
                stmsg.put_status(m)
                return False

        m = _("Good: need {0} free blocks, medium has {1}.").format(
            self.checked_input_blocks, self.checked_media_blocks)
        msg_line_GOOD(m)
        stmsg.put_status(m)

        return True


    def do_target_check(self,
                        target_dev = None,
                        async_blank = False,
                        reset = False):
        if self.get_is_fs_target():
            return

        if reset:
            self.reset_target_data()

        if not target_dev:
            target_dev = self.target.input_select_node.GetValue()

        if target_dev:
            st = self.checked_output_devstat
            if not st:
                #self.reset_source_data()
                if self.do_target_medium_check(target_dev):
                    if self.do_in_out_size_check(async_blank):
                        if async_blank:
                            return
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
        self.checked_input_arg     = ''
        self.checked_input_devnode = ''
        self.checked_input_mountpt = ''
        self.checked_input_devstat = None


    def reset_target_data(self):
        self.target_data = None
        self.checked_media_blocks   = 0
        self.checked_output_arg     = ''
        self.checked_output_devnode = ''
        self.checked_output_devstat = None


    def do_idle(self, event):
        if self.iface_init == False:
            self.iface_init = True
            ov = self.opt_values
            self.source.type_opt.SetSelection(ov.s_whole)
            self.source.do_opt_id_change(ov.s_whole)
            self.target.type_opt.SetSelection(ov.t_dev)
            self.target.do_opt_id_change(ov.t_dev)
            self.target_opt_id_change(ov.t_dev)

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
                    if s1.st_rdev != s2.st_rdev:
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
            outf = d["target_dev"]
            mdone = None
            merr  = None

            if d["in_burn"] == True:
                # this means burn was just done
                self.reset_target_data()
                m = _("Burn succeeded!. Would you like to burn "\
                    "another? If yes, put a new burnable blank in "\
                    "the burner addressed by node '{0}'.").format(outf)
                r = self.dialog(
                    m, "sty",
                    wx.YES_NO|wx.ICON_QUESTION)
                if r == wx.YES:
                    d["in_burn"] = False
                    self.do_target_check(outf, reset = True)
                    if self.checked_output_devnode:
                        d["target_dev"] = self.checked_output_arg
                        if self.do_burn(chil, d):
                            msg_line_INFO(_("Additional burn started."))
                            return
                    else:
                        merr = _("Media Error")

            else:
                m = _("Prepared to burn backup. "\
                    "Make sure a writable blank disc is ready in "\
                    "the burner addressed by node '{0}'.").format(outf)
                r = self.dialog(
                    m, "sty",
                    wx.OK|wx.CANCEL|wx.ICON_INFORMATION)
                if r == wx.OK:
                    self.do_target_check(outf, reset = True)
                    if self.checked_output_devnode:
                        d["target_dev"] = self.checked_output_arg
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

        m = ''
        try:
            m = dat.rstrip(' \n\r\t')
            _dbg("%s: %s" % (typ, m))
        except:
            _dbg("%s: <no data>" % typ)

        if mth and typ == 'time period':
            if not self.in_check_op:
                self.update_working_gauge()
                self.update_working_msg(slno)

            if dat and dat == "pulse":
                if self.gauge_wnd:
                    self.gauge_wnd.Pulse()

        elif mth and typ == 'l1':
            if not self.in_check_op:
                self.mono_message(
                    prefunc = lambda : msg_line_INFO('1:'),
                    monofunc = lambda : msg_(" %s" % m))

            if self.cur_task_items:
                self.cur_task_items["linelevel"] = 1
                self.cur_task_items["line"] = m

        elif mth and typ == 'l2':
            if not self.in_check_op:
                self.mono_message(
                    prefunc = lambda : msg_line_WARN('2:'),
                    monofunc = lambda : msg_(" %s" % m))

            if self.cur_task_items:
                self.cur_task_items["linelevel"] = 2
                self.cur_task_items["line"] = m

        elif mth and typ == 'l-1':
            if not self.in_check_op:
                self.mono_message(
                    prefunc = lambda : msg_line_ERROR('ERROR'),
                    monofunc = lambda : msg_(" %s" % m))

        elif mth and typ == 'enter run':
            self.target.set_cancel_label()
            m = _(
                "New thread {0} started for child processes").format(m)
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
                ms = _("status")
                if bsig:
                    ms = _("cancelled, signal")

                m = _("Child process {0} {1}").format(ms, stat)
                msg_line_INFO(m)

                if not j_ok:
                    m = _("Thread join() fail")
                    msg_line_ERROR(m)

            self.ch_thread = None
            self.work_msg_last_idx = 0

            global eintr

            if stat == 0:
                slno.put_status(_("Success!"))
            elif bsig or (stat == eintr and ch.is_growisofs()):
                slno.put_status(_("Cancelled!"))
            else:
                slno.put_status(_("Failed!"))

            self.do_child_status(stat, ch)

        elif mth:
            msg_line_ERROR(_("unknown thread event '{0}'").format(typ))

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

        if typ == "intinput":
            # use 'sty' argument as tuple w/ addl. args
            prmt, mn, mx, dflt = sty
            return wx.GetNumberFromUser(
                msg, prmt, PROG, dflt, mn, mx, self.topwnd)

        if typ == "choiceindex":
            # use 'sty' argument as default text
            return wx.GetSingleChoiceIndex(msg, PROG, sty, self.topwnd)

    #
    # Utilities to help with files and directories
    #

    def get_tempfile(self):
        try:
            ofd, outf = tempfile.mkstemp('.iso', 'dd-dvd-')
            self.cur_tempfile = outf
            return (ofd, outf)
        except OSError, (errno, strerror):
            m = _("Error making temporary file: '{0}' (errno {1})"
                ).format(strerror, errno)
            msg_line_ERROR(m)
            self.get_stat_wnd().put_status(m)
            self.dialog(m, "msg", wx.OK|wx.ICON_EXCLAMATION)
            return False

    # not *the* temp dir like /tmp. but a temporary directory
    def get_tempdir(self):
        try:
            outf = tempfile.mkdtemp('-iso', 'cprec-')
            self.cur_tempfile = outf
            return outf
        except OSError, (errno, strerror):
            m = _("Error making temporary directory: '{0}' (errno {1})"
                ).format(strerror, errno)
            msg_line_ERROR(m)
            self.get_stat_wnd().put_status(m)
            self.dialog(m, "msg", wx.OK|wx.ICON_EXCLAMATION)
            return False

    def get_openfile(self, outf, fl = os.O_WRONLY|os.O_CREAT|os.O_EXCL):
        try:
            ofd = os.open(outf, fl, 0666)
            return (ofd, outf)
        except OSError, (errno, strerror):
            m = _("Error opening file '{2}': '{0}' (errno {1})"
                ).format(strerror, errno, outf)
            msg_line_ERROR(m)
            self.get_stat_wnd().put_status(m)
            self.dialog(m, "msg", wx.OK|wx.ICON_EXCLAMATION)
        except AttributeError:
            msg_line_ERROR(_("Internal error opening {0}").format(outf))
        except:
            msg_line_ERROR(
                _("UNKNOWN EXCEPTION opening {0}").format(outf))

        return False

    # must call this in try: block, it return single, tuple or False
    def get_outfile(self, outf):
        is_direct = self.get_is_dev_direct_target()

        if is_direct and self.get_is_whole_backup():
            tof = ("/dev/fd/0", "/dev/stdin")
            for f in tof:
                st = x_lstat(f, True, True)
                if st:
                    return f
            # TODO: make fifo e.g.
            #tnam = self.get_tempdir()
            #f = os.path.join(tnam, "wxDVDBackup")
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
                        self.dialog(m, "msg", wx.OK|wx.ICON_ERROR)
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
                    r = self.dialog(m, "yesno", wx.YES_NO)
                    if r != wx.YES:
                        return False
                    return self.get_openfile(
                        outreg, os.O_WRONLY|os.O_TRUNC)

                if sym:
                    m = _(
                        "{0} is a symbolic link to non-existing {1}.\n"
                        "Use the name '{2}'?"
                        ).format(outf, outreg, outreg)
                    r = self.dialog(m, "yesno", wx.YES_NO)
                    if r != wx.YES:
                        return False

                    return self.get_openfile(outreg)

                if reg:
                    m = _(
                        "{0} is an existing file.\nReplace it?"
                        ).format(outf)
                    r = self.dialog(m, "yesno", wx.YES_NO)
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
                    m = _(
                        "No output directory given!\nUse '{0}'?"
                        ).format(tnam)
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

            self.cleanup_run()
            st = x_lstat(outf, True)

            if st and not stat.S_ISDIR(st.st_mode):
                m = _(
                 "{0} exists. Please choose another directory name."
                 ).format(outf)
                self.dialog(m, "msg", wx.OK|wx.ICON_ERROR)
                return False

            if st:
                m = _(
                 "Directory {0} exists. Remove and replace (lose) it?"
                 ).format(outf)
                r = self.dialog(m, "yesno", wx.YES_NO)
                if r == wx.YES:
                    self.rm_temp(outf)
                else:
                    return False

            try:
                os.mkdir(outf, 0777)
            except OSError, (errno, strerror):
                m = _(
                    "Failed, error creating directory \"{0}\":"
                    "'{1}' (errno {2})"
                    ).format(outf, strerror, errno)
                msg_line_ERROR(m)
                self.get_stat_wnd().put_status(m)
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
        try:
            self.rm_temp(self.cur_tempfile)
        except:
            _dbg("cleanup_run: exeption in rm_temp(self.cur_tempfile)")
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
            r = self.dialog(m, "input", target_dev)
            if len(r) > 0 and r != target_dev:
                target_dev = r
                self.target.set_target_text(r)
                return self.check_target_dev(target_dev)
            return False

        if not self.do_target_medium_check(target_dev):
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
            stmsg.put_status(_("Already busy!"))
            return

        if self.get_is_whole_backup():
            if self.get_is_dev_direct_target():
                if not target_dev:
                    m = _("Please set a target device (with disc) "
                          "and click the 'Check settings' button")
                    msg_line_ERROR(m)
                    self.dialog(m, "msg")
                    return
                if not self.do_burn_pre_check():
                    m = _("Please be sure the source and target "
                          "do not change after the Check button")
                    msg_line_ERROR(m)
                    self.dialog(m, "msg")
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
        if do_it and dat["in_burn"] == True:
            # this means burn was just done
            do_it = False

        if do_it and not self.do_burn_pre_check(dat):
            do_it = False

        if not do_it:
            return False

        typ = dat["source_type"]

        if typ == "hier":
            do_it = self.do_burn_hier(ch_proc, dat)
        elif typ == "whole":
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

        return pmt + self.get_drive_medium_info_string("        ")

    def get_drive_medium_info_string(self, prefix = ""):
        if self.target_data == None:
            return _("Select a speed or action from the list:")

        d = self.target_data

        drv = d.get_data_item("drive")
        fw = drv[2]
        model = drv[1]
        drv = drv[0]

        b = d.get_data_item("medium book")
        if not b:
            b = _('[no medium book type found]')

        m = d.get_data_item("medium")
        if m:
            i = int(m["id"].rstrip("hH"), 16)
            ext = ""
            if m["type_ext"]:
                ext = " (%s)" % m["type_ext"]
            m = '%s%s [%02X], booktype %s' % (m["type"], ext, i, b)
        else:
            m = _('[no medium type description found]')

        mi = d.get_data_item("medium id")
        if not mi:
            mi = _('[no medium id found] - booktype {0}').format(b)

        medi = "%s - %s" % (mi, m)

        fr = d.get_data_item("medium freespace")

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
            spds = (2.0, 4.0, 6.0, 8.0, 12.0, 16.0, 18.0)
        chcs = []

        for s in spds:
            chcs.append("{0} (~ {1}KB/s)".format(s, s * 1385))

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
        r = self.dialog(m, "choiceindex", chcs)

        if r < 0:
            return False
        elif r < nnumeric:
            self.last_burn_speed = "%u" % spds[r]
        elif r == def_idx:
            self.last_burn_speed = None
        elif r == last_idx:
            return self.last_burn_speed
        elif r == ent_idx:
            title = "Enter the speed number you would like"
            sdef = self.last_burn_speed
            if not sdef:
                sdef = "%u" % spds[ndefchoice]
            mn = 1
            mx = 256
            m = _("Min {mn}, max {mx}:").format(mn = mn, mx = mx)
            self.last_burn_speed = self.dialog(title, "intinput",
                (m, mn, mx, int(sdef)))
            if self.last_burn_speed < 1:
                self.last_burn_speed = "%u" % spds[ndefchoice]
        elif r == cnc_idx:
            return False
        else:
            self.last_burn_speed = "%u" % spds[ndefchoice]

        return self.last_burn_speed

    def do_burn_whole(self, ch_proc, dat):
        stmsg = self.get_stat_wnd()
        self.cur_task_items = {}

        try:
            outdev  = os.path.realpath(dat["target_dev"])
        except:
            outdev  = dat["target_dev"]
        srcfile = dat["source_file"]
        dat["in_burn"] = True

        msg_line_INFO(_(
            '\nburn from temporary file "{0}" to device {1}').format(
                srcfile, outdev))

        self.cur_out_file = None
        self.cur_task_items["taskname"] = 'growisofs-whole'
        self.cur_task_items["taskfile"] = None
        self.cur_task_items["taskdirect"] = False

        xcmd = 'growisofs'
        xcmdargs = []
        xcmdargs.append(xcmd)

        spd = self.get_burn_speed(xcmd)
        if spd == False:
            self.do_cancel()
            return False
        if spd:
            xcmdargs.append("-speed=%s" % spd)

        xcmdargs.append("-dvd-video")
        xcmdargs.append("-dvd-compat")

        xcmdargs.append("-Z")
        xcmdargs.append("%s=%s" % (outdev, srcfile))

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
            outdev  = os.path.realpath(dat["target_dev"])
        except:
            outdev  = dat["target_dev"]
        srcdir = dat["source_file"]
        dat["in_burn"] = True

        msg_line_INFO(_(
            '\nburn from temporary directory "{0}" to {1}').format(
                srcdir, outdev))

        self.cur_out_file = None
        self.cur_task_items["taskname"] = 'growisofs-hier'
        self.cur_task_items["taskfile"] = None
        self.cur_task_items["taskdirect"] = False

        xcmd = 'growisofs'
        xcmdargs = []
        xcmdargs.append(xcmd)

        spd = self.get_burn_speed(xcmd)
        if spd == False:
            self.do_cancel()
            return False
        if spd:
            xcmdargs.append("-speed=%s" % spd)

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
            s = xlst[k]
            lmax = i[1]
            while len(s) > lmax:
                m = _(
                    "Volume data field '{0}' has max length {1}\n"
                    "'{2}'\nhas length {3}\n"
                    "Edit field, or cancel burn?"
                    ).format(i[4], lmax, s, len(s))
                r = self.dialog(
                    m, "yesno", wx.YES_NO|wx.CANCEL|wx.ICON_QUESTION)
                if r == wx.CANCEL:
                    self.do_cancel()
                    return
                elif r != wx.YES:
                    s = ""
                    continue
                m = _("Please make value length no more than {0}"
                    ).format(lmax)
                s = self.dialog(m, "input", s)
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
            self.dialog(m, "msg", wx.OK|wx.ICON_EXCLAMATION)
            return False

        origdev = dev
        realdev = os.path.realpath(dev)
        if realdev and realdev != dev:
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
            self.dialog(m, "msg", wx.OK|wx.ICON_ERROR)
            return False

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
                return False
        except:
            return False

        msg_line_INFO(_('using target directory "{0}"').format(outf))

        self.cur_out_file = outf
        self.cur_task_items["taskname"] = 'cprec'
        self.cur_task_items["taskfile"] = outf
        self.cur_task_items["taskdirect"] = False

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
        xcmdenv = [
            ('CPREC_LINEBUF', 'true'), ('DDD_LINEBUF', 'true')
            ]

        stmsg.put_status(_("Running {0} for {1}").format(xcmd, origdev))

        parm_obj = ChildProcParams(xcmd, xcmdargs, xcmdenv)
        ch_proc = ChildTwoStreamReader(parm_obj, self)

        if to_dev:
            """Set data so that writer may be run if this succeeds
            """
            dat = {}
            dat["target_dev"] = target_dev
            dat["source_file"] = outf
            dat["source_type"] = "hier"
            dat["in_burn"] = False
            dat["vol_info"] = self.vol_wnd.get_fields()
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
            self.dialog(m, "msg", wx.OK|wx.ICON_EXCLAMATION)
            return False

        origdev = dev
        realdev = os.path.realpath(dev)
        if realdev and realdev != dev:
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
            self.dialog(m, "msg", wx.OK|wx.ICON_ERROR)
            return False

        devname = os.path.split(origdev)[1]
        stmsg.put_status("")

        to_dev = self.get_is_dev_tmp_target()
        is_direct = self.get_is_dev_direct_target()

        ofd = -1
        is_gr = True

        try:
            if to_dev:
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
                'target direct to burner ({0})').format(outf))

        self.cur_out_file = outf
        self.cur_task_items["taskname"] = 'dd-dvd'
        self.cur_task_items["taskfile"] = outf

        xcmd = 'dd-dvd'
        xcmdargs = []
        xcmdargs.append("%s-%s" % (xcmd, devname))
        xcmdargs.append("-vv")
        xcmdargs.append(dev)
        if not is_direct:
            xcmdargs.append(outf)
        xcmdenv = [
            ('CPREC_LINEBUF', 'true'), ('DDD_LINEBUF', 'true')
            ]

        stmsg.put_status(_("Running {0} for {1}").format(xcmd, dev))

        if not is_direct:
            self.cur_task_items["taskdirect"] = False
            parm_obj = ChildProcParams(xcmd, xcmdargs, xcmdenv)
        else:
            self.cur_out_file = None
            self.cur_task_items["taskname"] = 'growisofs-direct'
            self.cur_task_items["taskfile"] = None
            self.cur_task_items["taskdirect"] = True

            inp_obj = ChildProcParams(xcmd, xcmdargs, xcmdenv)

            ycmd = 'growisofs'
            ycmdargs = []
            ycmdargs.append(ycmd)

            spd = self.get_burn_speed(ycmd)
            if spd == False:
                #self.do_cancel()
                return False
            if spd:
                ycmdargs.append("-speed=%s" % spd)

            ycmdargs.append("-dvd-video")
            ycmdargs.append("-dvd-compat")

            ycmdargs.append("-Z")
            ycmdargs.append("%s=%s" % (outdev, outf))

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
            dat["target_dev"] = target_dev
            dat["source_file"] = outf
            dat["source_type"] = "whole"
            dat["in_burn"] = False
            ch_proc.set_extra_data(dat)

        self.child_go(ch_proc)

        if ofd > -1:
            os.close(ofd)

        return True


    def child_go(self, ch_proc, is_check_op = False, cb = None):
        fpid, rfd = ch_proc.go()

        if not ch_proc.go_return_ok(fpid, rfd):
            if isinstance(rfd, str) and isinstance(fpid, int):
                ei = fpid
                es = rfd
                m = _(
                    "cannot execute child because '{0}' ({1})").format(
                        es, ei)
            else:
                m = _("ERROR: child process failure")

            msg_line_ERROR(m)
            self.dialog(m, "msg", wx.OK|wx.ICON_EXCLAMATION)
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

        xcmd = 'dvd+rw-format'
        xcmdargs = []
        xcmdargs.append(xcmd)

        xcmdargs.append("-blank")
        xcmdargs.append(outdev)

        stmsg.put_status(_("Running {0} for {1}").format(xcmd, outdev))

        parm_obj = ChildProcParams(xcmd, xcmdargs)
        ch_proc = ChildTwoStreamReader(parm_obj, self)

        if blank_async:
            self.cur_task_items = {}
            self.cur_task_items["taskname"] = 'blanking'
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
        is_ok = ch_proc.get_status()

        if is_ok == 0:
            m = _("{0} succeeded blanking {1}").format(xcmd, outdev)
            msg_line_GOOD(m)
            stmsg.put_status(m)
        else:
            m = _(
                "Failed media blank of {0} with {1} - status {2}"
                ).format(outdev, xcmd, is_ok)
            msg_line_ERROR(m)
            stmsg.put_status(m)
            return False

        return True


    def do_target_medium_check(self, target_dev):
        stmsg = self.get_stat_wnd()
        self.target_data = None

        if self.working():
            stmsg.put_status(_("Already busy!"))
            return False

        xcmd = 'dvd+rw-mediainfo'
        xcmdargs = []
        xcmdargs.append(xcmd)
        xcmdargs.append(target_dev)
        xcmdenv = []

        m = _("Checking {0} with {1}").format(target_dev, xcmd)
        msg_line_WARN(m)
        stmsg.put_status(m)

        parm_obj = ChildProcParams(xcmd, xcmdargs, xcmdenv)
        ch_proc = ChildTwoStreamReader(parm_obj, self)

        is_ok = ch_proc.go_and_read()

        if not is_ok:
            m = _(
                "Failed media check of {0} with {1}"
                ).format(target_dev, xcmd)
            msg_line_ERROR(m)
            stmsg.put_status(m)
            return False
        else:
            stmsg.put_status(_("Waiting for {0}").format(xcmd))

        ch_proc.wait()
        is_ok = ch_proc.get_status()

        if is_ok:
            m = _(
                "{0} failed status {1} for {2}"
                ).format(xcmd, is_ok, target_dev)
            msg_line_ERROR(m)
            is_ok = False
        else:
            m = _("{0} succeeded for {1}").format(xcmd, target_dev)
            msg_line_INFO(m)
            is_ok = True

        stmsg.put_status(m)

        l1, l2, lx = ch_proc.get_read_lists()
        self.target_data = MediaDrive(target_dev)

        for lin in l2:
            lin = lin.rstrip()
            self.target_data.rx_add(lin)
            msg_line_WARN(lin)

        e = self.target_data.get_data_item("presence")
        if e:
            m = _(
                "Failed: {0} says \"{1}\" for {2}"
                ).format(xcmd, e, target_dev)
            msg_line_ERROR(m)
            stmsg.put_status(m)
            self.target_data = None
            return False

        for lin in l1:
            lin = lin.rstrip()
            self.target_data.rx_add(lin)
            if is_ok:
                msg_line_GOOD(lin)
            else:
                msg_line_ERROR(lin)

        if not is_ok:
            self.target_data = None
        else:
            self.checked_media_blocks = self.target_data.get_data_item(
                "medium freespace")
            msg_line_INFO(_("Medium free blocks: {0}").format(
                self.checked_media_blocks))
            self.checked_output_devnode = os.path.realpath(target_dev)
            st = x_lstat(self.checked_output_devnode)
            self.checked_output_devstat = st

        return is_ok

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
            self.dialog(m, "msg", wx.OK|wx.ICON_EXCLAMATION)
            self.checked_input_arg = ''
            return False

        self.checked_input_arg = origdev = dev
        realdev = os.path.realpath(dev)
        if realdev and realdev != dev:
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
            self.dialog(m, "msg", wx.OK|wx.ICON_ERROR)
            return False

        devname = os.path.split(origdev)[1]

        xcmd = 'dd-dvd'
        xcmdargs = []
        xcmdargs.append("%s-%s" % (xcmd, devname))
        xcmdargs.append("-vvn")
        xcmdargs.append(dev)
        xcmdenv = []
        xcmdenv.append( ('CPREC_LINEBUF', 'true') )
        xcmdenv.append( ('DDD_LINEBUF', 'true') )

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
            ch_proc.wait(4, 20)
            return 0
        else:
            ch_proc.kill_wait(4, 20)

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
            'DVDVersion', 'output <standard output>', 'total bad blocks'
        )

        msg_line_(_("\nChecked device '{0}':\n").format(dev))

        stat = ch_proc.get_status()

        if stat < 60 and stat > -1:
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
                    monofunc = lambda : msg_(" %s" % l))

            voldict = {}

            self.checked_input_mountpt = ''

            for l in rlin1:
                lbl, sep, val = l.partition('|')

                if val:
                    val = val.rstrip(' \n\r\t')

                m = val
                if lbl == 'input_arg':
                    mnt, sep, nod = val.partition('|')
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
                    if lbl == 'filesystem_block_count':
                        self.checked_input_blocks = int(val.strip())

                    if m == "":
                        m = _("[field is not set]")

                    m = _("{0}: {1}").format(lbl, m)

                self.mono_message(
                    prefunc = lambda : msg_GOOD(_("DVD volume info: ")),
                    monofunc = lambda : msg_(m + "\n"))

            # give volume info pane new data
            self.vol_wnd.set_source_info(voldict)

            for l in rlinx:
                msg_ERROR(_("AUXILIARY OUTPUT: '{0}'").format(l))

            if stat != 0:
                msg_line_ERROR(_(
                    "!!! {0} check of '{1}' FAILED code {2}").format(
                        (xcmd, dev, stat)))
            else:
                self.checked_input_devnode = nod
                st = x_lstat(self.checked_input_devnode)
                self.checked_input_devstat = st

        elif stat >= 60:
            msg_line_ERROR(_(
                "!!! execution of '{0}' FAILED").format(xcmd))
        else:
            msg_line_ERROR(_(
                "!!! check of '{0}' FAILED code {1}").format(
                    (dev, stat)))


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

