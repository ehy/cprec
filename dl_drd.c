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

#include "config.h"

/* this program's various incs */
#include "hdr_cfg.h"
#include "cprec.h"
#include "lib_misc.h"
#include "dl_drd.h"

#if HAVE_LIBDVDREAD

int
load_drd_syms(void)
{
	return 0;
}

int
close_drd(void)
{
	return 0;
}

int
open_drd(const char* drd_soname, int drd_flags)
{
	return 0;
}

int
open_drd_default(void)
{
	return 0;
}

int
get_drd_defflags(void)
{
	return 0;
}

#else /* HAVE_LIBDVDREAD */
#if ! HAVE_DLFCN_H
#error "FIXME: no dlfcn.h: how is runtime loading done?"
#endif
#if ! HAVE_DLSYM
#error "FIXME: no dlsym(): how is runtime loading done?"
#endif
/* loader */
#include <dlfcn.h>

const char drd_defname[] = "libdvdread.so.3";
const char drd_altname[] = "libdvdread.so";
const int  drd_defflags  = RTLD_LAZY;
void* handle;

drd_reader_t*    (*DVDOpen)(const char*);
void     (*DVDClose)(drd_reader_t*);
drd_file_t*    (*DVDOpenFile)(drd_reader_t*, int, drd_read_t);
void     (*DVDCloseFile)(drd_file_t*);
ssize_t  (*DVDReadBlocks)(drd_file_t*, int, size_t, unsigned char*);
int      (*DVDFileSeek)(drd_file_t*, int);
ssize_t  (*DVDReadBytes)(drd_file_t*, void*, size_t);
ssize_t  (*DVDFileSize)(drd_file_t*);
int      (*DVDDiscID)(drd_reader_t*, unsigned char*);
int      (*DVDUDFVolumeInfo)(drd_reader_t*, char*, unsigned int,
                      unsigned char*, unsigned int);
int      (*DVDISOVolumeInfo)(drd_reader_t*, char*, unsigned int,
                      unsigned char*, unsigned int);
int      (*DVDUDFCacheLevel)(drd_reader_t*, int);
/* special case: DVDVersion was not in libdvdread 904; this might be NULL */
int      (*DVDVersion)(void);
/* proto in dvdread/dvd_udf.h -- reliable published interface? */
uint32_t (*UDFFindFile)(drd_reader_t*, char*, uint32_t*);

int
load_drd_syms(void)
{
	int nerr = 0;

	dlerror();

/* dlsym() null return is not strictly an error, but not OK here */
#undef  SYMLOAD
#define SYMLOAD(S, C, E) \
if ( (S = (C)dlsym(handle, #S)) == 0 ) { \
  const char* p = dlerror(); \
  nerr += E; \
  pfeall(_("%s: failed on symbol %s: %s\n"), \
  	program_name, #S, p ? p : _("true null address")); \
}
	SYMLOAD(DVDOpen, DVDOpen_t, 1)
	SYMLOAD(DVDClose, DVDClose_t, 1)
	SYMLOAD(DVDOpenFile, DVDOpenFile_t, 1)
	SYMLOAD(DVDCloseFile, DVDCloseFile_t, 1)
	SYMLOAD(DVDReadBlocks, DVDReadBlocks_t, 1)
	SYMLOAD(DVDFileSeek, DVDFileSeek_t, 1)
	SYMLOAD(DVDFileSize, DVDFileSize_t, 1)
	SYMLOAD(UDFFindFile, UDFFindFile_t, 1)
	/* special optional case: leave this last among used symbols */
	SYMLOAD(DVDVersion, DVDVersion_t, 0)
	/* Not used or optional so do not add to error count.
	   If symbol is not optional then change 0 to 1
	   and move above this comment.
	 */
	SYMLOAD(DVDReadBytes, DVDReadBytes_t, 0)
	SYMLOAD(DVDDiscID, DVDDiscID_t, 0)
	SYMLOAD(DVDUDFVolumeInfo, DVDUDFVolumeInfo_t, 0)
	SYMLOAD(DVDISOVolumeInfo, DVDISOVolumeInfo_t, 0)
	SYMLOAD(DVDUDFCacheLevel, DVDUDFCacheLevel_t, 0)
#undef  SYMLOAD

	return nerr;
}

int
close_drd(void)
{
	if ( !handle || dlclose(handle) )
		return -1;
	handle = 0;
	return 0;
}

int
open_drd(const char* drd_soname, int drd_flags)
{
	close_drd();
	handle = dlopen(drd_soname, drd_flags);
	if ( handle == 0 ) {
		const char* p = dlerror();
		pfeall(_("%s: failed loading %s: %s\n"),
			program_name, drd_soname, p?p:_("unknown error"));
		return -1;
	}
	return 0;
}

int
open_drd_default(void)
{
	return open_drd(drd_defname, drd_defflags);
}

int
get_drd_defflags(void)
{
	return drd_defflags;
}

#endif /* HAVE_LIBDVDREAD */
