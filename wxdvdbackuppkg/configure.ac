dnl Process this file with autoconf to produce a configure script.

dnl Every other copy of the package version number gets its value from here
AC_INIT([wxdvdbackuppkg], [0.0.1])

AM_INIT_AUTOMAKE([])

dnl options below, for dd-dvd and wxpy-frontend, are present merely
dnl to {in,ex}clude installation of this package in Makefile.am --
dnl this repeats logic in top level configure.ac; I do not know a
dnl better way.

dnl dd-dvd made optional
AC_ARG_ENABLE([dd-dvd],
	AS_HELP_STRING([--disable-dd-dvd],
		 [do not build dd-dvd, the simple dvd filesystem backup program (C++)]),
	[case "${enableval}" in
	yes) enable_dd_dvd=true ;;
	no)  enable_dd_dvd=false ;;
	*) AC_MSG_ERROR([bad value ${enableval} for --enable-dd-dvd]) ;;
	esac],[enable_dd_dvd=true])
AM_CONDITIONAL([WITH_DD_DVD], [test x$enable_dd_dvd = xtrue])

dnl Version 0.2.1, wxPython front end
AC_ARG_ENABLE([wxpy-frontend],
	AS_HELP_STRING([--disable-wxpy-frontend],
		 [do not install the wxPython graphical backup frontend program:
          requires Python 2.7 (not 3.x), wxPython, growisofs, dvd+rw-mediainfo,
          dvd+rw-format (the latter three from the same package "dvd+rw-tools"
          or maybe "growisofs"), genisoimage or mkisofs, and cprec and dd-dvd
          from this package (--disable-dd-dvd will disable this frontend
          application too)
         ]),
	[case "${enableval}" in
	yes) enable_frontend=true ;;
	no)  enable_frontend=false ;;
	*) AC_MSG_ERROR([bad value ${enableval} for --enable-wxpy-frontend]) ;;
	esac],[enable_frontend=true])
AM_CONDITIONAL([WITH_FRONTEND], [test x$enable_frontend = xtrue])

if test x"$enable_frontend" = xtrue; then
AM_PATH_PYTHON([2.7],, [:])
AC_CONFIG_LINKS([__init__.py:__init__.py])
AC_CONFIG_LINKS(appthreads.py:appthreads.py)
AC_CONFIG_LINKS(chars.py:chars.py)
AC_CONFIG_LINKS(childproc.py:childproc.py)
AC_CONFIG_LINKS(debug.py:debug.py)
AC_CONFIG_LINKS(dialogs.py:dialogs.py)
AC_CONFIG_LINKS(fp_write.py:fp_write.py)
AC_CONFIG_LINKS(fsdirspace.py:fsdirspace.py)
AC_CONFIG_LINKS(globaldata.py:globaldata.py)
AC_CONFIG_LINKS(media.py:media.py)
AC_CONFIG_LINKS(msgprocs.py:msgprocs.py)
AC_CONFIG_LINKS(tmpdirschk.py:tmpdirschk.py)
AC_CONFIG_LINKS(util.py:util.py)
dnl AC_CONFIG_LINKS(tasks.py:tasks.py)
dnl template for new additions:
dnl AC_CONFIG_LINKS(.py:.py)
fi

#AC_OUTPUT
AC_OUTPUT([Makefile])
