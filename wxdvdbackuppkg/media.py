# coding=utf-8
"""Classes for DVD media"""

import re

from chars import *

class MediaDrive:
    """
    class to get wanted data from verbose output of "dvd+rw-mediainfo"
    -- a utility from dvd+rw-tools, along with growisofs -- feed lines
    to rx_add() method, get data items with get_data_item(key) (see
    class def for keys) or whole map with get_data()
    """
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
        for k in self.__class__.regx:
            m = self.__class__.regx[k].match(lin)
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


# testing
if __name__ == '__main__':
    import sys
    import childproc
    import msgprocs

    def get_stat_data_line(line, ch_proc):
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


    # pointless names here; was cut&paste
    pr_GOOD = msgprocs.msg_line_GOOD
    pr_INFO = msgprocs.msg_line_INFO
    pr_WARN = msgprocs.msg_line_WARN
    pr_ERR  = msgprocs.msg_line_ERROR
    ms_GOOD = msgprocs.msg_GOOD
    ms_INFO = msgprocs.msg_INFO
    ms_WARN = msgprocs.msg_WARN
    ms_ERR  = msgprocs.msg_ERROR

    target_dev = sys.argv[1] if len(sys.argv) > 1 else "/dev/dvd"

    xcmd = _T('dvd+rw-mediainfo')
    xcmdargs = []
    xcmdargs.append(xcmd)
    xcmdargs.append(target_dev)
    xcmdenv = []

    m = _("Checking {0} with {1}").format(target_dev, xcmd)
    pr_WARN(m)

    parm_obj = childproc.ChildProcParams(xcmd, xcmdargs, xcmdenv)
    ch_proc = childproc.ChildTwoStreamReader(parm_obj)

    is_ok = ch_proc.go_and_read()

    if not is_ok:
        m = _("Failed media check of {0} with {1}"
            ).format(target_dev, xcmd)
        pr_ERR(m)
        exit(1)

    ch_proc.wait()
    is_ok, is_sig = ch_proc.get_status()
    rlin1, rlin2, rlinx = ch_proc.get_read_lists()

    m = _T("")
    for l in rlinx:
        ok, l, dat = get_stat_data_line(l, ch_proc)
        if ok:
            m = _T("X: {pre}\n{lin} ").format(pre = m, lin = l)
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

    l1, l2, lx = ch_proc.get_read_lists()
    target_data = MediaDrive(target_dev)

    for lin in l2:
        lin = lin.rstrip()
        target_data.rx_add(lin)
        pr_WARN(_T("L2: ") + lin)

    e = target_data.get_data_item(_T("presence"))
    if e:
        m = _(
            "Failed: {0} says \"{1}\" for {2}"
            ).format(xcmd, e, target_dev)
        pr_ERR(m)
        exit(2)

    for lin in l1:
        lin = lin.rstrip()
        target_data.rx_add(lin)
        if is_ok:
            pr_GOOD(_T("L1, OK: ") + lin)
        else:
            pr_ERR(_T("L1, NG: ") + lin)

    if not is_ok:
        exit(3)
    else:
        checked_media_blocks = target_data.get_data_item(
            _T("medium freespace"))
        pr_INFO(_("Medium free blocks: {0}").format(
            checked_media_blocks))

    exit(0)
