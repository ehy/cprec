# coding=utf-8
"""
Message procedure: print on sys.std* until GUI object is set,
then use that.
"""

import sys
import wx

import __init__
from chars import *
import fp_write
from debug import pdbg

_fp_write = fp_write.fp_write
_dbg = pdbg

# Make some global message procedures -- initial output to file, and
# output to GUI object after GUI setup.
msg_red_color = wx.RED
msg_green_color = wx.Colour(0, 227, 0)
msg_blue_color = wx.BLUE
#msg_yellow_color = wx.Colour(227, 227, 0)
msg_yellow_color = wx.Colour(202, 145, 42)
msg_default_color = wx.BLACK

# refs to GUI message objects for message procs (above).
_msg_obj = None
_msg_obj_init_is_done = False

def set_msg_obj(obj = None):
    global _msg_obj
    global _msg_obj_init_is_done
    if obj:
        _msg_obj_init_is_done = True
        _msg_obj = obj
    else:
        _msg_obj_init_is_done = False
        _msg_obj = None

def set_msg_default_color(clr = None):
    global msg_default_color
    if clr:
        msg_default_color = wx.BLACK
    else:
        msg_default_color = clr

def msg_(msg, clr = None):
    if _msg_obj_init_is_done == True:
        if clr == None:
            _msg_obj.AppendTextColored(msg, msg_default_color)
        else:
            _msg_obj.AppendTextColored(msg, clr)
    else:
        _fp_write(sys.stdout, msg)

def err_(msg, clr = None):
    _dbg(msg)
    if _msg_obj_init_is_done == True:
        if clr == None:
            _msg_obj.AppendTextColored(msg, msg_red_color)
        else:
            _msg_obj.AppendTextColored(msg, clr)
    else:
        _fp_write(sys.stderr, msg)

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


def msg_line_(msg, clr = None):
    if _msg_obj_init_is_done == True:
        msg_(_T("\n") + msg, clr)
    else:
        msg_(msg + _T("\n"), clr)

def err_line_(msg, clr = None):
    m = _T("{0}: {1}").format(PROG, msg)
    if _msg_obj_init_is_done == True:
        err_(_T("\n") + m, clr)
        _fp_write(sys.stderr, m + _T("\n"))
    else:
        err_(m + _T("\n"), clr)

def msg_line_red(msg):
    msg_line_(msg, msg_red_color)

def msg_line_green(msg):
    msg_line_(msg, msg_green_color)

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

