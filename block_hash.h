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

#ifndef _BLOCK_HASH_H_
#define _BLOCK_HASH_H_ 1

/**
 *  type to store block addresses and key into hash;
 *  libdvdread UDFFindFile() returns uint32_t so that's it
 */
typedef uint32_t blkhash_t;
/**
 *  libdvdread UDFFindFile() takes pointer to uint32_t
 *  and store file size in bytes there
 */
typedef uint32_t filesize_t;

/**
 *  structure used in storage
 */
typedef struct _block_hash_item {
        unsigned long	bh_count; /* additional links; 1 based */
        char*		bh_name;
	blkhash_t	bh_block;
        filesize_t	bh_size;
} BHI;

/**
 *  if block address is not stored already, add it with
 *  file name and size in bytes, else if found return from
 *  storage const pointer to structure typedef'd BHI
 */
const BHI* blk_check(blkhash_t addr, const char* name, filesize_t sz);

/**
 * scan for entries with same "addr", placing up to
 * "num" pointers in output array "pbhi"
 * return count put in output array (between 0 and "num")
 * (there is no way to find if more are present except to
 * try again with a larger array)
 */
unsigned blk_scan(blkhash_t addr, const BHI* pbhi[], unsigned num);

/**
 *  free all storage
 */
void blk_free_storage(void);

#endif /* _BLOCK_HASH_H_ */
