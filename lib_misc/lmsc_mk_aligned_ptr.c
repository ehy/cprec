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
#include <sys/types.h>
#include <string.h>
#include <unistd.h>


/*
 * return base pointer 'up' aligned to address that is a multiple
 * of 'alnmnt' (aligment), which must be a power of 2
 */
unsigned char*
lmsc_mk_aligned_ptr(unsigned char* up, size_t alnmnt)
{
    size_t msk;
    ptrdiff_t dff;

    msk = alnmnt - 1;
    dff = (ptrdiff_t)up & (ptrdiff_t)msk;

    if ( dff == (ptrdiff_t)0 ) {
        return up;
    }

    return up + (ptrdiff_t)alnmnt - dff;
}


