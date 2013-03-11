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

/* helpful things */
#define A_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#ifndef LOGICAL_BLOCK_LENGTH
#define LOGICAL_BLOCK_LENGTH	2048	/* agrees w/ DVD video */
#endif
#define CAST_L(a) ((long)(a))
#define CAST_UL(a) ((unsigned long)(a))
#define CAST_LL(a) ((long long)(a))
#define CAST_ULL(a) ((unsigned long long)(a))

#ifndef MIN
#define MIN(a, b)	((a) < (b) ? (a) : (b))
#endif
#ifndef MAX
#define MAX(a, b)	((a) > (b) ? (a) : (b))
#endif

/* procedure prototypes */
int	    get_nofd(int);
int	    get_max_path(void);
int	    get_page_size(void);
int	    xget_page_size(void);
nlink_t	    get_max_hlink(const char* path);
ssize_t	    read_all(int fd, void* buf, size_t count);
ssize_t	    write_all(int fd, void* buf, size_t count);
#if HAVE_STRLCPY
#define strcntcpy strlcpy
#else
size_t	    strcntcpy(char* dst, const char* src, size_t cnt);
#endif
int	    statihack(const char* fn, char* n, struct stat* sb);

/* formerly inline procedures */
char* l2U(char* p); /* convert case lower -> upper */
char* U2l(char* p); /* convert case upper -> lower */
/*
 * return base pointer 'up' aligned to address that is a multiple
 * of 'alnmnt' (aligment), which must be a power of 2
 */
unsigned char* mk_aligned_ptr(unsigned char* up, size_t alnmnt);
/* wrap strtol(): returns nonzero on error */
int s_tol(const char* str, long* result, char** endp, int base);

/*
 * print format to out or err streams optionally or unconditionally.
 */
int pfoopt(const char*, ...); /* print format to out stream optionally */
int pfoall(const char*, ...); /* print format to out stream not optionally */
int pfeopt(const char*, ...); /* print format to err stream optionally */
int pfeall(const char*, ...); /* print format to err stream not optionally */
int pf_dbg(const char*, ...); /* print format debug messages optionally */
#if NO_PUTS_MACROS
int oputs(const char*); /* print string to out stream optionally */
int aputs(const char*); /* print string to out stream not optionally */
int eoputs(const char*);/* print string to out stream optionally */
int eputs(const char*); /* print string to out stream not optionally */
#else
#define oputs(str)   pfoopt("%s", (str))
#define aputs(str)   pfoall("%s", (str))
#define eoputs(str)  pfeopt("%s", (str))
#define eputs(str)   pfeall("%s", (str))
#endif
/*
 * print format setup.
 */
/* assign the option flags (pf[oe]opt) */
void pfo_setopt(int doit);
void pfe_setopt(int doit);
void pf_setup(int dopfo, int dopfe); /* just calls above two */
/* assign the FILE*s for output */
void pf_assign_files(FILE* out, FILE* err);
void pf_assign_files_default(void);
void pf_init_files(void);

/* size of a (char) pointer, needed by mk_aligned_ptr()
   should be be defined by configure from macro in configure.in
   ensure correct definition if built w/o auto* system
 */
#ifndef SIZEOF_CHARP
#	error "size of char* must be defined as SIZEOF_CHARP"
#endif


#endif /* _LIB_MISC_H_ */
