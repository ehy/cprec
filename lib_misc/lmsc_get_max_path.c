/* 
   lmsc_*.[hc] - library of misc. funcs.

   Copyright (C) 2007 Ed Hynan

   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation; either version 2, or (at your option)
   any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software Foundation,
   Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.  
*/

/* this program's various incs */
#include "lib_misc.h"

#include <limits.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>

#ifndef MIN
#	define MIN(a, b) ((a) < (b) ? (a) : (b))
#endif

#ifndef DEFAULT_PATH_MAXIMUM
#define DEFAULT_PATH_MAXIMUM 1024
#endif

int
lmsc_get_max_path(void)
{
	static int pm;

	if ( !pm || pm == -1 ) {
		pm = lmsc_get_max_per_path("/");
		if ( pm != -1 ) {
			pm += 1;
		}
	}

	return pm;
}

int
lmsc_get_max_per_path(const char* pth)
{
	int pm = -1;
#if HAVE_PATHCONF
	long l;
	int en = errno;
	errno = 0;
	/* POSIX does not specify behavior
	 * if path is not a directory
	 */
	l = pathconf(pth, _PC_PATH_MAX);
	if ( l < 0 ) {
		if ( errno )
			return -1;
		/* this can be reached if indeterminate;
		 * we'll return a value
		 */
		pm = -1;
	} else
		pm = (int)MIN(INT_MAX, l);
	errno = en;
#endif

	if ( pm == -1 ) {
#ifdef PATH_MAX
		pm = PATH_MAX;
#else
#ifdef _POSIX_PATH_MAX
		pm = _POSIX_PATH_MAX;
#else
		pm = DEFAULT_PATH_MAXIMUM;
#endif
#endif
		// having used a fallback,
		// simplistically subtract arg length
		pm -= strlen(pth);
		if ( pm < 0 ) {
			pm = -1;
			errno = ERANGE;
		}
	}

	return pm;
}


