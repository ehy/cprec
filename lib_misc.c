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

#include "hdr_cfg.h"
#include <stddef.h>

/* this program's various incs */
#include "lib_misc.h"

#if defined(_SC_PAGE_SIZE) && ! defined(_SC_PAGESIZE)
#   define _SC_PAGESIZE _SC_PAGE_SIZE
#endif

int
get_nofd(int resv)
{
	int		nofd, i, n;
#if HAVE_GETRLIMIT
	struct rlimit	rl;

        if ( getrlimit(RLIMIT_NOFILE, &rl) ) {
                perror("getrlimit(RLIMIT_NOFILE, )");
		return 0;
        }
        n = nofd = (int)rl.rlim_cur;
#elif HAVE_SYSCONF
	long l;
	
	i = errno;
	errno = 0;
	l = sysconf(_SC_OPEN_MAX);
        if ( l < 0 ) {
                if ( errno ) {
			perror("sysconf(_SC_OPEN_MAX)");
			return 0;
		}
		l = 20;
        }
	errno = i;
        n = nofd = (int)l;
#elif OPEN_MAX
        n = nofd = OPEN_MAX;
#elif NOFILE
        n = nofd = NOFILE;
#elif _NFILE
        n = nofd = _NFILE;
#elif _POSIX_OPEN_MAX
        n = nofd = _POSIX_OPEN_MAX;
#else
        n = nofd = 20;
#endif
        for ( i = 0; i < n; i++ ) {
                if ( fcntl(i, F_GETFL) >= 0 )
                        --nofd;
        }

        return nofd - resv;
}

int
xget_page_size(void)
{
	int s = get_page_size();
	if ( s < 0 )
		exit(1);
	return s;
}

int
get_page_size(void)
{
	int s;
#if HAVE_SYSCONF
	s = (int)sysconf(_SC_PAGESIZE);
        if ( s < 0 ) {
		perror("sysconf(_SC_PAGESIZE)");
        }
#elif HAVE_GETPAGESIZE
	s = getpagesize();
#else
#	error "Fix get_page_size() somehow!"
#endif
        if ( s <= 0 ) {
		pfeall(_("get_page_size(void) whacked: %d\n"), s);
		return s ? s : -1;
        }

	return s;
}

int
get_max_path(void)
{
	static int pm;

	if ( !pm ) {
#ifdef PATH_MAX
		pm = PATH_MAX;
#else
#if HAVE_PATHCONF
		long l;
		int en = errno;
		errno = 0;
		l = pathconf("/", _PC_PATH_MAX);
		if ( l < 0 ) {
			if ( errno )
				return -1;
			pm = 1024;
		} else
			pm = (int)MIN(INT_MAX, l);
		errno = en;
#else
		pm = 1024;
#endif
#endif
	}

	return pm;
}

nlink_t
get_max_hlink(const char* path)
{
#if HAVE_PATHCONF
	long l = pathconf(path, _PC_LINK_MAX);
	if ( l == -1 ) l = 1;
	return (nlink_t)l;
#elif	LINK_MAX
	return LINK_MAX;
#elif	_POSIX_LINK_MAX
	return _POSIX_LINK_MAX;
#else
	return 1;
#endif
}

/* A stupid hack in honor of stupid case insensitive filesystems */
int
statihack(const char* fn, char* n, struct stat* sb)
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

ssize_t
write_all(int fd, void* buf, size_t count)
{
        ssize_t rem, tw;
        char* p = buf;

        for ( rem = count; rem; ) {
                tw = write(fd, &p[count-rem], rem);
                if ( tw < 0 ) {
                        if ( errno == EAGAIN || errno == EINTR ) {
                                #if DEBUG_IO_INTR
				perror("continuing interrupted write");
				#endif
                                continue;
                        }
                        return tw;
                }
                rem -= tw;
        }

        return count;
}

ssize_t
read_all(int fd, void* buf, size_t count)
{
        ssize_t rem, tw;
        char* p = buf;

        for ( rem = count; rem; ) {
                tw = read(fd, &p[count-rem], rem);
                if ( tw < 0 ) {
                        if ( errno == EAGAIN || errno == EINTR ) {
                                #if DEBUG_IO_INTR
                                perror("continuing interrupted read");
				#endif
                                continue;
                        }
			return tw;
                }
		if ( tw == 0 ) {
			return count - rem;
		}
                rem -= tw;
        }

        return count;
}

#if ! HAVE_STRLCPY
size_t
strcntcpy(char* dst, const char* src, size_t cnt)
{
        size_t n = cnt;
        char* d = dst;
        const char* s = src;

        while ( n && (*d++ = *s++) )
                --n;
        if ( !n ) {
                if ( cnt )
                        *--d = '\0';
                while ( *s++ );
        }
        return --s - src;
}
#endif

char* l2U(char* p)
{
	char* s;
	for ( s = p; *s; s++ )
		*s = toupper((int)*s);
	return p;
}

char* U2l(char* p)
{
	char* s;
	for ( s = p; *s; s++ )
		*s = tolower((int)*s);
	return p;
}

/* wrap strtol(): returns nonzero on error */
int s_tol(const char* str, long* result, char** endp, int base)
{
	int e = errno;

	errno = 0;
	*result = strtol(str, endp, base);

	if ( errno ) {
		return -1;
	}
	if ( str == *endp ) {
		errno = EINVAL;
		return -1;
	}

	errno = e;

	return 0;
}

/*
 * return base pointer 'up' aligned to address that is a multiple
 * of 'alnmnt' (aligment), which must be a power of 2
 */
unsigned char*
mk_aligned_ptr(unsigned char* up, size_t alnmnt)
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


#if HAVE_VPRINTF

#if HAVE_STDARG_H
#include <stdarg.h>
#elif HAVE_VARARGS_H
#include <varargs.h>
#else
#error "FIX headers for va_list"
#endif

static int pf_init_done;
static int do_pfoopt;
static int do_pfeopt;
static int do_pf_dbg;
static FILE* pfoutfile;
static FILE* pferrfile;
static FILE* pfdbgfile;

/* assign the above flags (pf[oe]opt) */
void
pfo_setopt(int doit)
{
	pf_init_files();
	do_pfoopt = doit ? 1 : 0;
}
void
pfe_setopt(int doit)
{
	pf_init_files();
	do_pfeopt = doit ? 1 : 0;
}

void
pf_debug_check(void)
{
	static int done;
	const char* p;
	const char* str = "CPREC_DEBUG";

	if ( done )
		return;

	done = 1;
	pfdbgfile = stderr;

	p = getenv(str);

	if ( p ) {
		do_pf_dbg = 1;
		if ( *p && *p != '-' )
			pfdbgfile = fopen(p, "w");
		if ( pfdbgfile == NULL ) {
			pfdbgfile = stderr;
			pf_dbg(_("dbg: failed opening dbg file %s\n"), p);
		}
	}

	pf_dbg(_("dbg: %s == %s -- will print debug messages\n"), str, p);
}

void
pf_setup(int dopfo, int dopfe)
{
	pfo_setopt(dopfo);
	pfe_setopt(dopfe);
}

/* assign the above FILE*s */
void
pf_assign_files(FILE* out, FILE* err)
{
	pfoutfile = out;
	pferrfile = err;
	pf_debug_check();
	pf_init_done = 1;
}
void
pf_assign_files_default(void)
{
	pf_assign_files(stdout, stderr);
}
void
pf_init_files(void)
{
	if ( !pf_init_done ) {
		pf_assign_files_default();
	}
}

/*
 * print format to `pfoutfile' optionally.
 */
int
pfoopt(const char* fmt, ...)
{
	int r;
	va_list ap;

	va_start(ap, fmt);
	pf_init_files();
	if ( do_pfoopt )
		r = vfprintf(pfoutfile, fmt, ap);
	else if ( do_pf_dbg )
		r = vfprintf(pfdbgfile, fmt, ap);
	else
		r = 0;
	va_end(ap);

	return r;
}


/*
 * print format to `pfoutfile' unconditionally.
 */
int
pfoall(const char* fmt, ...)
{
	int r;
	va_list ap;

	va_start(ap, fmt);
	pf_init_files();
	r = vfprintf(pfoutfile, fmt, ap);
	va_end(ap);

	return r;
}


/*
 * print format to `pferrfile' optionally.
 */
int
pfeopt(const char* fmt, ...)
{
	int r;
	va_list ap;

	va_start(ap, fmt);
	pf_init_files();
	if ( do_pfeopt )
		r = vfprintf(pferrfile, fmt, ap);
	else if ( do_pf_dbg )
		r = vfprintf(pfdbgfile, fmt, ap);
	else
		r = 0;
	va_end(ap);

	return r;
}


/*
 * print format to pferrfile unconditionally.
 */
int
pfeall(const char* fmt, ...)
{
	int r;
	va_list ap;

	va_start(ap, fmt);
	pf_init_files();
	r = vfprintf(pferrfile, fmt, ap);
	va_end(ap);

	return r;
}

/*
 * print format to pfdbgfile if flag is set
 */
int
pf_dbg(const char* fmt, ...)
{
	int r;
	va_list ap;

	va_start(ap, fmt);
	pf_init_files();
	if ( do_pf_dbg )
		r = vfprintf(pfdbgfile, fmt, ap);
	else
		r = 0;
	va_end(ap);

	return r;
}


#if NO_PUTS_MACROS
int
aputs(const char* str)
{
    return pfoall("%s", str);
}
int
oputs(const char* str)
{
    return pfoopt("%s", str);
}
int
eputs(const char* str)
{
    return pfeall("%s", str);
}
int
eoputs(const char* str)
{
    return pfeopt("%s", str);
}
#endif /* #if NO_PUTS_MACROS */

#if ! HAVE_ERROR
void error(int code, int errn, const char* fmt, ...)
{
	va_list ap;

	va_start(ap, fmt);
	vfprintf(stderr, fmt, ap);
	va_end(ap);

	if ( errn )
		fprintf(stderr, ": %s\n", strerror(errn));
	else
		fputc('\n', stderr);

	if ( code )
		exit(code);
}
#endif /* ! HAVE_ERROR */

#else /* HAVE_VPRINTF */
#error "FIX this for systems without vprintf()"
#endif /* HAVE_VPRINTF */

