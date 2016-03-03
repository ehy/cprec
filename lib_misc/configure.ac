dnl Process this file with autoconf to produce a configure script.

dnl Every other copy of the package version number gets its value from here
AC_INIT([lib_misc.a], [0.9.0])
AM_INIT_AUTOMAKE([-Wall -Werror])

dnl create a config.h file (Automake will add -DHAVE_CONFIG_H)
AC_CONFIG_HEADERS(config.h)

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


dnl Checks for programs.
#AC_PROG_INSTALL
AC_PROG_CC
AM_PROG_AR
AC_PROG_RANLIB
AC_C_INLINE

dnl Checks for libraries.

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
AC_CHECK_FUNCS(mkfifo vprintf doprnt seekdir telldir getrlimit pathconf getpagesize sysconf strlcpy mmap lstat readlink symlink lchown lchmod lutimes utimes error dlsym posix_memalign getfsfile endfsent getmntinfo setmntent getmntent endmntent realpath)
AC_CHECK_FUNC(mknod)

dnl Checks for typedefs, structures, and compiler characteristics.
AC_C_CONST
AC_TYPE_SIZE_T
AC_TYPE_SSIZE_T
AC_TYPE_UID_T
AC_CHECK_SIZEOF(char*, 4)

dnl Checks for library functions.

#AC_CONFIG_FILES([Makefile])
#AC_OUTPUT
AC_OUTPUT([Makefile])
