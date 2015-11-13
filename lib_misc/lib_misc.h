/*
 lib_misc.[hc] - library of misc. funcs.

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

#ifndef _LIB_MISC_H_
#define _LIB_MISC_H_ 1

#include <stdio.h>
#include <stdlib.h>
#include <limits.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>

/* the typical configure script generates
 * config.h, and defines HAVE_CONFIG_H,
 * but if that is not defined, then the
 * 'HAVE_' macros must be hand-edited.
 */
#ifdef HAVE_CONFIG_H
    /*
     * test PACKAGE: this library might be configured
     * as a subdir of a package that uses config.h --
     * sadly, configure does not put re-inclusion
     * guards around config.h contents, and so this
     * header might be reinc'ing a different config.h;
     * configure tools probably have some hack for this
     * problem, but this will have to do for now.
     * NOTE that the upper configure must have tested
     * for what this lib needs, and the config.h
     * be appropriate.
     * Also, it's only an assumption that config.h
     * will invariably define PACKAGE; there might
     * be better choices.
     */
#    ifndef PACKAGE
#        include "config.h"
#    endif
#else
#    if defined(__GLIBC__)
#        define    HAVE_STRLCPY    0
#    else  /* __GLIBC__ */
#        define    HAVE_STRLCPY    1
#    endif /* __GLIBC__ */
#    define    HAVE_PATHCONF    1
#    define    HAVE_REALPATH    1
#    define    HAVE_SYSCONF    1
#    define    HAVE_GETRLIMIT    1
#    define    HAVE_GETPAGESIZE    1
#    define    HAVE_VPRINTF    1
#    define    HAVE_STDARG_H    1
#    define    HAVE_VARARGS_H    0
#    define    HAVE_ERROR    0
#endif

/* needed things */
#ifndef _
#    if ENABLE_NLS
#        include <libintl.h>
#        define _(Text) gettext (Text)
#    else
#        define textdomain(Domain)
#        define _(Text) Text
#    endif
#endif

/* helpful things */
#ifndef A_SIZE
#define A_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#endif
#define CAST_L(a) ((long)(a))
#define CAST_UL(a) ((unsigned long)(a))
#define CAST_LL(a) ((long long)(a))
#define CAST_ULL(a) ((unsigned long long)(a))

#ifndef MIN
#define MIN(a, b)    ((a) < (b) ? (a) : (b))
#endif
#ifndef MAX
#define MAX(a, b)    ((a) > (b) ? (a) : (b))
#endif

/* C code, but useful in C++ */
#if defined(__cplusplus)
extern "C" {
#endif

/* procedure prototypes */
/* get number of available descriptors at time of call */
int        lmsc_get_nofd(int);
/* get path maximum, e.g. pathconf(), PATH_MAX, etc. */
int        lmsc_get_max_path(void);
/* as above, but per arg pth if pathconf() is available */
int        lmsc_get_max_per_path(const char* pth);
/**
 * pass name of a mount point, and get name of mounted device node
 *
 * mtpt:      const char* mount point name
 * outbuf:    char buffer *must* have space for PATH_MAX chars,
 *            if PATH_MAX is defined, else return from
 *            lmsc_get_max_path() (get_max_path()) from this lib,
 *            receives device node name
 * path_max:  size_t pass actual size of outbuf in this parameter
 *
 * returns integer 0 on success, -1 on failure -- errno might be set
 *            by sys/library calls, but is not set herein
 */
int lmsc_get_mnt_dev(const char* mtpt, char* outbuf, size_t path_max);
/* get system's RAM page size */
int        lmsc_get_page_size(void);
/* as above, but exit(1) if above fails */
int        lmsc_xget_page_size(void);
/* get hardlink LINK_MAX per pathconf() or macro */
nlink_t        lmsc_get_max_hlink(const char* path);
/* read or write all of count arg in face of potential interruption */
ssize_t        lmsc_write_all(int fd, void* buf, size_t count);
ssize_t        lmsc_read_all(int fd, void* buf, size_t count);
#if ! HAVE_STRLCPY
#define strlcpy lmsc_strcntcpy
#endif
/* a workalike for BSD strlcpy; just use strlcpy, not this by name */
size_t        lmsc_strcntcpy(char* dst, const char* src, size_t cnt);
/* ignore this -- appears in this lib in error */
int        lmsc_statihack(const char* fn, char* n, struct stat* sb);

/* formerly inline procedures */
char* lmsc_l2U(char* p); /* convert case lower -> upper */
char* lmsc_U2l(char* p); /* convert case upper -> lower */
/*
 * return base pointer 'up' aligned to address that is a multiple
 * of 'alnmnt' (aligment), which must be a power of 2
 */
unsigned char* lmsc_mk_aligned_ptr(unsigned char* up, size_t alnmnt);
/* wrap strtol(): returns nonzero on error */
int lmsc_s_tol(const char* str, long* result, char** endp, int base);

/*
 * wrap strdup (POSIX) making failure fatal
 * with configurable message
 */
extern const char* lmsc_x_strdup_failmsg;
char* lmsc_x_strdup(const char*);

/*
 * print format to out or err streams optionally or unconditionally.
 */
int lmsc_pfoopt(const char*, ...); /* print to stdout optionally */
int lmsc_pfoall(const char*, ...); /* print to stdout not optionally */
int lmsc_pfeopt(const char*, ...); /* print to stderr optionally */
int lmsc_pfeall(const char*, ...); /* print to stderr not optionally */
int lmsc_pf_dbg(const char*, ...); /* print debug messages optionally */
#if ! HAVE_ERROR
void lmsc_error(int code, int errn, const char* fmt, ...);
#endif
#if NO_PUTS_MACROS
int lmsc_oputs(const char*); /* puts to stdout optionally */
int lmsc_aputs(const char*); /* puts to stdout not optionally */
int lmsc_eoputs(const char*);/* puts to stderr optionally */
int lmsc_eputs(const char*); /* puts to stderr not optionally */
#else
#define lmsc_oputs(str)   lmsc_pfoopt("%s", (str))
#define lmsc_aputs(str)   lmsc_pfoall("%s", (str))
#define lmsc_eoputs(str)  lmsc_pfeopt("%s", (str))
#define lmsc_eputs(str)   lmsc_pfeall("%s", (str))
#endif
/*
 * print format setup.
 */
/* assign the option flags (pf[oe]opt) */
void lmsc_pfo_setopt(int doit);
void lmsc_pfe_setopt(int doit);
void lmsc_pf_setup(int dopfo, int dopfe); /* just calls above two */
/* assign the FILE*s for output */
void lmsc_pf_assign_files(FILE* out, FILE* err);
void lmsc_pf_assign_files_default(void);
void lmsc_pf_init_files(void);


#if ! NO_LIB_MISC_DEF_SYMS
/*
 * Optional prettier handier symbols
 * defined w/o the lmsc_ prefix
 */

/* define handier names for procedure */
#define    get_nofd             lmsc_get_nofd
#define    get_max_path         lmsc_get_max_path
#define    get_max_per_path     lmsc_get_max_per_path
#define    get_mnt_dev          lmsc_get_mnt_dev
#define    get_page_size        lmsc_get_page_size
#define    xget_page_size       lmsc_xget_page_size
#define    get_max_hlink        lmsc_get_max_hlink
#define    read_all             lmsc_read_all
#define    write_all            lmsc_write_all
#define    strcntcpy            lmsc_strcntcpy
#define    statihack            lmsc_statihack

/* formerly inline procedures */
#define    l2U    lmsc_l2U
#define    U2l    lmsc_U2l
/*
 * return base pointer 'up' aligned to address that is a multiple
 * of 'alnmnt' (aligment), which must be a power of 2
 */
#define    mk_aligned_ptr    lmsc_mk_aligned_ptr
/* wrap strtol(): returns nonzero on error */
#define    s_tol    lmsc_s_tol

#define x_strdup_failmsg    lmsc_x_strdup_failmsg
#define x_strdup            lmsc_x_strdup

/*
 * print format to out or err streams optionally or unconditionally.
 */
#define    pfoopt    lmsc_pfoopt
#define    pfoall    lmsc_pfoall
#define    pfeopt    lmsc_pfeopt
#define    pfeall    lmsc_pfeall
#define    pf_dbg    lmsc_pf_dbg
#if ! HAVE_ERROR
#define error    lmsc_error
#endif
#if NO_PUTS_MACROS
#define    oputs    lmsc_oputs
#define    aputs    lmsc_aputs
#define    eoputs   lmsc_eoputs
#define    eputs    lmsc_eputs
#else
#define oputs(str)   lmsc_pfoopt("%s", (str))
#define aputs(str)   lmsc_pfoall("%s", (str))
#define eoputs(str)  lmsc_pfeopt("%s", (str))
#define eputs(str)   lmsc_pfeall("%s", (str))
#endif
/*
 * print format setup.
 */
/* assign the option flags (pf[oe]opt) */
#define    pfo_setopt    lmsc_pfo_setopt
#define    pfe_setopt    lmsc_pfe_setopt
#define    pf_setup      lmsc_pf_setup
/* assign the FILE*s for output */
#define    pf_assign_files         lmsc_pf_assign_files
#define    pf_assign_files_default lmsc_pf_assign_files_default
#define    pf_init_files           lmsc_pf_init_files

#endif /* ! NO_LIB_MISC_DEF_SYMS */

/* C code, but useful in C++ */
#if defined(__cplusplus)
} /* end extern "C" */
#endif

#endif /* _LIB_MISC_H_ */
