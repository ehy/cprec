/*
 * vd_cpf.[hc] - video data copy functions
 *
 * Copyright (C) 2015 Ed Hynan
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
 * MA 02110-1301, USA.
 */

#ifndef _VD_CPF_H_
#define _VD_CPF_H_ 1

/* C code, but useful in C++ */
#if defined(__cplusplus)
extern "C" {
#endif

#include <stdlib.h> /* size_t */

#include "dl_drd.h" /* drd_file_t */

/* option flag for messages from reader procs, and minimum
 * to produce messages */
extern int vd_cpf_verbose;
extern int vd_cpf_verbose_min;

/**
 * Procedures extracted from cpf.c and dd-dvd.cc, so they
 * needn't appear twice, and to reduce size of those files.
 *
 * 11.11.2015
 */

/*
 * data structure as argument to procedures defined herein:
 * each procedure will use most, if not all, structure members
 *
 * name: typedef vd_rw_proc_arg_data vd_rw_proc_args;
 * @param vd_dvdfile file handle for libdvdread: see dl_drd.h
 * @param vd_inp read(2) descriptor used if vd_poff == NULL
 * @param vd_out write(2) descriptor; data target
 * @param vd_program_name traditional argv[0] name string for messages
 * @param vd_inp_fname source/destination name string for messages
 * @param vd_out_fname source/destination name string for messages
 * @param vd_blkcnt count of 2048 byte blocks requested for read->write
 * @param vd_blknrd count of 2048 byte blocks to request per read
 * @param vd_blk_sz rw block size (certainly 2048)
 * @param vd_retrybadblk count for io error retry reads
 * @param vd_numbadblk pointer bad block count accumulator
 * @param vd_poff if not NULL: DVDReadBlocks titleset offset, maintained
 * @param vd_buf working data buffer: capacity at least (blkcnt * 2048)
 */
typedef struct vd_rw_proc_arg_data {
    drd_file_t*     vd_dvdfile;
    int             vd_inp;
    int             vd_out;
    const char*     vd_program_name;
    const char*     vd_inp_fname;
    const char*     vd_out_fname;
    size_t          vd_blkcnt;
    size_t          vd_blknrd;
    size_t          vd_blk_sz;
    size_t          vd_retrybadblk;
    size_t*         vd_numbadblk;
    int*            vd_poff;
    unsigned char*  vd_buf;
} vd_rw_proc_args;

/*
 * Read and write procedure using as source either a handle from
 * libdvdread for use by DVDReadBlocks, or a 'low level' file
 * descriptor open for read(2)ing.
 *
 * name: vd_rw_vob_blks
 * @param pargs see typedef vd_rw_proc_arg_data vd_rw_proc_args;
 * @return count of successful blocks (and *poff updated if ! NULL)
 */
ssize_t
vd_rw_vob_blks(vd_rw_proc_args* pargs);

/*
 * Read and write procedure using as source either a handle from
 * libdvdread for use by DVDReadBytes, or a 'low level' file
 * descriptor open for read(2)ing.
 *
 * name: vd_rw_ifo_blks
 * @param pargs see typedef vd_rw_proc_arg_data vd_rw_proc_args;
 * @return count of successful blocks (and *poff updated if ! NULL)
 */
ssize_t
vd_rw_ifo_blks(vd_rw_proc_args* pargs);

/*
 * Read and write procedure using as source either a handle from
 * libdvdread for use by DVDReadBlocks, or a 'low level' file
 * descriptor open for read(2)ing.
 *
 * Includes badblock retry code, and should be called from
 * vd_rw_vob_blks only as necessary.
 *
 * name: vd_rw_vob_badblks
 * @param pargs see typedef vd_rw_proc_arg_data vd_rw_proc_args;
 * @return count of successful blocks (and *poff updated if ! NULL)
 */
ssize_t
vd_rw_vob_badblks(vd_rw_proc_args* pargs);


/* C code, but useful in C++ */
#if defined(__cplusplus)
} /* end extern "C" */
#endif

#endif /* _VD_CPF_H_ */
