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

#include <errno.h>
#include <sys/types.h>
#include <sys/stat.h>


/* A stupid hack in honor of stupid case insensitive filesystems */
int
lmsc_statihack(const char* fn, char* n, struct stat* sb)
{
    int statr, isup = (*n == 'V');

    if ( (statr = stat(fn, sb)) && errno == ENOENT && isup ) {
        U2l(n);

        if ( (statr = stat(fn, sb)) ) {
            l2U(n);
            errno = ENOENT;
        }
    }

    return statr;
}


