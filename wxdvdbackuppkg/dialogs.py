# coding=utf-8
"""
The application dialog window classes.
"""

import wx

import __init__
from chars import *
from msgprocs import *
from debug import pdbg

_dbg = pdbg

class ASettingsDialog(wx.Dialog):
    """
    A dialog box for settings
    using a tabbed interface for settings sections/groups
    """
    def __init__(self,
            parent, ID, gist,
            title = _("Application Settings"),
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


    def on_sys_color(self, event):
        event.Skip()

        f = lambda wnd: self._color_proc_per_child(wnd)
        invoke_proc_for_window_children(self, f)

    #private
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
            blr = wx.RIGHT # | wx.LEFT

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
