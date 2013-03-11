/* 
   block_hash.[hc] - for handling files pointed to by more
   than one name under the VIDEO_TS directory - seen on a March 2010
   Disney film DVD.
   
   libdvdread provides 'UDFFindFile' function which returns first
   block address of a file, and this can be used to identify
   additional names of one file.

   Copyright (C) 2010 Ed Hynan

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
#include "block_hash.h"
/* Prototypes for functions defined in xmalloc.c. */
#include "xmalloc.h"

#undef MULTIPLIER
#undef NHASH

#ifdef BLOCK_HASH_NHASH
#	define NHASH BLOCK_HASH_NHASH
#else
#	define NHASH 8
#endif
#ifdef BLOCK_HASH_MULTIPLIER
#	define MULTIPLIER BLOCK_HASH_MULTIPLIER
#else
#	define MULTIPLIER 31
#endif

typedef struct _block_hash_listitem {
	struct _block_hash_item		bh_item;  /* see block_hash.h */
	struct _block_hash_listitem*	bh_next;
} BHLI;

#define FREE_BHLI(li) do { \
         if ( (li)->bh_item.bh_name ) \
                 free((li)->bh_item.bh_name); \
         free(li); \
        } while ( 0 )

static BHLI* bh_tbl[NHASH];

static BHI* bhp_find(blkhash_t blk, filesize_t sz);
/* autoconf should ensure 'inline' makes sense */
static unsigned int bhp_index(blkhash_t blk);

/**
 *  free all storage
 */
void
blk_free_storage(void)
{
	unsigned  i;

	for ( i = 0; i < NHASH; i++ ) {
		BHLI* p = bh_tbl[i];

		while ( p != NULL ) {
			BHLI* tp = p;
			p = p->bh_next;
			FREE_BHLI(tp);
		}

		bh_tbl[i] = NULL;
	}
}

/**
 *  if inode,device is not stored already, add them with
 *  link count and path, else if found add path and return from
 *  storage const pointer of structure associated with
 *  inode,device pair; else if link count < 2 or any error,
 *  return NULL
 *  for odd hacks in cd9660/UDF filesystems, file size
 *  must match too, as it has been observed that file entries
 *  can point to same block, but list different sizes (!), and
 *  of course this cannot be handled in Unix fs.
 */
const BHI*
blk_check(blkhash_t addr, const char* name, filesize_t sz)
{
	BHI* bhi;

	bhi = bhp_find(addr, sz);
	if ( bhi == NULL ) {
		pfeall(_("%s: internal error in block hash %llu, %s\n"),
			program_name, (unsigned long long)addr, name);
		return NULL;
	}

	if ( bhi->bh_count == 0 ) { /* just created: initialize */
		bhi->bh_name = xmalloc(strlen(name) + 1);
		strcpy(bhi->bh_name, name);
                bhi->bh_block = addr;
                bhi->bh_size = sz;
	}
	bhi->bh_count++;

	return bhi;
}

/*
 * scan for entries with same "addr", placing up to
 * "num" pointers in output array "pbhi"
 * return count put in output array (between 0 and "num")
 * (there is no way to find if more are present except to
 * try again with a larger array)
 */
unsigned
blk_scan(blkhash_t addr, const BHI* pbhi[], unsigned num)
{
	unsigned nr = 0;
	BHLI* p = bh_tbl[bhp_index(addr)];

	if ( num == 0 ) {
		return 0;
	}

	while ( p != NULL ) {
		BHI* pi = &p->bh_item;
		if ( pi->bh_block == addr ) {
			pbhi[nr++] = pi;
		}
		if ( nr == num ) {
			break;
		}
		p = p->bh_next;
	}
	
	return nr;
}

static BHI*
bhp_find(blkhash_t blk, filesize_t sz)
{
	BHLI* p;
	BHLI** si = &bh_tbl[bhp_index(blk)];
	
	while ( (p = *si) != NULL ) {
		BHI* pi = &p->bh_item;
		if ( pi->bh_block == blk && pi->bh_size == sz )
			break;
		si = &(p->bh_next);
	}
	
	/* not found: new item in bucket */
	if ( p == NULL ) {
		/* use of calloc initializes bh_count, tested in caller
                 */
                *si = p = xcalloc(1, sizeof(BHLI));
	}

	return &(p->bh_item);
}

static unsigned int
bhp_index(blkhash_t blk)
{
	unsigned int r, i, sz;

	r = 0;
	sz = sizeof(blk);

	for ( i = 0; i < sz; i++ ) {
		r = r * MULTIPLIER + ((blk >> (i << 3)) & 0xFFllu);
	}

	return r % NHASH;
}
