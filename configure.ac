dnl Process this file with autoconf to produce a configure script.

dnl Every other copy of the package version number gets its value from here
AC_INIT([cprec], [0.1.2])
AM_INIT_AUTOMAKE([-Wall -Werror])

dnl create a config.h file (Automake will add -DHAVE_CONFIG_H)
AM_CONFIG_HEADER(config.h)

AC_SUBST(VERSION)

ISODATE=`date +%Y-%m-%d`
AC_SUBST(ISODATE)

dnl We want these before the checks, so the checks can modify their values.
dnl (found in fetchmail configure.in)
test x"$CFLAGS" = x && CFLAGS="-O"; AC_SUBST(CFLAGS)
test x"$CXXFLAGS" = x && CXXFLAGS="-O"; AC_SUBST(CXXFLAGS)
dnl test x"$LDFLAGS" = x && LDFLAGS=-s; AC_SUBST(LDFLAGS)

AC_CANONICAL_HOST

dnl Ensure use of large file support
AC_SYS_LARGEFILE
dnl Check file names
AC_SYS_LONG_FILE_NAMES

dnl arg to allow disabling of linking libdvdread
AC_ARG_WITH([libdvdread], AS_HELP_STRING([--with-libdvdread],
  [try to link -ldvdread (the better default is to try dynamic loading)]),,
  [with_libdvdread=no])

dnl dd-dvd only if requested
AC_ARG_ENABLE([dd-dvd], AS_HELP_STRING([--enable-dd-dvd],
  [try to build the dd-dvd program which requires C++ and uses libdvdread functions that might not be public in the shared library]),,
  [enable_dd_dvd=no])

dnl dd-dvd only if requested
AS_IF([test x"$enable_dd_dvd" != xno],
[
AM_CONDITIONAL(WITH_DD_DVD, true)
AC_DEFINE(WITH_DD_DVD,[],[Enabled dd-dvd])
], [
AM_CONDITIONAL(WITH_DD_DVD, false)
])

dnl Checks for programs.
AC_PROG_INSTALL
AC_PROG_CC
AC_PROG_CXX
AC_C_INLINE

dnl Checks for libraries.
# libdvdread check
if test x"$with_libdvdread" = xyes; then
# libdvdread enabled
#  Now it gets ugly^Hier. Many OS's might offer dvdread with a 3rd party
#  package system, but the installation directories might not be in
#  the default search path of the compiler and linker. Or it might be
#  'hand' installed anywhere. But it must be found. There seems to be
#  no autoconf magic for this, and all the 'googling' I could stand was
#  little help. Therefore shell script is resorted to.
#
_search_hack_prefix_list="/usr/local /opt/local /opt /usr/pkg"
_search_hack_headers_list="include/dvdread/dvd_reader.h"
_search_hack_libraries_list="lib/libdvdread.so lib/libdvdread.a"

for _search_hack_prefix in $_search_hack_prefix_list
do
  for _search_hack_var in $_search_hack_headers_list
  do
    if test -f "${_search_hack_prefix}/${_search_hack_var}"
    then
    	_search_hack_header="${_search_hack_prefix}/${_search_hack_var}"
	break
    fi
  done
  if test X"$_search_hack_header" != X
  then
    CFLAGS="$CFLAGS -I${_search_hack_prefix}/include"
    CXXFLAGS="$CXXFLAGS -I${_search_hack_prefix}/include"
    break
  fi
done

for _search_hack_prefix in $_search_hack_prefix_list
do
  for _search_hack_var in $_search_hack_libraries_list
  do
    if test -f "${_search_hack_prefix}/${_search_hack_var}"
    then
    	_search_hack_library="${_search_hack_prefix}/${_search_hack_var}"
	break
    fi
  done
  if test X"$_search_hack_library" != X
  then
    LDFLAGS="$LDFLAGS -L${_search_hack_prefix}/lib"
    break
  fi
done

AC_CHECK_LIB(dvdread, DVDVersion, AC_DEFINE([HAVE_DVDVERSION], [1], ["Got DVDVersion"]))
AC_CHECK_LIB(dvdread, DVDReadBlocks,, AC_CHECK_LIB(dl, dlsym))
else
# libdvdread not enabled
if test x"$with_libdvdread" = x || test x"$with_libdvdread" = xno; then
AC_MSG_NOTICE(Skipping check for libdvdread: --with-libdvdread not given)
AC_CHECK_LIB(dl, dlsym)
else
#  Here user has given a specific library argument; will assume such a user
#  will have set -I and -L as necessary.
AC_MSG_NOTICE(Skipping check for libdvdread: using --with-libdvdread=ARG)
LIBS="$with_libdvdread $LIBS"
AC_DEFINE([HAVE_LIBDVDREAD], [1])
fi
fi
# end libdvdread check

dnl Checks for header files.
AC_HEADER_STDC
AC_HEADER_DIRENT
AC_CHECK_HEADERS(unistd.h sys/param.h sys/time.h time.h sys/mkdev.h sys/sysmacros.h string.h memory.h fcntl.h dirent.h sys/ndir.h ndir.h alloca.h locale.h error.h errno.h limits.h sys/resource.h ctype.h stdarg.h varargs.h dlfcn.h)

dnl  this jm_* was provided by an older autogen, and now causes
dnl  warning noise with newer auto* tools: do without it and watch
dnl  for reports from any old system users
dnl jm_CHECK_TYPE_STRUCT_UTIMBUF

AC_HEADER_MAJOR
AC_STRUCT_TM
AC_STRUCT_ST_BLOCKS
AC_FUNC_ALLOCA
AC_FUNC_FSEEKO
AC_FUNC_CLOSEDIR_VOID
AC_CHECK_FUNCS(mkfifo vprintf doprnt seekdir telldir getrlimit pathconf getpagesize sysconf strlcpy mmap lstat readlink symlink lchown lchmod lutimes utimes error dlsym posix_memalign)
AC_CHECK_FUNC(mknod)

dnl Checks for typedefs, structures, and compiler characteristics.
AC_C_CONST
AC_TYPE_SIZE_T
AC_TYPE_SSIZE_T
AC_TYPE_UID_T
AC_CHECK_SIZEOF(char*, 4)

dnl Checks for library functions.

dnl subdir configures
AC_CONFIG_SUBDIRS(lib_misc)

AC_OUTPUT(Makefile cprec.lsm cprec.spec)
