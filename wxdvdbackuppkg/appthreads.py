# coding=utf-8
"""
Thread and related classes.
"""

import os
import select
import threading
import time
import wx

#import __init__
from .chars import *
from .msgprocs import *
from .debug import pdbg

_dbg = pdbg

"""
    classes for threads --

    NOTE: testing suggests that the event delivery is picky, as follows:
    *   wx.PyCommandEvent will not be delivered to the application
        object; wx.PyEvent will
    *   wx.PyEvent will not be delivered to the top frame window, at
        least not after Window::Show(false) is called
    therefore be thought full about which (sub-)class to choose,
    according to delivery target type
"""

T_EVT_CHILDPROC_MESSAGE = wx.NewEventType()
EVT_CHILDPROC_MESSAGE = wx.PyEventBinder(T_EVT_CHILDPROC_MESSAGE, 1)
class AThreadEvent(wx.PyEvent):
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
    def __init__(self, evttag, payload = None, destid = -1):
        wx.PyEvent.__init__(
            self, destid,
            T_EVT_CHILDPROC_MESSAGE)

        self.ev_type = evttag
        self.ev_data = payload

    def get_content(self):
        """on receipt, get_content() may be called on the event
        object to return a tuple with the event type tag at [0]
        and any data payload (by default None) at [1]
        """
        return (self.ev_type, self.ev_data)

class AThreadCommandEvent(wx.PyCommandEvent):
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
    def __init__(self, evttag, payload = None, destid = -1):
        wx.PyCommandEvent.__init__(
            self, destid,
            T_EVT_CHILDPROC_MESSAGE)

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
    def __init__(self, destobj, destid, cb, args):
        threading.Thread.__init__(self)

        self.destobj = destobj
        self.destid = destid
        self.cb = cb
        self.args = args

        self.status = -1
        self.got_quit = False

        self.per_th = APeriodThread(destobj, destid)

    def run(self):
        tid = threading.current_thread().ident
        t = _T("tid {tid}").format(tid = tid)
        self.per_th.start()

        m = _T('enter run')
        wx.CallAfter(wx.PostEvent,
            self.destobj, AThreadEvent(m, t, self.destid))

        r = self.cb(self.args)
        self.status = r
        self.per_th.do_stop()
        while self.per_th.is_alive():
            self.per_th.join()

        if self.got_quit:
            return

        m = _T('exit run')
        wx.CallAfter(wx.PostEvent,
            self.destobj, AThreadEvent(m, t, self.destid))

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

    def __init__(self, destobj, destid, interval = 1, msg = None):
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

        self.destobj = destobj
        self.destid = destid
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
        wx.CallAfter(wx.PostEvent,
            self.destobj, AThreadEvent(m, payload, self.destid))

    def do_stop(self):
        self.got_stop = True

