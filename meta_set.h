/* 
   meta_set.[hc] - filesys metadata functions

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

#ifndef _META_SET_H_
#define _META_SET_H_ 1

/* for final utime setting of dirs tree */
typedef struct _directory {
    unsigned long        ndirs;  /* count of dirs in this dir */
    struct _directory*   pdirs;  /* (re)alloc'd array */
    unsigned long        alloc;  /* count of dirs mem mallocated */
    struct _directory*   ppare;  /* parent */
    struct stat*         sb;     /* status of this dir */
    char*                path;   /* full path name */
} dire_t, * dire_p;
#define REALLOC_dire_t    8
extern dire_p topdir;

/* procedure prototypes */
void        set_f_meta(const char*, const struct stat*);
void        set_d_meta(const char*, const struct stat*);
void        rec_d_meta(dire_p);
void        set_dire_t(const char*, const struct stat*);

#endif /* _META_SET_H_ */
