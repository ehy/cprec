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

#include <string.h>
#include <unistd.h>

size_t
lmsc_strcntcpy(char* dst, const char* src, size_t cnt)
{
    size_t n = cnt;
    char* d = dst;
    const char* s = src;

    while ( n && (*d++ = *s++) ) {
        --n;
    }

    if ( !n ) {
        if ( cnt ) {
            *--d = '\0';
        }
        while ( *s++ ) {
            ;
        }
    }

    return --s - src;
}


