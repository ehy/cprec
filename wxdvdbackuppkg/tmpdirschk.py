# coding=utf-8
"""
Get sorted list of suitable temprorary directories.
"""

import errno
import os
import sys
import tempfile

import __init__
from chars import *
from msgprocs import *
from debug import pdbg
from util import *
from fsdirspace import FsDirSpaceCheck

_dbg = pdbg

class TempDirsCheck:
    """
    Check for temp directories with sufficient available space,
    make sorted result available
    """
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
                bla = r.blocks_avail()
                bls = r.size_of_block()
                imx = sys.maxsize / bls

                if bls < 1:
                    #paranoia
                    continue

                if bls != 1024:
                    if imx >= bla:
                        bla *= bls
                        bla /= 1024
                    else:
                        bla /= 1024
                        if bla <= imx:
                            bla *= bls
                        else:
                            # result too big -- should not happen
                            # TODO: some indication of this occurance
                            continue
                if bla >= self.min_space:
                    res.append((d, r))
                elif False:
                    m = _("{d} has {a} blocks -- {m} needed")
                    msg_line_WARN(m.format(d=d,a=bla,m=self.min_space))
                    m = _("orig: {a} blocks of {s} bytes")
                    msg_line_WARN(m.format(
                        a=r.blocks_avail(),s=r.size_of_block()))

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


# testing
if __name__ == '__main__':
    addl = sys.argv[1:] if len(sys.argv) > 1 else []

    chk = TempDirsCheck(
        use_env = True, use_def = True, min_space = 8400000,
        use_mod_tempfile = True, do_expand = True, addl_dirs = addl,
        sort_type = "big" # "small" or "none"
        )

    res = chk.do()
    err = chk.get_error()

    if err:
        msg_line_WARN(_("directory errors:\n") + err)

    if not res:
        msg_line_WARN(_(
            "Cannot find a directory with enough available "
            "space for temporary data!"))
        exit(69)

    if res:
        for (d, r) in res:
            # count in 2048 byte blocks
            bcnt = (r.blocks_avail() * r.size_of_block()) >> 11
            msg_line_INFO(_(
                "dir '{d}' has {cnt} DVD-size blocks free").format(
                    d = d, cnt = bcnt))

    exit(0)
