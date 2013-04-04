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

#if HAVE_VPRINTF

#include <stdio.h>
#include <string.h>
#include <errno.h>

#if HAVE_STDARG_H
#include <stdarg.h>
#elif HAVE_VARARGS_H
#include <varargs.h>
#else
#error "FIX headers for va_list"
#endif

#ifndef PFIO_DEBUG_ENVNAME
#	define PFIO_DEBUG_ENVNAME	"PFIO_DEBUG"
#endif /* PFIO_DEBUG_ENVNAME */
static const char* pfio_dbg_envvar_str = PFIO_DEBUG_ENVNAME;

static int pf_init_done;
static int do_pfoopt;
static int do_pfeopt;
static int do_pf_dbg;
static FILE* pfoutfile;
static FILE* pferrfile;
static FILE* pfdbgfile;

/* assign the above flags (pf[oe]opt) */
void
lmsc_pfo_setopt(int doit)
{
	lmsc_pf_init_files();
	do_pfoopt = doit ? 1 : 0;
}
void
lmsc_pfe_setopt(int doit)
{
	lmsc_pf_init_files();
	do_pfeopt = doit ? 1 : 0;
}

void
lmsc_pf_debug_check(void)
{
	static int done;
	const char* p;
	const char* str = pfio_dbg_envvar_str;

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
			lmsc_pf_dbg(_("dbg: failed opening dbg file %s\n"), p);
		}
	}

	lmsc_pf_dbg(_("dbg: %s == %s -- will print debug messages\n"), str, p);
}

void
lmsc_pf_setup(int dopfo, int dopfe)
{
	lmsc_pfo_setopt(dopfo);
	lmsc_pfe_setopt(dopfe);
}

/* assign the above FILE*s */
void
lmsc_pf_assign_files(FILE* out, FILE* err)
{
	pfoutfile = out;
	pferrfile = err;
	lmsc_pf_debug_check();
	pf_init_done = 1;
}
void
lmsc_pf_assign_files_default(void)
{
	lmsc_pf_assign_files(stdout, stderr);
}
void
lmsc_pf_init_files(void)
{
	if ( !pf_init_done ) {
		lmsc_pf_assign_files_default();
	}
}

/*
 * print format to `pfoutfile' optionally.
 */
int
lmsc_pfoopt(const char* fmt, ...)
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
lmsc_pfoall(const char* fmt, ...)
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
lmsc_pfeopt(const char* fmt, ...)
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
lmsc_pfeall(const char* fmt, ...)
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
lmsc_pf_dbg(const char* fmt, ...)
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
lmsc_aputs(const char* str)
{
    return lmsc_pfoall("%s", str);
}
int
lmsc_oputs(const char* str)
{
    return lmsc_pfoopt("%s", str);
}
int
lmsc_eputs(const char* str)
{
    return lmsc_pfeall("%s", str);
}
int
lmsc_eoputs(const char* str)
{
    return lmsc_pfeopt("%s", str);
}
#endif /* #if NO_PUTS_MACROS */

#if ! HAVE_ERROR
void lmsc_error(int code, int errn, const char* fmt, ...)
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

#endif /* HAVE_VPRINTF */

