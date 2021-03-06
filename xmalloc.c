/* xmalloc.c -- malloc with out of memory checking
   Copyright (C) 1990, 91, 92, 93, 94, 95, 96, 99 Free Software Foundation, Inc.

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
   Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.  */

#if HAVE_CONFIG_H
# include <config.h>
#endif

/* this include is specific to the current package (it
 * provides error() substitute) -- remove this include
 * if this source file is reused in another package --
 * unless, of course, the included lib_misc is used too
 */
#include "lib_misc.h"

#if __STDC__
# define VOID void
#else
# define VOID char
#endif

#if HAVE_SYS_TYPES_H
#include <sys/types.h>
#endif

/* EH: August 16, 2014 12:58:14 PM GMT --
 * add __STDC__ to test below for OpenIndiana etc.
 */
#if STDC_HEADERS || defined(__STDC__)
# include <stdlib.h>
#else
VOID *calloc ();
VOID *malloc ();
VOID *realloc ();
void free ();
#endif

#if HAVE_STRING_H
# include <string.h>
#else
#	if __STDC__
	size_t strlen (const char *);
#	else
	size_t strlen ();
#	endif
#endif

#if ENABLE_NLS
# include <libintl.h>
# define _(Text) gettext (Text)
#else
# define textdomain(Domain)
# define _(Text) Text
#endif

/* EH: August 16, 2014 12:58:14 PM GMT --
 * lib_misc/lib_misc.h may #define error, but
 * Sun cc is not handling the definition at
 * the proto below -- so, undef
 */
#if HAVE_ERROR_H
#undef error
#include "error.h"
#elif ! defined(error)
#	if __STDC__ && (HAVE_VPRINTF || HAVE_DOPRNT)
	void error (int, int, const char *, ...);
#	else
	void error ();
#	endif
#endif

#ifndef EXIT_FAILURE
# define EXIT_FAILURE 1
#endif

/* Prototypes for functions defined here.  */
#include "xmalloc.h"
static VOID *fixup_null_alloc (size_t n);


/* Exit value when the requested amount of memory is not available.
   The caller may set it to some other value.  */
int xmalloc_exit_failure = EXIT_FAILURE;


static VOID *
fixup_null_alloc (n)
     size_t n;
{
  VOID *p;

  p = 0;
  if (n == 0)
    p = malloc ((size_t) 1);
  if (p == 0)
    error (xmalloc_exit_failure, 0, _("Memory exhausted"));
  return p;
}

/* Allocate N bytes of memory dynamically, with error checking.  */

VOID *
xmalloc (n)
     size_t n;
{
  VOID *p;

  p = malloc (n);
  if (p == 0)
    p = fixup_null_alloc (n);
  return p;
}

/* Allocate memory for N elements of S bytes, with error checking.  */

VOID *
xcalloc (n, s)
     size_t n, s;
{
  VOID *p;

  p = calloc (n, s);
  if (p == 0)
    p = fixup_null_alloc (n);
  return p;
}

/* Change the size of an allocated block of memory P to N bytes,
   with error checking.
   If P is NULL, run xmalloc.  */

VOID *
xrealloc (p, n)
     VOID *p;
     size_t n;
{
  if (p == 0)
    return xmalloc (n);
  p = realloc (p, n);
  if (p == 0)
    p = fixup_null_alloc (n);
  return p;
}
