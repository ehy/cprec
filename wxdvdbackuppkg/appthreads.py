# coding=utf-8
"""
Thread and related classes.
"""

import os
import select
import threading
import wx

import __init__
from chars import *
from msgprocs import *
from debug import pdbg

_dbg = pdbg

"""
    classes for threads
"""

T_EVT_CHILDPROC_MESSAGE = wx.NewEventType()
EVT_CHILDPROC_MESSAGE = wx.PyEventBinder(T_EVT_CHILDPROC_MESSAGE, 1)
class AThreadEvent(wx.PyCommandEvent):
    """A custom event for the wxWidgets event mechanism:
    thread safe, i.e. may pass to main thread from other threads
    (which is particularly useful to initiate anything that will
    update the GUI, which must be done in the main thread with
    wxWidgets).  The evttag argument to the constructor *must*
    be passed (it associates the event with a type), and the
    payload argument *may* be passed if the event should carry
    a message or some data (but be mindful of threading issues),
    and finally the event will by default be delivered to the
    main top window, but a different window id may be given
    in the destid argument.
    """
    def __init__(self, evttag, payload = None, destid = None):
        if destid == None:
            destid = wx.GetApp().GetTopWindow().GetId()

        wx.PyCommandEvent.__init__(
            self,
            T_EVT_CHILDPROC_MESSAGE,
            destid)

        self.ev_type = evttag
        self.ev_data = payload

    def get_content(self):
        """on receipt, get_content() may be called on the event
        object to return a tuple with the event type tag at [0]
        and any data payload (by default None) at [1]
        """
        return (self.ev_type, self.ev_data)

class AChildThread(threading.Thread):
    """
    A thread for time consuming child process --
    cb is a callback, args is/are arguments to pass
    """
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
        wx.PostEvent(self.topwnd, AThreadEvent(m, t, self.destid))

        r = self.cb(self.args)
        self.status = r
        self.per_th.do_stop()
        if self.got_quit:
            return

        self.per_th.join()

        m = _T('exit run')
        wx.PostEvent(self.topwnd, AThreadEvent(m, t, self.destid))

    def get_status(self):
        return self.status

    def get_args(self):
        return self.args

    def set_quit(self):
        self.got_quit = True
        self.per_th.do_stop()


class APeriodThread(threading.Thread):
    """
    A thread for posting an event at intervals --
    """
    th_sleep_ok = (_T("FreeBSD"), _T("OpenBSD"))

    def __init__(self, topwnd, destwnd_id, interval = 1, msg = None):
        """
        OS unames I feel good about sleep in thread; {Free,Open}BSD
        implement sleep() with nanosleep)() and don't diddle signals,
        NetBSD and Linux use SIGALRM says manual -- others unknown --
        use of python's time.sleep() vs. the others here is not
        inconsequential: the others are causing yet another thread
        to be created (by python, not here), and sleep is not.
        Of course, python time.sleep() is not just a wrapped call
        of libc sleep(3); in fact it will take a float argument.
        """
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
            self.topwnd, AThreadEvent(m, payload, self.destid))

    def do_stop(self):
        self.got_stop = True

