# CPRec

This package contains two command line tool programs -- the namesake
'cprec' and 'dd-dvd' -- and a graphical front-end to those tools called
'wxDVDBackup'.  These tools are for Unix-like systems, and have
been tested and used on various GNU/Linux distributions, on
{Free,Net,Open}BSD, and on Open{Solaris,Indiana}.  These tools are
helpers for making a backup of a DVD video disc.

The cprec and dd-dvd tools should be useful to those accustomed to
working at the command line and developing their own procedures
for accomplishing a task.  Manual pages cprec(1) and dd-dvd(1)
are installed.

The front-end wxDVDBackup should be easy and convenient to use,
particularly for those willing to spend a few moments examining the
interface, as there are several detailed ``tool-tips''.

## __cprec__

This program names the package simply because it was written first.
The odd name should evoke "CoPy RECusrsively".  The DVD must be
mounted, and the mount point given as an argument.

This is useful if you would like to add additional files to your
backup.  For example, for a favorite DVD you might like to add
images, web pages and research, or what have you (being careful,
of course, not exceed the capacity of the target writable disc).

To build, a C compiler is required.

The __DVDRead__ library (libdvdread) is required (and libdvdcss
if you backup a css encrypted DVD).

On success, the output directory hierarchy may be burned to a
writable DVD blank with __growisofs__.

## __dd-dvd__

This program's name should evoke "Data Duplicate DVD".  The DVD
may be mounted, but needn't be and a device node may be given
rather than a mount point.

This makes a straightforward backup, copying data via libdvdread
where needed.

To build, a C++ compiler is required.

The __DVDRead__ library (libdvdread) is required (and libdvdcss
if you backup a css encrypted DVD).

Note this is not designed for non-video DVD discs; Use dd(1) for
those.

On success, the output filesystem image may be burned to a
writable DVD blank with __growisofs__.

## __wxDVDBackup__

This graphical interface program, which requires __wxPython__ (or
the resurrected __wxPhoenix__), should make the backup process
easy, and covers intermediate tasks such as checking the capacity
of a target disc or blanking a written re-writable disc (after a
prompt).  It then provides the disc burning with __growisofs__.

It provides the two backup types (cprec or dd-dvd).  The interface
elements have 'tooltips' that appear when the mouse pointer is
paused over an element, and hopefully this will be sufficient
to learn the program's use.

The __growisofs__ program is required, and also the associated
programs dvd+rw-mediainfo(1) and dvd+rw-format(1) (those three
programs should be in the same package from your OS package
management system).  Also, mkisofs or genisoimage are required.

## Experimental feature

Both cprec and dd-dvd (and therefore wxDVDBackup) will, by default,
attempt to handle read failures by writing zeros (in the amount of
the failed read, of course).  This experimental feature is optional,
and can be controlled by command-line parameters (or from a settings
dialog in the graphical front end).  Control parameters are described
in the manual pages cprec(1) and dd-dvd(1).

The author has found that these backups, with unexpected zeroed data,
play fine in set-top players.  Usually, there is no noticable glitch.

It might be expected that a player's code could be confused by
unexpected zeroed blocks, but the author has played these discs
in several set-top players from several manufacturers, and has
not found any to be problematic.  Of course, you might have
different results.

This feature has been useful to the author quite often (even brand new
commercial discs sometimes have defects).

One caveat: this feature is on by default, triggered by read errors,
and while working with default settings will be time consuming and
hard on the drive.  See the manual pages for parameters that will
spare time and drive abuse (i.e. fewer retries and larger block read
counts, or disabling).

## Build Configuration

Detailed configration notes are in the file 'INSTALL'.

## Author

Ed Hynan, ehynan@gmail.com

