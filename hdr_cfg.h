/**********************************************************************\
	hdr_cfg.h --	including most common things in accord with		
			a 'config.h' file.
			
	Copyright (C) Edward V. Hynan Jr., Nov 14 2007

	The GNU GPL v2 or greater is your licence to use this code.
\**********************************************************************/

#ifndef _HDR_CFG_H_
#define _HDR_CFG_H_ 1

/* ensure LFS : probably done by autoconf, but paranoia . . . */
#ifndef _FILE_OFFSET_BITS
#define _FILE_OFFSET_BITS 64
#endif
#ifndef _LARGEFILE_SOURCE
#define _LARGEFILE_SOURCE 1
#endif

#include <stdio.h>

#if HAVE_SYS_TYPES_H
#include <sys/types.h>
#endif

#if 1 /* system.h, from auto* tools, much better as far as it goes */
#include "system.h"
#else

#if HAVE_SYS_STAT_H
#include <sys/stat.h>
#endif

#if HAVE_SYS_PARAM_H
#include <sys/param.h>
#endif

#if STDC_HEADERS
#include <stdlib.h>
#else
VOID *calloc ();
VOID *malloc ();
VOID *realloc ();
void free ();
#endif

#if HAVE_STRING_H
# include <string.h>
#else
#	if __STDC__
	char *strcpy (char *, const char *);
	size_t strlen (const char *);
#	else
	char *strcpy ();
	size_t strlen ();
#	endif
#endif

#if HAVE_CTYPE_H
#include <ctype.h>
#endif

#if HAVE_FCNTL_H
#include <fcntl.h>
#endif

#if HAVE_DIRENT_H
#include <dirent.h>
#elif HAVE_NDIR_H
#include <ndir.h>
#elif HAVE_SYS_DIR_H
#include <sys/dir.h>
#elif HAVE_SYS_NDIR_H
#include <sys/ndir.h>
#endif

#if HAVE_UTIME_H
#include <utime.h>
#endif

#if HAVE_ERRNO_H
#include <errno.h>
#endif

#if ENABLE_NLS
# include <libintl.h>
# define _(Text) gettext (Text)
#else
# define textdomain(Domain)
# define _(Text) Text
#endif

#if HAVE_UNISTD_H
#include <unistd.h>
#endif

#endif /* system.h */

#if HAVE_STDINT_H
#include <stdint.h>
#endif

#if HAVE_LIMITS_H
#include <limits.h>
#endif

#if HAVE_SYS_RESOURCE_H
#include <sys/resource.h>
#endif

#if HAVE_ERROR_H
#include <error.h>
#else
#	if defined(__STDC__) && (HAVE_VPRINTF || HAVE_DOPRNT)
	void error (int, int, const char *, ...);
#	else
	void error ();
#	endif
#endif

#ifndef O_NOFOLLOW
#define O_NOFOLLOW  0
#endif
#ifndef O_LARGEFILE
#define O_LARGEFILE  0
#endif

#ifndef PATH_MAX
#ifdef _POSIX_PATH_MAX
#define PATH_MAX _POSIX_PATH_MAX
#else
#define PATH_MAX 255 /* short, safe */
#endif
#endif

#endif /* _HDR_CFG_H_ */
