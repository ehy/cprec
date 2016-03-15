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
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if HAVE_SETMNTENT && HAVE_GETMNTENT && HAVE_ENDMNTENT
#   include <mntent.h>
    /* a Linux sys will define MNTTAB but as /etc/fstab,
     * not /etc/mtab, which is what is wanted . . .
     * so use new macro
     */
#   ifndef MNT_TABLE
#      define MNT_TABLE "/etc/mtab"
#   endif
#   define GET_MNT_T1
#elif defined(__sun) && HAVE_GETMNTENT
#   include <sys/mnttab.h>
    /* a OpenSolaris sys will define MNTTAB
     * as /etc/mnttab, which is what is wanted . . .
     */
#   ifndef MNTTAB
#      warning "on sun we expect MNTTAB macro in sys/mnttab.h: FIXME"
#      define MNTTAB "/etc/mnttab"
#   endif
#   define GET_MNT_SUN
#elif HAVE_GETMNTINFO
#   include <sys/param.h>
#   include <sys/mount.h>
#   define GET_MNT_44BSD
#elif HAVE_GETFSFILE && HAVE_ENDFSENT
#   include <fstab.h>
#   define GET_FS_FILE
#endif

/**
 * pass name of a mount point, and get name of mounted device node
 *
 * mtpt:      const char* mount point name
 * outbuf:    char buffer should have space for PATH_MAX chars,
 *            if PATH_MAX is defined, else return from
 *            lmsc_get_max_path() (get_max_path()) from this lib;
 *            this receives device node name
 * path_max:  size_t pass actual size of outbuf in this parameter
 *
 * returns integer 0 on success, -1 on failure -- errno might be set
 *            by sys/library calls, but is not set herein
 */
int
lmsc_get_mnt_dev(const char* mtpt, char* outbuf, size_t path_max)
{
    const char* want_mtpt = mtpt;

/* realpath() is in POSIX 2008 (earlier?) */
#if HAVE_REALPATH && defined(PATH_MAX)
    /* POSIX speaks of realpath in terms of
     * *if* PATH_MAX is defined (in limits.h);
     * here, depend on it (CPP conditional)
     * and use only if we get sufficient size
     * arg, else calling code can see to path
     * normalization on its own
     */
    if ( path_max >= PATH_MAX && realpath(mtpt, outbuf) ) {
        want_mtpt = outbuf;
    }
#endif

/* these test macros are defined near top of file */
#if defined(GET_MNT_T1)
    { /* new block scope for new auto vars */
    struct mntent* pme;
    FILE* fp = setmntent(MNT_TABLE, "r");

    if ( fp == 0 ) {
        return -1;
    }

    while ( pme = getmntent(fp) ) {
        if ( strcmp(pme->mnt_dir, want_mtpt) == 0 ) {
            size_t l = path_max;

            if ( strlcpy(outbuf, pme->mnt_fsname, l) >= l ) {
                endmntent(fp);
                return -1;
            }

            endmntent(fp);
            return 0;
        }
    }

    endmntent(fp);
    return -1;
    }
#elif defined(GET_MNT_SUN)
    { /* new block scope for new auto vars */
    struct mnttab sm;
    int gr;
    FILE* fp = fopen(MNTTAB, "r");

    if ( fp == 0 ) {
        return -1;
    }

    while ( (gr = getmntent(fp, &sm)) == 0 ) {
        if ( strcmp(want_mtpt, sm.mnt_mountp) == 0 ) {
            size_t l = path_max;

            if ( strlcpy(outbuf, sm.mnt_special, l) >= l ) {
                fclose(fp);
                return -1;
            }

            fclose(fp);
            return 0;
        }
    }

    if ( gr > 0 ) {
        perror("getmntent");
    }

    fclose(fp);
    return -1;
    }
#elif defined(GET_MNT_44BSD)
    { /* new block scope for new auto vars */
#   if defined(__NetBSD__)
#       define STRUCT_STATFS_TYPE struct statvfs
#   else
#       define STRUCT_STATFS_TYPE struct statfs
#   endif
    STRUCT_STATFS_TYPE* stp;
    int i;
    int stsz = getmntinfo(&stp, MNT_NOWAIT);

    for ( i = 0; i < stsz; ++i ) {
        if ( strcmp(want_mtpt, stp[i].f_mntonname) == 0 ) {
            size_t l = path_max;

            if ( strlcpy(outbuf, stp[i].f_mntfromname, l) >= l ) {
                return -1;
            }

            return 0;
        }
    }

    return -1;
    }
#elif defined(GET_FS_FILE)
    { /* new block scope for new auto vars */
    size_t l = path_max;
    struct fstab* stp = getfsfile(want_mtpt);

    if ( stp == 0 ) {
        endfsent();
        return -1;
    }

    if ( strlcpy(outbuf, stp->fs_spec, l) >= l ) {
        endfsent();
        return -1;
    }

    endfsent();
    return 0;
    }
#else
    return -1;
#endif
}
