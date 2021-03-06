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

/* this program's various incs */
#include "hdr_cfg.h"
#include "cprec.h"
#include "lib_misc.h"
#define DL_DRD_INTERN 1
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
void* drd_handle;

DVDOpen_t drd_DVDOpen;
DVDClose_t drd_DVDClose;
DVDOpenFile_t drd_DVDOpenFile;
DVDCloseFile_t drd_DVDCloseFile;
DVDReadBlocks_t drd_DVDReadBlocks;
DVDFileSeek_t drd_DVDFileSeek;
DVDReadBytes_t drd_DVDReadBytes;
DVDFileSize_t drd_DVDFileSize;
DVDDiscID_t drd_DVDDiscID;
DVDUDFVolumeInfo_t drd_DVDUDFVolumeInfo;
DVDISOVolumeInfo_t drd_DVDISOVolumeInfo;
DVDUDFCacheLevel_t drd_DVDUDFCacheLevel;
/* special case: DVDVersion was not in libdvdread 904; this might be NULL */
DVDVersion_t drd_DVDVersion;
/* proto in dvdread/dvd_udf.h -- reliable published interface? */
UDFFindFile_t drd_UDFFindFile;

int
load_drd_syms(void)
{
    int nerr = 0;

    dlerror();

/* dlsym() null return is not strictly an error, but not OK here */
#undef  SYMLOAD
#define SYMLOAD(S, E) \
if ( (drd_##S = (S##_t)dlsym(drd_handle, #S)) == 0 ) { \
  const char* p = dlerror(); \
  nerr += E; \
  pfeall(_("%s: failed on symbol %s: %s\n"), \
      program_name, #S, p ? p : _("true null address")); \
}
    SYMLOAD(DVDOpen, 1)
    SYMLOAD(DVDClose, 1)
    SYMLOAD(DVDOpenFile, 1)
    SYMLOAD(DVDCloseFile, 1)
    SYMLOAD(DVDReadBlocks, 1)
    SYMLOAD(DVDFileSeek, 1)
    SYMLOAD(DVDFileSize, 1)
    SYMLOAD(UDFFindFile, 1)
    /* special optional case: allowed to fail */
    SYMLOAD(DVDVersion, 0)
    /* Not used or optional so do not add to error count.
       If symbol is not optional then change 0 to 1
       and move above this comment.
     */
    SYMLOAD(DVDReadBytes, 0)
    SYMLOAD(DVDDiscID, 0)
    SYMLOAD(DVDUDFVolumeInfo, 0)
    SYMLOAD(DVDISOVolumeInfo, 0)
    SYMLOAD(DVDUDFCacheLevel, 0)
#undef  SYMLOAD

    return nerr;
}

int
close_drd(void)
{
    if ( !drd_handle || dlclose(drd_handle) ) { /* fix-missing-block.sh */
        return -1;
    }
    drd_handle = 0;
    return 0;
}

int
open_drd(const char* drd_soname, int drd_flags)
{
    close_drd();
    drd_handle = dlopen(drd_soname, drd_flags);
    if ( drd_handle == 0 ) {
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
