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
#include <errno.h>
#include <unistd.h>

#ifndef MIN
#	define MIN(a, b) ((a) < (b) ? (a) : (b))
#endif

int
lmsc_get_max_path(void)
{
	static int pm;

	if ( !pm ) {
		pm = lmsc_get_max_per_path("/");
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
	l = pathconf("/", _PC_PATH_MAX);
	if ( l < 0 ) {
		if ( errno )
			return -1;
		pm = -1;
	} else
		pm = (int)MIN(INT_MAX, l);
	errno = en;
#endif

	if ( pm == -1 ) {
#ifdef PATH_MAX
		pm = PATH_MAX;
#else
		pm = 1024;
#endif
	}

	return pm;
}


