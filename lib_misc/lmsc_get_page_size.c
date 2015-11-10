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

#include <stddef.h>
#include <errno.h>
#include <unistd.h>

#if defined(_SC_PAGE_SIZE) && ! defined(_SC_PAGESIZE)
#   define _SC_PAGESIZE _SC_PAGE_SIZE
#endif


int
lmsc_xget_page_size(void)
{
    int s = lmsc_get_page_size();
    if ( s < 0 ) {
        exit(1);
    }
    return s;
}

int
lmsc_get_page_size(void)
{
    int s;
#if HAVE_SYSCONF
    s = (int)sysconf(_SC_PAGESIZE);
#   if LIB_MISC_VERBOSE
    if ( s < 0 ) {
        perror("sysconf(_SC_PAGESIZE)");
    }
#   endif /* LIB_MISC_VERBOSE */
#elif HAVE_GETPAGESIZE
    s = getpagesize();
#else
#   error "Fix get_page_size() somehow!"
#endif
    if ( s <= 0 ) {
        return s ? s : -1;
    }

    return s;
}


