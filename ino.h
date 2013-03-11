/* 
   ino.[hc] - handling of files with link count > 1.

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

#ifndef _INO_H_
#define _INO_H_ 1

typedef unsigned long long dit_t_t;
#define DEV_T_2_DIT_T(dev) ((dit_t_t)(dev))
#define INO_T_2_DIT_T(ino) ((dit_t_t)(ino))

#if HARDLINK_STORE_PATHS
extern int ino_store_paths;
#endif

/* structure used in storage */
typedef struct _ino_dev_paths {
	dit_t_t		id_dev;
	dit_t_t		id_ino;
	nlink_t		id_nlink;
	/* count of paths presently seen for dev,ino */
	nlink_t		id_count;
#if HARDLINK_STORE_PATHS
	/* path pointers to be allocated per id_nlink, above, */
	/* if global flag ino_store_paths is not zero */
	char**		id_paths;
#endif
	/* first path found for dev,ino */
	char*		id_path0;
} IDP;

/**
 *  if inode,device is not stored already, add them with
 *  link count and path, else if found add path and return from
 *  storage const pointer of structure associated with
 *  inode,device pair; else if link count < 2 or any error,
 *  return NULL; 1st form taking stat* arg merely calls second
 *  form
 */
const IDP* ino_check(const struct stat* pss, const char* path);
const IDP* ino_check_args(dit_t_t dev, dit_t_t ino, nlink_t nlink,
				const char* path);

/**
 *  what has been found so far?
 *
 *  pointer arguments, if not NULL, are written as follows:
 *
 *  ntbl:	number of buckets (entries in table)
 *  minentlen:	minimum length of any bucket list
 *  maxentlen:	maximum length of any bucket list
 *  nnotfull:	number of entries with count < nlinks
 *  nitems:	total distinct dev,ino stored
 *
 *  returns number of non-NULL table entries
 */
unsigned ino_status(
	unsigned* ntbl,
	unsigned* minentlen,
	unsigned* maxentlen,
	unsigned* nnotfull,
	unsigned* nitems
);

/**
 *  free all storage
 */
void ino_free_storage(void);

#endif /* _INO_H_ */
