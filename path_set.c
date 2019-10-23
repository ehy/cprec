/*
   path_set.[hc] - path argument functions

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

/* this program's various incs */
#include "cprec.h"
#include "path_set.h"
#include "walk.h"
#include "lib_misc.h"
#include "xmalloc.h"

/* flage to set if dvd has lower case names */
int fnlower;
/* flage to set if paths are too long */
int  expaths;

/* buffers for pathnames */
#if DYNALLOC_BUFFERS
char* vidd;
int   viddlen;
char* outd;
int   outdlen;
char* mntd;
int   mntdlen;
char* nbuf;

size_t  outdbufdlen;
size_t  mntdbufdlen;
size_t  viddbufdlen;
size_t  nbufbufdlen;
#else
char vidd[PATH_MAX + 1];
int  viddlen;
char outd[PATH_MAX + 1];
int  outdlen;
char mntd[PATH_MAX + 1];
int  mntdlen;
char nbuf[PATH_MAX + 1];

size_t  outdbufdlen = A_SIZE(outd);
size_t  mntdbufdlen = A_SIZE(mntd);
size_t  viddbufdlen = A_SIZE(vidd);
size_t  nbufbufdlen = A_SIZE(nbuf);
#endif


void
unset_paths(void)
{
#if DYNALLOC_BUFFERS
    if ( mntd ) { /* fix-missing-block.sh */
        free(mntd);
    }
    mntd = NULL;
    if ( outd ) { /* fix-missing-block.sh */
        free(outd);
    }
    outd = NULL;
    if ( vidd ) { /* fix-missing-block.sh */
        free(vidd);
    }
    vidd = NULL;
    if ( nbuf ) { /* fix-missing-block.sh */
        free(nbuf);
    }
    nbuf = NULL;
#else
    mntd[0] = '\0';
    outd[0] = '\0';
    vidd[0] = '\0';
    nbuf[0] = '\0';
#endif
    viddlen = outdlen = mntdlen = 0;
    expaths = fnlower = 0;
}

/* string safety return checks; fatal err */
#define SCPYCHK(d, s, c) \
    do { \
        size_t n, sz = (size_t)(c); \
        if ( (n = strlcpy(d, s, sz)) >= sz ) { \
            pfeall( \
            _("%s: string size (%llu) error: exceeds space (%llu)\n"), \
            program_name, CAST_ULL(n), CAST_ULL(sz)); \
            exit(1); \
        } \
    } while ( 0 )

void
set_paths(const char* mountp, const char* outname)
{
    unset_paths();

#if DYNALLOC_BUFFERS
    if ( (mntdlen = get_max_path()) < 0 ) {
        pfeall(_("%: failed to get path maximum - %s\n"),
            program_name, strerror(errno));
        exit(1);
    }

    mntdlen *= sizeof(char); /* ha ha ha for form only */
    viddbufdlen = nbufbufdlen = outdbufdlen = mntdbufdlen = mntdlen;
    mntd = xmalloc(mntdbufdlen);
    outd = xmalloc(outdbufdlen);
    vidd = xmalloc(viddbufdlen);
    nbuf = xmalloc(nbufbufdlen);
#endif

    outdlen = strlcpy(outd, outname, outdbufdlen);
    if ( outdlen >= outdbufdlen ) {
        pfeall(_("%s: destination arg too long %s\n"),
            program_name, outname);
        exit(1);
    }

    /* clear trailing separator */
    if ( strcmp(outd, "/") ) {
        while ( outdlen && outd[outdlen - 1] == '/' ) {
            outd[--outdlen] = '\0';
        }
    }

    if ( !outdlen ) {
        pfeall(_("%s: bad target argument: %s\n"),
            program_name, outname);
        exit(1);
    }

    mntdlen = strlcpy(mntd, mountp, mntdbufdlen);
    if ( mntdlen >= mntdbufdlen ) {
        pfeall(_("%s: source arg too long %s\n"),
            program_name, mountp);
        exit(1);
    }

    viddlen = strlcpy(vidd, outd, viddbufdlen);

    /* return if buffers don't have reasonable space */
    if ( (outdlen + 1 + A_SIZE("VIDEO_TS/VIDEO_TS.VOB")) > outdbufdlen ) {
        expaths = 1;
        pfeopt(_("%s: WARNING - target argument very long: %d\n"),
            program_name, outdlen);
        return;
    }
    if ( (mntdlen + 1 + A_SIZE("VIDEO_TS/VIDEO_TS.VOB")) > mntdbufdlen ) {
        expaths = 1;
        pfeopt(_("%s: WARNING - source argument very long: %d\n"),
            program_name, mntdlen);
        return;
    }

    /* add trailing separator . . . */
    if ( mntdlen && mntd[mntdlen - 1] != '/' ) {
        mntd[mntdlen++] = '/';
    }
    vidd[viddlen++] = '/';

    /* . . . and name to check */
    SCPYCHK(&mntd[mntdlen], "VIDEO_TS", mntdbufdlen - mntdlen);
    if ( !access(mntd, F_OK) ) {
        okvid = 1;
        viddlen +=
            strlcpy(&vidd[viddlen], "VIDEO_TS", viddbufdlen - viddlen);
    } else {
        SCPYCHK(&mntd[mntdlen], "video_ts", mntdbufdlen - mntdlen);
        if ( !access(mntd, F_OK) ) {
            okvid = 1;
            viddlen += strlcpy(&vidd[viddlen],
                         ign_lc ? "video_ts" : "VIDEO_TS",
                         A_SIZE(vidd) - viddlen);
        }
    }
    mntd[mntdlen] = '\0';

    /* clear trailing separator */
    if ( strcmp(mntd, "/") ) {
        while ( mntdlen && mntd[mntdlen - 1] == '/' ) {
            mntd[--mntdlen] = '\0';
        }
    }
    if ( !mntdlen ) {
        pfeall(_("%s: bad argument: %s\n"),
            program_name, mountp);
        exit(1);
    }
}

