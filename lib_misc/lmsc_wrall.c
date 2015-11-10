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

#include <sys/types.h>
#include <errno.h>
#include <unistd.h>

/*
 * a BOOLEAN proc(void) is useful for a check on
 * signal interrupt -- if available, make a
 * testable definition so it is used
 */
#ifndef signal_check_intr
static int signal_check_intr(void)
{
    return 0;
}
#endif

/* uncertainty: just in case */
#ifndef EWOULDBLOCK
#   define EWOULDBLOCK EAGAIN
#endif

ssize_t
lmsc_write_all(int fd, void* buf, size_t count)
{
    ssize_t rem, tw;
    char* p = buf;

    for ( rem = count; rem; ) {
        errno = 0;
        tw = write(fd, &p[count-rem], rem);
        if ( tw < 0 ) {
            if ( errno == EAGAIN || errno == EWOULDBLOCK ) {
                /* this proc is not designed for
                 * non-blocking IO -- handle elsewhere
                 */
                break;
            }
            if ( errno == EINTR ) {
                if ( signal_check_intr() ) {
                    break;
                }
                errno = 0;
                continue;
            }
            return tw;
        }
        rem -= tw;
    }

    return count - rem;
}

ssize_t
lmsc_read_all(int fd, void* buf, size_t count)
{
    ssize_t rem, tw;
    char* p = buf;

    for ( rem = count; rem; ) {
        errno = 0;
        tw = read(fd, &p[count-rem], rem);
        if ( tw < 0 ) {
            if ( errno == EAGAIN || errno == EWOULDBLOCK ) {
                /* this proc is not designed for
                 * non-blocking IO -- handle elsewhere
                 */
                break;
            }
            if ( errno == EINTR ) {
                if ( signal_check_intr() ) {
                    break;
                }
                errno = 0;
                continue;
            }
            return tw;
        }
        if ( tw == 0 ) {
            break;
        }
        rem -= tw;
    }

    return count - rem;
}


