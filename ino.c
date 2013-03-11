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

#include "hdr_cfg.h"

/* this program's various incs */
#include "cprec.h"
#include "lib_misc.h"
#include "ino.h"
/* Prototypes for functions defined in xmalloc.c. */
#include "xmalloc.h"

#undef MULTIPLIER
#undef NHASH

#ifdef INODE_HASH_NHASH
#	define NHASH INODE_HASH_NHASH
#else
#	define NHASH 32  /* 16, 32, 64, 128, 256 . . . */
#	define NHASH_MINUS_1     (NHASH - 1)
#	define NHASH_IS_PWR_OF_2 1
#endif
#ifdef INODE_HASH_MULTIPLIER
#	define MULTIPLIER INODE_HASH_MULTIPLIER
#else
#	define MULTIPLIER 31
#endif

#if HARDLINK_STORE_PATHS
int ino_store_paths = 1;
#endif

typedef struct _ino_dev_listitem {
	struct _ino_dev_paths		il_item;  /* see ino.h */
	struct _ino_dev_listitem*	il_next;
} IDLI;

#if HARDLINK_STORE_PATHS
#	define FREE_IDLI(li) do { \
		if ( (li)->il_item.id_paths ) { \
			if ( ino_store_paths ) { \
			  nlink_t _i; \
			  for(_i=0;_i<(li)->il_item.id_nlink;_i++) { \
			    if ( (li)->il_item.id_paths[_i] ) \
			      free((li)->il_item.id_paths[_i]); \
			  } \
			  free((li)->il_item.id_paths); \
			} else { \
			  if ( (li)->il_item.id_paths[0] ) \
			    free((li)->il_item.id_paths[0]); \
			  free((li)->il_item.id_paths); \
			} \
		} \
		free(li); \
	} while ( 0 )
#else
#	define FREE_IDLI(li) do { \
		if ( (li)->il_item.id_path0 ) \
			free((li)->il_item.id_path0); \
		free(li); \
	} while ( 0 )
#endif

static IDLI* id_tbl[NHASH];

static IDP* idp_find(dit_t_t dev, dit_t_t ino);
/* autoconf should ensure 'inline' makes sense */
static inline unsigned int idp_index(dit_t_t dev, dit_t_t ino);

/**
 *  free all storage
 */
void
ino_free_storage(void)
{
	unsigned  i;

	for ( i = 0; i < NHASH; i++ ) {
		IDLI* p = id_tbl[i];

		while ( p != NULL ) {
			IDLI* tp = p;
			p = p->il_next;
			FREE_IDLI(tp);
		}

		id_tbl[i] = NULL;
	}
}

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
unsigned
ino_status(
	unsigned* ntbl,
	unsigned* minentlen,
	unsigned* maxentlen,
	unsigned* nnotfull,
	unsigned* nitems
)
{
	IDLI* p;
	unsigned  i;
	unsigned  min = UINT_MAX;
	unsigned  max = 0;
	unsigned  nno = 0;
	unsigned  nit = 0;
	unsigned  num = 0;

	for ( i = 0; i < NHASH; i++ ) {
		unsigned ccnt;

		if ( id_tbl[i] == NULL )
			continue;

		num++;
		ccnt = 0;

		for ( p = id_tbl[i]; p != NULL; p = p->il_next ) {
			ccnt++;
			if ( p->il_item.id_count < p->il_item.id_nlink ) {
				nno++;
			}
		}

		nit += ccnt;
		min = MIN(ccnt, min);
		max = MAX(ccnt, max);
	}

	if ( min == UINT_MAX )
		min = 0;

	if ( ntbl != NULL ) *ntbl = (unsigned)NHASH;
	if ( minentlen != NULL ) *minentlen = min;
	if ( maxentlen != NULL ) *maxentlen = max;
	if ( nnotfull != NULL ) *nnotfull = nno;
	if ( nitems != NULL ) *nitems = nit;

	return num;
}

/**
 *  if inode,device is not stored already, add them with
 *  link count and path, else if found add path and return from
 *  storage const pointer of structure associated with
 *  inode,device pair; else if link count < 2 or any error,
 *  return NULL; 1st form taking stat* arg merely calls second
 *  form
 */
const IDP*
ino_check(const struct stat* pss, const char* path)
{
	return ino_check_args(
		DEV_T_2_DIT_T(pss->st_dev), 
		INO_T_2_DIT_T(pss->st_ino),
		pss->st_nlink,
		path);
}

const IDP*
ino_check_args(dit_t_t dev, dit_t_t ino, nlink_t nlink, const char* path)
{
	int		i;
	IDP*		id;

	if ( nlink < 2 )
		return NULL;

	id = idp_find(dev, ino);
	if ( id == NULL ) {
		pfeall(_("%s: internal error in hash i,%llu d,%llu %s\n"),
			program_name, ino, dev, path);
		return NULL;
	}

	if ( id->id_count == 0 ) { /* just created: initialize */
		id->id_nlink = nlink;
#if HARDLINK_STORE_PATHS
		if ( ino_store_paths ) 
			id->id_paths =
				xcalloc((size_t)id->id_nlink, sizeof(char*));
		else
			id->id_paths = xmalloc(sizeof(char*));
#endif
	}

#if HARDLINK_STORE_PATHS
	if ( ino_store_paths ) {
		/* quick sanity check 1 */
		if ( id->id_count == id->id_nlink ) {
			pfeall(_("%s: i,%llu d,%llu has bogus nlink %lld\n"),
				program_name, ino, dev,
				CAST_LL(id->id_nlink));
			for ( i = 0; i < id->id_count; i++ )
				pfeall(_("%s: i,%llu d,%llu has path %s\n"),
					program_name, ino, dev,
					id->id_paths[i]);
			pfeall(_("%s: i,%llu d,%llu has extra path: %s\n"),
				program_name, ino, dev, path);
			return NULL;
		}

		/* quick sanity check 2 */
		for ( i = 0; i < id->id_count; i++ ) {
			if ( !strcmp(id->id_paths[i], path) ) {
				pfeall(_("%s: i,%llu d,%llu %s repeated\n"),
					program_name, ino, dev, path);
				return NULL;
			}
		}
	}
#endif

	i = id->id_count++;
#if HARDLINK_STORE_PATHS
	if ( ino_store_paths || i == 0 ) {
		id->id_paths[i] = xmalloc(strlen(path) + 1);
		strcpy(id->id_paths[i], path);
	}
	if ( i == 0 )
		id->id_path0 = id->id_paths[0];
#else
	if ( i == 0 ) {
		id->id_path0 = xmalloc(strlen(path) + 1);
		strcpy(id->id_path0, path);
	}
#endif

	return id;
}

static IDP*
idp_find(dit_t_t dev, dit_t_t ino)
{
	IDLI* p;
	IDLI** si = &id_tbl[idp_index(dev, ino)];
	
	while ( (p = *si) != NULL ) {
		if ( p->il_item.id_dev == dev && p->il_item.id_ino == ino )
			break;
		si = &(p->il_next);
	}
	
	/* not found: new item in bucket */
	if ( p == NULL ) {
		*si = p = xcalloc(1, sizeof(IDLI));
		p->il_item.id_dev = dev;
		p->il_item.id_ino = ino;
	}

	return &(p->il_item);
}

static inline unsigned int
idp_index(dit_t_t dev, dit_t_t ino)
{
/* How should inodes be hashed? Are they not sequential
 * within a file system? Would it not be effectively random
 * which inodes would have multiple links?
 *
 * Very limited testing has shown no advantage of prime #
 * multiplications vs. relying on the bits as they appear.
 */
#if 0
	unsigned int r, i, sz;

	r = 0;
	sz = sizeof(dev_t);
	for ( i = 0; i < sz; i++ ) {
		r = r * MULTIPLIER + ((dev >> (i << 3)) & 0xFFllu);
	}

	sz = sizeof(ino_t);
	for ( i = 0; i < sz; i++ ) {
		r = r * MULTIPLIER + ((ino >> (i << 3)) & 0xFFllu);
	}

	return r % NHASH;
#else
	/* slight hashing with the bits of octets */
#	if NHASH_IS_PWR_OF_2 && NHASH_MINUS_1
	return (dev + (dev >> 8) + ino + (ino >> 8)) & NHASH_MINUS_1;
#	else
	return (dev + (dev >> 8) + ino + (ino >> 8)) % NHASH;
#	endif
#endif
}
