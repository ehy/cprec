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

#ifndef _PATH_SET_H_
#define _PATH_SET_H_ 1

/* procedure prototypes */
void        set_paths(const char* mountp, const char* outname);
void        unset_paths(void);

/* flage to set if dvd has lower case names */
extern int  fnlower;
/* flage to set if paths are too long */
extern int  expaths;

#ifndef PATH_MAX
#undef  DYNALLOC_BUFFERS
#define DYNALLOC_BUFFERS 1
#endif

#ifndef DYNALLOC_BUFFERS
#define DYNALLOC_BUFFERS 0
#endif

/* buffers for pathnames */
#if DYNALLOC_BUFFERS
extern char* vidd;
extern int   viddlen;
extern char* outd;
extern int   outdlen;
extern char* mntd;
extern int   mntdlen;
extern char* nbuf;
#else
extern char vidd[];
extern int  viddlen;
extern char outd[];
extern int  outdlen;
extern char mntd[];
extern int  mntdlen;
extern char nbuf[];
#endif

extern size_t  outdbufdlen;
extern size_t  mntdbufdlen;
extern size_t  viddbufdlen;
extern size_t  nbufbufdlen;

/* some helpful snprintf macros for these buffers */
/* for snprintf into outd, mntd, vidd, nbuf */
#define OBPRINTF(ret, ARGS, nxit) CHECKSNPRINTF(outd, ret, ARGS, nxit)
#define MBPRINTF(ret, ARGS, nxit) CHECKSNPRINTF(mntd, ret, ARGS, nxit)
#define VBPRINTF(ret, ARGS, nxit) CHECKSNPRINTF(vidd, ret, ARGS, nxit)
#define NBPRINTF(ret, ARGS, nxit) CHECKSNPRINTF(nbuf, ret, ARGS, nxit)

#define CHECKSNPRINTF(BUF, R, ARGS, NXIT) \
{ \
    int n = snprintf ARGS ; \
    if ( n >= (BUF##bufdlen) || n < 0 ) { \
        pfeall( \
        _("%s: internal error in pointer or size (using %s, %s:%u)\n") \
        , program_name, #BUF, __FILE__, (unsigned)__LINE__); \
        exit(NXIT); \
    } \
    R = n; \
}

#endif /* _PATH_SET_H_ */
