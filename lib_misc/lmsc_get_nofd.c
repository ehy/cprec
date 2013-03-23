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
#include <fcntl.h>
#include <sys/types.h>
#include <sys/time.h>
#include <sys/resource.h>
#include <errno.h>
#include <unistd.h>


int
lmsc_get_nofd(int resv)
{
	int		nofd, i, n;
#if HAVE_SYSCONF
	long l;
	
	i = errno;
	errno = 0;
	l = sysconf(_SC_OPEN_MAX);
        if ( l < 0 ) {
                if ( errno ) {
#       if LIB_MISC_VERBOSE
			perror("sysconf(_SC_OPEN_MAX)");
#       endif /* LIB_MISC_VERBOSE */
			return 0;
		}
		l = 20;
        }
	errno = i;
        n = nofd = (int)l;
#elif HAVE_GETRLIMIT
	struct rlimit	rl;

        if ( getrlimit(RLIMIT_NOFILE, &rl) ) {
#       if LIB_MISC_VERBOSE
                perror("getrlimit(RLIMIT_NOFILE, )");
#       endif /* LIB_MISC_VERBOSE */
		return 0;
        }
        n = nofd = (int)rl.rlim_cur;
#elif OPEN_MAX
        n = nofd = OPEN_MAX;
#elif NOFILE
        n = nofd = NOFILE;
#elif _NFILE
        n = nofd = _NFILE;
#elif _POSIX_OPEN_MAX
        n = nofd = _POSIX_OPEN_MAX;
#else
        n = nofd = 20;
#endif
        for ( i = 0; i < n; i++ ) {
                if ( fcntl(i, F_GETFL) >= 0 )
                        --nofd;
        }

        return nofd - resv;
}


