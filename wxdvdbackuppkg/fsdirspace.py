# coding=utf-8
"""
Check directories for free space on filesystem.
"""

import errno
import os
import re
import stat
import tempfile

from .chars import *
from .msgprocs import *
from .debug import pdbg
from .util import *
from .childproc import *

_dbg = pdbg

"""
  classes for the task of getting POSIX df -kP results for a directory
"""

class StructDfData:
    """ data structure class to hold df -kP output
        Use like C struct, no logic implemented, just
        get procedures for convenience, although members
        may be accessed directly
    """
    def __init__(self,
                 filesystem = None,
                 blocks_total = -1,
                 blocks_used = -1,
                 blocks_avail = -1,
                 percent_capacity = 100,
                 mount_point = None,
                 size_of_block = 1024):
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

class RegexDf_kP:
    """regex class to masticate df -kP child process lines
    """
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

class FsDirSpaceCheck:
    """
    class to check directories for free space
    """
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
                _dbg(_T("FsDirSpaceCheck: {}").format([d, e.strerror]))
                self.errs.append([d, e.strerror])

        _dbg(_T("FsDirSpaceCheck: {}").format(self.chks))
        self.error = (0, _("No error"))

    def chk_dir(self, d):
        st = os.stat(d)
        if stat.S_ISDIR(st.st_mode):
            return True
        self._raise(errno.ENOTDIR, _("Not a directory"))

    def chk_access(self, d):
        fd, nm = tempfile.mkstemp(_T("file"), _T("test"), d)
        try:
            fp = os.fdopen(fd, _T("w"), 128)
        except OSError as e:
            _dbg(_T("space access X: {} '{}'").format(
                                                e.errno, e.strerror))
            raise e
        except Exception as e:
            _dbg(_T("space access X: '{}'").format(e))
            self._raise(e.errno, e.strerror)
        fp.write(_T("This test file should not exist unless error"))
        fp.flush()
        fp.close()
        os.unlink(nm)
        return True

    def _raise(self, e, s):
        raise self.__class__._internal_except(e, s)

    class _internal_except(Exception):
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

    def try_statvfs(self):
        roks = []
        errs = []

        for d in self.chks:
            try:
                v = os.statvfs(d)
                sd = StructDfData(
                    blocks_total = v.f_blocks,
                    blocks_avail = v.f_bavail,
                    size_of_block = v.f_frsize
                )
                roks.append((d, sd))
            except OSError as e:
                self.error = (e.errno, e.strerror)
                errs.append(d, e.strerror)
            except:
                self.error = (0, _("unknown error"))
                errs.append(d, _("unknown error"))

        return (roks, errs)

    def get_results(self):
        return (self.roks, self.errs)

    def go(self, try_statvfs = True):
        if try_statvfs:
            roks, errs = self.try_statvfs()
            if len(roks) > 0:
                self.roks += roks
                self.errs += errs
                return True

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


# testing
if __name__ == '__main__':
    import sys

    dirs = sys.argv[1:] if len(sys.argv) > 1 else ["/tmp"]

    chk = FsDirSpaceCheck(dirs)

    r_chk = chk.go(False)

    r_ok, r_ng = chk.get_results()

    if not r_chk:
        e, s = chk.error
        msg_line_ERROR(_(
            "Failed: {s} ({n}) -- "
            "{ne} err, {ok} good").format(
                n = e, s = s, ne = len(r_ng), ok = len(r_ok)))

    for (d, m) in r_ng:
        msg_line_ERROR(_(
            "df error on {d} '{m}'").format(d = d, m = m))

    res = []
    for (d, r) in r_ok:
        if r.blocks_avail() >= 0:
            msg_line_INFO(_("{0} has {1} blocks size {2}").format(
                d, r.blocks_avail(), r.size_of_block()))
            res.append((d, r))

    if len(res) > 0:
        exit(0)
    exit(1)
