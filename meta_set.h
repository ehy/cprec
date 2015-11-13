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

/*
 * The following are helpers for code external to this translation unit.
 *
 * The program has an option to preserve metadata and this is set in
 * extern preserve.
 *
 * where directories or regular files are created, the syscall takes
 * a mode_t argument.  Therefore, let the following provide a value
 * for that argument based on preserve.
 *
 * If we are preserving, mask off group and world bits temporarily, on
 * the premise that prior to successful completion permissions will
 * be set depth-first-recursively from the source modes.  Else, if not
 * preserving then allow umask to work with all bits.
 */

/* return mode_t for regular files per preserve option */
mode_t get_reg_mode(void);

/* return mode_t for directories per preserve option */
mode_t get_dir_mode(void);

#endif /* _META_SET_H_ */
