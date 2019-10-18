# coding=utf-8
"""
For Unix/POSIX: exec pipeline, read std{out,err}, get pipe statuses.
"""

import errno
import os
import re
import select
import signal
import stat
import string
import sys
import threading

#import __init__
from .chars import *
from .fp_write import *
from .msgprocs import *
from .debug import pdbg
from .util import *

_dbg = pdbg
_fp_write = fp_write

class ChildProcParams:
    """
    ChildProcParams:
    Parameter object to simplify interface to ChildTwoStreamReader.
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

    ChildTwoStreamReader builds a pipeline if ChildProcParams is in
    fact a list where ChildProcParams.fd is another ChildProcParams,
    and so on.

    For example, like this . . .
    pipecmds = []
    pipecmds.append( ("cat", (), {}) )
    pipecmds.append( ("sed",
        ('-e', 's/lucy/& IN THE SKY/g',
         '-e', 's/kingbee/IM A & BABY/g'),
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


class ChildTwoStreamReader:
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
        _dbg(_T("handler pid {}, with signal {}").format(mpid, sig))
        # are we 1st child. grouper leader w/ children?
        if not self.root:
            # USR1 used by this prog
            if sig == signal.SIGUSR1:
                sig = signal.SIGINT
                for p, s, b, x in self.procstat:
                    _dbg(_T("handler USR1 kill {p}, signal {s}").format(
                        p = p, s = sig))
                    self.kill(sig, p)
            elif sig == signal.SIGUSR2:
                pg = os.getpgrp()
                sig = signal.SIGINT
                _dbg(_T("handler USR2 kill grp {g}, signal {s}").format(
                    g = pg, s = sig))
                os.killpg(pg, sig)
            else:
                self.kill(sig)
            return
        if sig in self._exit_sigs:
            _dbg(_T("handler:exit pid {}, with signal {}").format(
                mpid, sig))
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
            if idx == 0: # controller process -- kill group
                pid = 0 - pid
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
    public: do kill and wait on current child list
    """
    def kill_wait(self, sig = 0):
        if self.kill_index(sig, 0) != 0:
            return -1

        return self._child_wait_all()

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
            _fp_write(fp, pfx)
            _fp_write(fp, lin)

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


# testing
if __name__ == '__main__':
    infile = _T(sys.argv[0])
    rxpatt = _T('^[[:space:]]*$')

    use_infd = True

    pipecmds = []
    # uncomment next line to try child param exception
    #pipecmds.append( (None, (None, ), -1) )
    if use_infd:
        pipecmds.append( (_T("cat"), (), {}) )
    else:
        pipecmds.append( (_T("cat"), (infile,), {}) )
    pipecmds.append( (_T("tr"), (_T('#'), _T('*')), {}) )
    pipecmds.append( (_T("sed"),
        (_T('-e'), _T('s/lucy/& IN THE SKY MIT DIAMONDS/g'),
         _T('-e'), _T('s/kingbee/I\'M A & BABY,/g'),
         _T('-e'), _T('s/\*/--ASTERISK--/g')), {}) )
    pipecmds.append( (_T("grep"), (_T('-E'), _T('-v'), rxpatt), {}) )
    #pipecmds.append( (_T("grep-but-not-really"), (_T('-E'), _T('-v'), rxpatt), {}) )
    #pipecmds.append( (_T("sort"), (), ()) )
    pipecmds.append( (_T("sort"), (), ( (_T("LC_ALL"), _T("C")), )) )
    #pipecmds.append( (_T("sort"), (), [ (_T("LC_ALL"), _T("C")) ]) )
    #pipecmds.append( (_T("sort"), (), {_T("LC_ALL"): _T("C")}) )
    pipecmds.append( (_T("uniq"), (), {_T("TST"): _T("CR:\rNL\nFOO")}) )

    xstat = 0
    parm_obj = None
    if use_infd:
        parm_obj = infile

    for cmd, aargs, cmdenv in pipecmds:
        cmdargs = [cmd]
        msg_line_INFO(_T("command '%s'") % cmd)
        for arg in aargs:
            cmdargs.append(arg)
        try:
            parm_obj = ChildProcParams(cmd, cmdargs, cmdenv, parm_obj)
        except ChildProcParams.BadParam as e:
            msg_line_ERROR(_T("ChildProcParams exception: '%s'") % e)
            exit(1)

    ch_proc = ChildTwoStreamReader(parm_obj)

    is_ok = ch_proc.go_and_read()

    if is_ok:
        msg_line_INFO(_T('child create SUCCESS'))
    else:
        msg_line_ERROR(_T('child create failed'))

    ch_proc.wait()
    is_ok, sig, sstat = ch_proc.get_status_string()
    msg_line_INFO(_T("PIPELINE STATUS {0}").format(sstat))

    if is_ok >= 0:
        stat = is_ok

        if stat != 0:
            msg_line_ERROR(
                _T("child pipeline FAILED code %d, '%s'")
                % (stat, sstat))

        rlin1, rlin2, rlinx = ch_proc.get_read_lists()
        for l in rlin2:
            msg_line_INFO(_T("2: %s") % l)

        for l in rlin1:
            msg_line_GOOD(_T("1: %s") % l)

        if False:
            for l in rlinx:
                dat = ch_proc.get_stat_line_data(l)
                if dat:
                    stat = max(stat, dat[1])
                    msg_line_INFO(
                        _T("STATUS: "
                        "cmd='{cmd}' "
                        "code='{code}' "
                        "signalled='{sig}' "
                        "status_string='{sstr}' "
                        "args: {ae}").format(
                            cmd = dat[0], code = dat[1],
                            sig = dat[2], sstr = dat[3], ae = dat[4])
                        )
                else:
                    msg_line_ERROR(_T("AUX: \"%s\"\n") % l.rstrip())
        else:
            for dat in ch_proc.get_pipeline_status():
                stat = max(stat, dat[1])
                msg_line_INFO(
                    _T("PIPE STATUS: "
                    "cmd='{cmd}' "
                    "code='{code}' "
                    "signalled='{sig}' "
                    "status_string='{sstr}' "
                    "args: {ae}").format(
                        cmd = dat[0], code = dat[1],
                        sig = dat[2], sstr = dat[3], ae = dat[4])
                    )

        xstat += stat

    else:
        xstat += 31
        msg_line_ERROR(_T("child pipeline FAILED BADLY %s") % is_ok)

    exit(xstat)
