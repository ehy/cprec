/*
   meta_set.[hc] - filesys metadata functions

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

#include "hdr_cfg.h"

#if HAVE_UTIMES
#include <sys/time.h>
#else
#define _DOUTIME_ 1
#endif

/* this program's various incs */
#include "meta_set.h"
#include "cprec.h"
#include "lib_misc.h"
#include "xmalloc.h"

#ifndef CHOWN_TAKES_NEG1
#define CHOWN_TAKES_NEG1 1
#endif
#if CHOWN_TAKES_NEG1
#define TEMPUID -1
#else
#define TEMPUID getuid()
#endif

void
set_d_meta(const char* nbuf, const struct stat* psb)
{
    if ( !preserve ) {
        return;
    }
    set_f_meta(nbuf, psb);
}

void
set_f_meta(const char* nbuf, const struct stat* psb)
{
#if _DOUTIME_
    struct utimbuf    tb;
#else
    struct timeval    tv[2];
#endif
    int isl;

    if ( !preserve ) {
        return;
    }

    isl = S_ISLNK(psb->st_mode);

#if _DOUTIME_
    tb.actime = psb->st_atime;
    tb.modtime = psb->st_mtime;

    if ( !isl && utime(nbuf, &tb) ) {
        perror(nbuf);
    }
#else
    tv[0].tv_sec = psb->st_atime;
    tv[0].tv_usec = 0;
    tv[1].tv_sec = psb->st_mtime;
    tv[1].tv_usec = 0;

    if ( !isl ) {
        if ( utimes(nbuf, tv) ) {
            perror(nbuf);
        }
    }
#   if HAVE_LUTIMES
    else if ( lutimes(nbuf, tv) ) {
        perror(nbuf);
    }
#   endif
#endif
    /* Stevens in APUE describes 4.3BSD behavior of chown(2)
     * treating a symbolic link and not the target, but not
     * SYSV.  {Net,Open,Free}BSD now have lchown(), and NetBSD
     * manual does not describe the behavior mentioned by Stevens.
     * Here simply do not treat symlinks if lchown is not available.
     */
    if ( !isl ) {
        /* 1st use temp uid to set gid . . . */
        if ( chown(nbuf, TEMPUID, psb->st_gid) ) {
            if ( errno != EPERM ) {
                perror(nbuf);
            }
        }
        /* . . . because this will likely fail */
        if ( chown(nbuf, psb->st_uid, psb->st_gid) ) {
            if ( errno != EPERM ) {
                perror(nbuf);
            }
        }
    }
#   if HAVE_LCHOWN
    else {
        /* 1st use temp uid to set gid . . . */
        if ( lchown(nbuf, TEMPUID, psb->st_gid) ) {
            if ( errno != EPERM ) {
                perror(nbuf);
            }
        }
        /* . . . because this will likely fail */
        if ( lchown(nbuf, psb->st_uid, psb->st_gid) ) {
            if ( errno != EPERM ) {
                perror(nbuf);
            }
        }
    }
#   endif
    /*
     * Here simply do not treat symlinks if lchmod is not available.
     */
    if ( !isl ) {
        if ( chmod(nbuf, psb->st_mode) ) {
            if ( errno != EPERM ) {
                perror(nbuf);
            }
        }
    }
#   if HAVE_LCHMOD
    else {
        if ( lchmod(nbuf, psb->st_mode) ) {
            if ( errno != EPERM ) {
                perror(nbuf);
            }
        }
    }
#   endif
}

static dire_p last;

void
rec_d_meta(dire_p pd)
{
    unsigned long nd;

    for ( nd = 0; nd < pd->ndirs; nd++ ) {
        rec_d_meta(&pd->pdirs[nd]);
    }

    if ( pd->ndirs ) {
        if ( pd->pdirs ) {
            free(pd->pdirs);
        }
        pd->ndirs = pd->alloc = 0;
        pd->pdirs = NULL;
    }

    set_d_meta(pd->path, pd->sb);

    free(pd->sb);
    last = NULL;
}

void
set_dire_t(const char* path, const struct stat* sb)
{
    const char* ptmp;

    if ( last == NULL ) {
        last = topdir;
    }

    /* last->path is substr at front of path we are downlevel */
    if ( (ptmp = strstr(path, last->path)) && ptmp == path ) {
        size_t sz;
        dire_p pnew;

        if ( !strcmp(path, last->path) ) {
            return;
        }

        pf_dbg(_("dbg: down %s -> %s\n"), last->path, path);

        if ( last->ndirs >= last->alloc ) {
            last->alloc += REALLOC_dire_t;
            last->pdirs = xrealloc(last->pdirs
                , sizeof(dire_t) * last->alloc);
        }

        pnew = &last->pdirs[last->ndirs++];
        sz = strlen(path) + 1 + sizeof(*pnew->sb);
        pnew->sb = xmalloc(sz);
        pnew->path = (char*)pnew->sb + sizeof(*pnew->sb);
        sz = sz + 1 - sizeof(*pnew->sb);
        if ( strlcpy(pnew->path, path, sz) >= sz ) {
            pfeall(_("%s: path part too long (%llu: %s) (%s:%u)\n"),
                program_name, CAST_ULL(sz), path,
                __FILE__, (unsigned)__LINE__);
            exit(EXIT_FAILURE);
        }
        pnew->ppare = last;
        pnew->ndirs = 0;
        pnew->pdirs = NULL;
        pnew->alloc = 0;
        /* safe: see above */
        memcpy(pnew->sb, sb, sizeof(*sb));
        last = pnew;

        return;
    }

    /* up some level: */
    do {
        last = last->ppare;
    } while ( last
        && !((ptmp = strstr(path, last->path)) && ptmp == path) );

    #ifdef DEBUG
    if ( last ) {
        pf_dbg(_("dbg: uplevel %s -> %s\n"), last->path, path);
    } else {
        pf_dbg(_("dbg: final %s\n"), path);
    }
    #endif

    set_dire_t(path, sb);
}

/*
 * The following are helpers for code external to this translation unit.
 *
 * The program has an option to preserve metadata and this is set in
 * extern preserve.
 *
 * where directories or regular files are created, the syscall takes
 * a mode_t argument.  Therefore, let the following provide a value
 * for that argument based on preserve.
 *
 * If we are preserving, mask off group and world bits temporarily, on
 * the premise that prior to successful completion permissions will
 * be set depth-first-recursively from the source modes.  Else, if not
 * preserving then allow umask to work with all bits.
 */

/* return mode_t for regular files per preserve option */
mode_t
get_reg_mode(void)
{
    return preserve ? 0600 : 0666;
}

/* return mode_t for directories per preserve option */
mode_t
get_dir_mode(void)
{
    return preserve ? 0700 : 0777;
}
