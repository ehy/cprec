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
DVD Backup frontend for cprec and dd-dvd, growisofs, genisoimage/mkisofs
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
import signal
import stat
import string
import sys
import tempfile
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
try:
    import wx.lib.agw.multidirdialog as MDD
except:
    pass
# end from wxPython samples

# packaged code specific to this app:
#from wxdvdbackuppkg import *
from wxdvdbackuppkg.chars import *
import wxdvdbackuppkg.fp_write
import wxdvdbackuppkg.debug
from wxdvdbackuppkg.msgprocs import *
from wxdvdbackuppkg.util import *
from wxdvdbackuppkg.globaldata import *
from wxdvdbackuppkg.childproc import *
from wxdvdbackuppkg.tmpdirschk import TempDirsCheck
import wxdvdbackuppkg.media
from wxdvdbackuppkg.appthreads import *
from wxdvdbackuppkg.dialogs import ASettingsDialog

_dbg = wxdvdbackuppkg.debug.pdbg
fp_write = wxdvdbackuppkg.fp_write.fp_write
MediaDrive = wxdvdbackuppkg.media.MediaDrive
ASettingsDialog = wxdvdbackuppkg.dialogs.ASettingsDialog


"""
    Global procedures
"""

PROGPATH = os.path.split(sys.argv[0])
PROGLONG = _T(PROGPATH[1])
PROG = PROGLONG
def _mk_PROG():
    try:
        tr = PROGLONG.rindex(_T(".py"))
    except:
        tr = len(PROGLONG)

    global PROG
    PROG = PROGLONG[:tr]

_mk_PROG()

"""
    Development hacks^Wsupport
"""

if "-XGETTEXT" in sys.argv:
    try:
        # argv[0] is unreliable, but this is not for general use.
        _xgt = "xgettext"
        _xgtargs = [_xgt, "-o", "-", "-L", "Python",
                "--keyword=_", "--add-comments",
                "{0}/{1}.py".format(PROGPATH[0], PROG)]
        try:
            import glob
            _xgtargs += glob.glob(
                "{0}/wxdvdbackuppkg/*.py".format(PROGPATH[0]))
        except Exception as m:
            sys.stderr.write(
                "COULD NOT GLOB THE PACKAGE DEAR^WDIR:\n{0}\n".format(
                m))
        except:
            sys.stderr.write("COULD NOT GLOB THE PACKAGE DEAR^WDIR!\n")
        os.execvp(_xgt, _xgtargs)
    except OSError as e:
        sys.stderr.write("Exec {0} {p}: {1} ({2})\n".format(
            _xgt, e.strerror, e.errno, p = sys.argv[0]))
        exit(1)


if "-DBG" in sys.argv:
    _ofd, _fdbg_name = tempfile.mkstemp(".dbg", "_DBG_wxDVDBackup-")
    if wxdvdbackuppkg.debug.dbg_open(_fdbg_name, _ofd):
        _dbg(_T("debug file opened"))

"""
    Global data
"""

# version globals: r/o
version_string = _T("0.4.1")
version_name   = _("Serpent Lake")
version_mjr    = 0
version_mjrrev = 4
version_mnr    = 1
version_mnrrev = 0
version = (
    version_mjr<<24|version_mjrrev<<16|version_mnr<<8|version_mnrrev)
maintainer_name = _T("Ed Hynan")
maintainer_addr = _T("<edhynan@gmail.com>")
copyright_years = _T("2016")
program_site    = _T("https://github.com/ehy/cprec")
program_desc    = _T("Flexible backup for video DVD discs.")
program_devs    = [maintainer_name]


"""
    interface widget classes
"""

class RepairedMDDialog(MDD.MultiDirDialog):
    """
    RepairedMDDialog -- a multi-directory selection dialog, deriving
                        from wxPython:agw.MultiDirDialog to repair
                        broken GTK2 implementation of underlying
                        wxTreeCtrl by removing unwanted false items
                        "Home directory" etc. -- also repairs bug
                        in wxPython:agw.MultiDirDialog that returns
                        items under '/' prefixed with '//'.
                        Furthermore, parameter defaults are tuned
                        to my preferences.
    """
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


class AMsgWnd(wx.TextCtrl):
    """
    AMsgWnd -- a text output window to appear within the ASashWnd
    """
    def __init__(self, parent, id = -1, size = wx.DefaultSize):
        wx.TextCtrl.__init__(self,
            parent, id, _T(""), wx.DefaultPosition, size,
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

        set_msg_obj(self)
        set_msg_default_color(self.GetForegroundColour())

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

        bclr = self.GetBackgroundColour()
        fclr = self.GetForegroundColour()

        set_msg_default_color(fclr)

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



class AFileListCtrl(wx.ListCtrl, listmix.ColumnSorterMixin):
    """
    AFileListCtrl -- Control to display additional file/dir selections
    """
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


ABasePaneBase = scrollpanel.ScrolledPanel
#ABasePaneBase = wx.ScrolledWindow
class ABasePane(ABasePaneBase):
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
    """
    def __init__(self, parent, gist, wi, hi, id = -1):
        ABasePaneBase.__init__(self,
                        parent, id,
                        style = wx.CLIP_CHILDREN |
                                wx.FULL_REPAINT_ON_RESIZE |
                                wx.TAB_TRAVERSAL
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


    # AcceptsFocusRecursively: override C++ vitual func, return true:
    # this is needed with wx 3.x for tab traversal into child windows
    def AcceptsFocusRecursively(self):
        return True

    # All following *focus* methods:
    # for derived classes hacking focus behavior --
    # for passing tab-focus across sibling windows
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

    # For derived classes: add child to our list
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


class AVolInfPane(ABasePane):
    """
    AVolInfPane -- Pane window for operation target volume info fields setup
    """
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

class AVolInfPanePanel(wx.Panel):
    """
    AVolInfPanePanel -- Panel window for operation volume info fields setup
    """
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


class ATargetPane(ABasePane):
    """
    ATargetPane -- Pane window for operation target setup
    """
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


class ATargetPanePanel(wx.Panel):
    """
    ATargetPanePanel -- Pane window for operation target setup
    """
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



class ASourcePane(ABasePane):
    """
    ASourcePane -- Pane window for operation source setup
    """
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

class ASourcePanePanel(wx.Panel):
    """
    ASourcePanePanel -- Pane window for operation source setup
    """
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


class AProgBarPanel(wx.Panel):
    """
    AProgBarPanel -- small class for wxGauge progress bar
    """
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


class AChildSashWnd(wx.SplitterWindow):
    """
    AChildSashWnd -- adjustable child of adjustable child of top frame
                     see ASashWnd class below
    """
    def __init__(self, parent, sz, logobj, ID, title, gist):
        wx.SplitterWindow.__init__(self, parent, ID,
            style = wx.SP_3D)

        self.core_ld = gist

        self.pane_minw = 40
        pane_width = sz.width / 2

        w_adj = 20
        h_adj = 40
        self.child1_maxw = pane_width
        self.child1_maxh = sz.height

        self.child2_maxw = pane_width
        self.child2_maxh = sz.height

        self.child1 = ASourcePane(
            self, gist,
            self.child1_maxw - w_adj, self.child1_maxh - h_adj,
            id = gist.get_new_idval()
            )
        self.child2 = ATargetPane(
            self, gist,
            self.child2_maxw - w_adj, self.child2_maxh - h_adj,
            id = gist.get_new_idval()
            )

        self.child1.set_focus_partner_fore(self.child2)
        self.child1.set_focus_partner_back(self.child2)

        self.child2.set_focus_partner_fore(self.child1)
        self.child2.set_focus_partner_back(self.child1)

        self.child1.take_focus()

        self.SplitVertically(self.child1, self.child2, pane_width)
        self.SetMinimumPaneSize(self.pane_minw)
        self.SetSashPosition(pane_width, True)

        self.Bind(wx.EVT_SIZE, self.OnSize)


    # Call once only, after ctor completes, so that parent may
    # treat children, knowing they are created.
    def post_contruct(self):
        self.SetThemeEnabled(True)
        self.child1.init_for_children()
        self.child1.init_for_children()

    def OnSize(self, event):
        self.UpdateSize()

    def get_msg_obj(self):
        return self.swnd[1].get_msg_obj()


class ASashWnd(wx.SplitterWindow):
    """
    ASashWnd -- adjustable child of top frame
    """
    def __init__(self, parent, ID, title, gist,
                       init_build = True, size = (800, 600)):
        wx.SplitterWindow.__init__(self, parent, ID,
            name = title, size = size, style = wx.SP_3D)

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

        sz = self.GetClientSize()
        top_ht = sz.height - 130

        sz1 = wx.Size(sz.width, top_ht)
        self.child1 = AChildSashWnd(
            self, sz1, parent, gist.get_new_idval(),
            _T("Source and Destination"), gist)
        self.child2 = AMsgWnd(self,
            size = wx.DefaultSize, id = gist.get_new_idval())

        self.core_ld.set_msg_wnd(self.child2)
        self.child2.set_scroll_to_end(True)

        self.SplitHorizontally(self.child1, self.child2, top_ht)
        self.SetMinimumPaneSize(20)
        self.SetSashPosition(top_ht, True)

        self.Bind(wx.EVT_SIZE, self.OnSize)


    # Call once only, after ctor completes, so that parent may
    # treat children, knowing they are created.
    def post_contruct(self):
        self.SetThemeEnabled(True)
        self.child1.post_contruct()

    def OnSize(self, event):
        self.UpdateSize()
        self.child2.conditional_scroll_adjust()

    def get_msg_obj(self):
        return self.child2



"""
    dialogs and main window
"""


class AFrame(wx.Frame):
    """
    top/main frame window class
    """
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
            self, gist.get_new_idval(), gist,
            title = _("{appname} Settings").format(appname = PROG)
            )

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

            lic = licence_data
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




class ACoreLogiDat:
    """
    The gist of it: much of the code in this file concerns
    GUI setup and logic -- that's unavoidable -- but the GUI
    classes should have little or no general logic, most of
    which goes here (other than support classes).
    This will also manage interaction among GUI elements
    in areas that would require GUI classes to know too much
    about and have references to other GUI classes; so this will
    keep ref's to some GUI objects, be passed to GUI c'tors,
    and provide a few (er, many) procedures.
    """
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

        # child proc handled by new thread -- refs thread
        self.ch_thread = None
        # child proc handled in main thread -- refs child proc object
        self.ch_syncro = None

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

    def get_child_sync(self):
        return self.ch_syncro

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
        self, outdev, wait_retry, settle_time = 5,
        blank_async = False, verbose= False):

        settle_tries = wait_retry

        while True:
            r = self.do_target_medium_check(outdev, settle_tries)
            if r == None:
                break

            if r:
                r = self.do_in_out_size_check(blank_async, verbose)

            if r:
                return True

            if settle_tries < 1 and self.get_is_dev_direct_target():
                break

            if settle_tries < 1:
                m = _("Target medium check failed. Try another disc?"
                    "\nIf yes, change disc before clicking 'yes'.")

                r = self.dialog(m, _T("yesno"), wx.YES_NO)
                if r != wx.YES:
                    break

                settle_tries = wait_retry
                continue

            msg_line_WARN(_(
                "target medium checked failed; will sleep "
                "{secs} more seconds, then try again "
                "({tries} more retries)"
                ).format(secs = settle_time, tries = settle_tries))

            settle_tries -= 1

            wx.GetApp().Yield(True)

            t = time.time()
            wx.Sleep(settle_time)
            t = time.time() - t
            t = int(t + 0.5)
            msg_line_INFO(
                _("Slept {secs} to let drive settle.").format(secs = t))


        return False

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

        self.do_target_check(
            target_dev, async_blank, reset, settle_tries, settle_time)

        if self.checked_output_devnode:
            return True

        return False


    # general check of target, including medium as necessary
    # param retry_num affects warn/error messages: should be
    # verbose only on the last try (retry_num == 0)
    def do_target_check(self,
                        target_dev = None,
                        async_blank = False,
                        reset = False,
                        retry_num = 0, settle_time = 5):
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
                if self.check_target_prompt(
                    target_dev, retry_num, settle_time):
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

        e = AThreadEvent(_T("l%d") % n, s, self.topwnd_id)
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
                m = _("Ready to burn backup. "
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

        if verbose: # or True:
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
        else:
            ch = self.get_child_sync()
            if ch:
                self.ch_syncro = None
                ch.kill(signal.SIGUSR1)
                ch.wait()

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

        self.ch_syncro = ch_proc
        is_ok = ch_proc.go_and_read()
        if not self.ch_syncro:
            # cancelled
            return False
        self.ch_syncro = None

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

        if retry_num > 0:
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

        self.ch_syncro = ch_proc
        is_ok = ch_proc.go_and_read()
        if not self.ch_syncro:
            # cancelled -- Note: return is None rather than False
            return None
        self.ch_syncro = None

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

        self.ch_syncro = ch_proc
        is_ok = ch_proc.go_and_read()
        if not self.ch_syncro:
            # cancelled
            return False
        self.ch_syncro = None

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
    """
    The wx application object class
    """
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


if __name__ == '__main__':
    app = TheAppClass(0)
    app.MainLoop()

