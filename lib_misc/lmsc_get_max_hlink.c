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
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>


nlink_t
lmsc_get_max_hlink(const char* path)
{
#if HAVE_PATHCONF
	long l = pathconf(path, _PC_LINK_MAX);
	if ( l == -1 ) l = 1;
	return (nlink_t)l;
#elif	LINK_MAX
	return LINK_MAX;
#elif	_POSIX_LINK_MAX
	return _POSIX_LINK_MAX;
#else
	return 1;
#endif
}


