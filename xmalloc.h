/* xmalloc.h -- malloc with out of memory checking
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

#ifndef _X_MALLOC_H_
#define _X_MALLOC_H_ 1

/* No includes here: necessities should be
   included before this file
 */

/* Sun cc has __STDC__ nonzero only for too restrictive
 * highly conformant mode (e.g. -Xc) -- so test is
 * altered. EH Tue Apr 20 15:13:42 EDT 2010
 */
#if defined (__STDC__) && (__STDC__ || __SUNPRO_C || __SUNPRO_CC)
# define VOID void
#else
# define VOID char
#endif


/* Prototypes for functions defined here.  */

/* Sun cc has __STDC__ nonzero only for too restrictive
 * highly conformant mode (e.g. -Xc) -- so test is
 * altered. EH Tue Apr 20 15:13:42 EDT 2010
 */
#if defined (__STDC__) && (__STDC__ || __SUNPRO_C || __SUNPRO_CC)
VOID *xmalloc (size_t n);
VOID *xcalloc (size_t n, size_t s);
VOID *xrealloc (VOID *p, size_t n);
char *xstrdup (char *p);
#endif


/* Exit value when the requested amount of memory is not available.
   The caller may set it to some other value.  */
extern int xmalloc_exit_failure;


#endif /* _X_MALLOC_H_ */
