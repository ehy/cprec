/* 
   dl_drd.[hc] - load libdvdread functions

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

#ifndef _DL_DRD_H_
#define _DL_DRD_H_ 1


/* procedure prototypes (stubs if we have the lib at link-time) */
int open_drd(const char* drd_soname, int drd_flags);
int open_drd_default(void);
int load_drd_syms(void);
int close_drd(void);
int get_drd_defflags(void);

/* least dvdread version known to this code */
#define DVDREAD_LEASTV	904

/* config.h should have been included by now */
#if HAVE_LIBDVDREAD

#include <dvdread/dvd_reader.h>
#include <dvdread/dvd_udf.h>

#define drd_VIDEO_LB_LEN DVD_VIDEO_LB_LEN

/* equivalent types */
#define drd_READ_INFO_FILE DVD_READ_INFO_FILE
#define drd_READ_INFO_BACKUP_FILE DVD_READ_INFO_BACKUP_FILE
#define drd_READ_MENU_VOBS DVD_READ_MENU_VOBS
#define drd_READ_TITLE_VOBS DVD_READ_TITLE_VOBS
typedef dvd_read_domain_t drd_read_t;
typedef dvd_file_t drd_file_t;
typedef dvd_reader_t drd_reader_t;

#else /* HAVE_LIBDVDREAD */

#define drd_VIDEO_LB_LEN 2048

/* equivalent enum type */
typedef enum {
  drd_READ_INFO_FILE,
  drd_READ_INFO_BACKUP_FILE,
  drd_READ_MENU_VOBS,
  drd_READ_TITLE_VOBS
} drd_read_t;
typedef void drd_file_t;
typedef void drd_reader_t;

/* function pointers */
extern drd_reader_t*	(*DVDOpen)(const char*);
extern void	(*DVDClose)(drd_reader_t*);
extern drd_file_t*	(*DVDOpenFile)(drd_reader_t*, int, drd_read_t);
extern void	(*DVDCloseFile)(drd_file_t*);
extern ssize_t  (*DVDReadBlocks)(drd_file_t*, int, size_t, unsigned char*);
extern int	(*DVDFileSeek)(drd_file_t*, int);
extern ssize_t  (*DVDReadBytes)(drd_file_t*, void*, size_t);
extern ssize_t  (*DVDFileSize)(drd_file_t*);
extern int	(*DVDDiscID)(drd_reader_t*, unsigned char*);
extern int	(*DVDUDFVolumeInfo)(drd_reader_t*, char*, unsigned int,
                      unsigned char*, unsigned int);
extern int      (*DVDISOVolumeInfo)(drd_reader_t*, char*, unsigned int,
                      unsigned char*, unsigned int);
extern int      (*DVDUDFCacheLevel)(drd_reader_t*, int);
/* special case: DVDVersion was not in libdvdread 904; this might be NULL */
extern int      (*DVDVersion)(void);
/* proto in dvdread/dvd_udf.h -- reliable published interface? */
extern uint32_t (*UDFFindFile)(drd_reader_t*, char*, uint32_t*);

/* function pointer typedefs to quieten noisy compilers w/ casts */
typedef drd_reader_t*	(*DVDOpen_t)(const char*);
typedef void	(*DVDClose_t)(drd_reader_t*);
typedef drd_file_t*	(*DVDOpenFile_t)(drd_reader_t*, int, drd_read_t);
typedef void	(*DVDCloseFile_t)(drd_file_t*);
typedef ssize_t  (*DVDReadBlocks_t)(drd_file_t*, int, size_t, unsigned char*);
typedef int	(*DVDFileSeek_t)(drd_file_t*, int);
typedef ssize_t  (*DVDReadBytes_t)(drd_file_t*, void*, size_t);
typedef ssize_t  (*DVDFileSize_t)(drd_file_t*);
typedef int	(*DVDDiscID_t)(drd_reader_t*, unsigned char*);
typedef int	(*DVDUDFVolumeInfo_t)(drd_reader_t*, char*, unsigned int,
                      unsigned char*, unsigned int);
typedef int      (*DVDISOVolumeInfo_t)(drd_reader_t*, char*, unsigned int,
                      unsigned char*, unsigned int);
typedef int      (*DVDUDFCacheLevel_t)(drd_reader_t*, int);
/* special case: DVDVersion was not in libdvdread 904; this might be NULL */
typedef int      (*DVDVersion_t)(void);
/* proto in dvdread/dvd_udf.h -- reliable published interface? */
typedef uint32_t (*UDFFindFile_t)(drd_reader_t*, char*, uint32_t*);

/* extern vars */
extern const char drd_defname[];
extern const char drd_altname[];
extern const int  drd_defflags;
extern void* handle;

#endif /* HAVE_LIBDVDREAD */

#endif /* _DL_DRD_H_ */
