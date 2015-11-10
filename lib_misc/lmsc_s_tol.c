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

/* wrap strtol(): returns nonzero on error */
int lmsc_s_tol(const char* str, long* result, char** endp, int base)
{
    int e = errno;

    errno = 0;
    *result = strtol(str, endp, base);

    if ( errno ) {
        return -1;
    }
    if ( str == *endp ) {
        errno = EINVAL;
        return -1;
    }

    errno = e;

    return 0;
}


