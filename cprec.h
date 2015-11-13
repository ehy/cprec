/*
   cprec - A recursive directory hierarchy copier; much like 'cp -Rp'.

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
#ifndef _CPREC_H_
#define _CPREC_H_ 1

/* dvd read stuff */
#ifndef DEF_BLOCK_READ_CNT
/* #define DEF_BLOCK_READ_CNT 4096 -- * 2k, so 1 == 2k, 512 == 1m */
#define DEF_BLOCK_READ_CNT	4096 /* 1 == 2k, 512 == 1m */
#endif /* #ifndef DEF_BLOCK_READ_CNT */
extern size_t         block_read_count;

/* badblock retry read count */
#define DEF_RETRY_BLOCK_CNT	48
extern size_t         retrybadblk;

/* main memory */
extern unsigned char* global_buffer;
extern unsigned char* global_aligned_buffer;
extern size_t         global_buffer_size;
extern size_t         global_buffer_align;

/* The name the program was run with, stripped of any leading path. */
extern const char* program_name;
/* The DVD drive device node, or symlink, as appropriate */
extern const char* dvdname;
extern const char* dvdnamedef;

/* opt vars */
extern int nfdresv;	/* reserve this from ftw() for other use */
extern int nfdmax;	/* use no more than this number of dir fd */
/* flagging whether to quit on unexpected dvd dir entries: */
extern int ign_dnr;	/* ignore directories not readable */
extern int ign_sl;	/* ignore symbolic links */
extern int ign_hl;	/* ignore hard links */
extern int ign_ns;	/* ignore stat() failures */
extern int ign_sf;	/* ignore special file failures */
/* other flags: */
extern int ign_lc;	/* ignore lower case 'video_ts' and its entries */
extern int ign_ex;	/* ignore EEXIST writing output --ignore-existing */
extern int do_ioerrs;	/* desperate measures in response to I/O errors */
extern int force;	/* -f; ignore read()/open() errors + overwrite */
extern int preserve;	/* -p; preserve metadata if permitted */

#if ! HAVE_LIBDVDREAD
extern const char* drd_libname;		/* --libdvdr */
#endif
extern int desired_title;		/* --dvdbackup (converted) */
extern int want_quiet;			/* --quiet, --silent */
extern int want_verbose;		/* --verbose */
/* dry-run is unmaintained; makes segfaults */
/* it is still tested, so it must remain 0 */
extern int want_dry_run;		/* --dry-run */
extern int simple_copy;			/* --simple-copy */

#endif /* _CPREC_H_ */
