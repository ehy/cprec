/* 
   lmsc_*.[hc] - library of misc. funcs.

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
#include "lib_misc.h"
#include <string.h>
#include <errno.h>

#if LIB_MISC_TESTING
#   define LIB_MISC_FUNC_PTRS 1
#endif

/* TODO: put x_string funcs in own file */

/*
 * wrap strdup (POSIX) making failure fatal
 * with configurable message
 */
const char* lmsc_x_strdup_failmsg = "strdup() failed";
char* lmsc_x_strdup(const char* src)
{
    char* p = strdup(src);

    if ( p == NULL ) {
        /* lmsc_pf_init_files() does nothing if not needed */
        lmsc_pf_init_files();
        lmsc_pfeall("%s (%s)\n",
            lmsc_x_strdup_failmsg,
            strerror(errno));
        exit(EXIT_FAILURE);
    }

    return p;
}

#if LIB_MISC_FUNC_PTRS

int (*p_lmsc_get_nofd)(int) = lmsc_get_nofd;
int (*p_lmsc_get_max_path)(void) = lmsc_get_max_path;
int (*p_lmsc_get_max_per_path)(const char* pth) = lmsc_get_max_per_path;
int (*p_lmsc_get_page_size)(void) = lmsc_get_page_size;
int (*p_lmsc_xget_page_size)(void) = lmsc_xget_page_size;
nlink_t (*p_lmsc_get_max_hlink)(const char* path) = lmsc_get_max_hlink;
size_t  (*p_lmsc_strcntcpy)(char* dst, const char* src, size_t cnt) = lmsc_strcntcpy;
int   (*p_lmsc_statihack)(const char* fn, char* n, struct stat* sb) = lmsc_statihack;
char* (*p_lmsc_l2U)(char* p) = lmsc_l2U;
char* (*p_lmsc_U2l)(char* p) = lmsc_U2l;
unsigned char* lmsc_mk_aligned_ptr(unsigned char* up, size_t alnmnt);
int (*p_lmsc_s_tol)(const char* str, long* result, char** endp, int base) = lmsc_s_tol;
int (*p_lmsc_pfoopt)(const char*, ...) = lmsc_pfoopt;
int (*p_lmsc_pfoall)(const char*, ...) = lmsc_pfoall;
int (*p_lmsc_pfeopt)(const char*, ...) = lmsc_pfeopt;
int (*p_lmsc_pfeall)(const char*, ...) = lmsc_pfeall;
int (*p_lmsc_pf_dbg)(const char*, ...) = lmsc_pf_dbg;
#if NO_PUTS_MACROS
int (*p_lmsc_oputs)(const char*) = lmsc_oputs;
int (*p_lmsc_aputs)(const char*) = lmsc_aputs;
int (*p_lmsc_eoputs)(const char*) = lmsc_eoputs;
int (*p_lmsc_eputs)(const char*) = lmsc_eputs;
#endif
void (*p_lmsc_pfo_setopt)(int doit) = lmsc_pfo_setopt;
void (*p_lmsc_pfe_setopt)(int doit) = lmsc_pfe_setopt;
void (*p_lmsc_pf_setup)(int dopfo, int dopfe) = lmsc_pf_setup;
void (*p_lmsc_pf_assign_files)(FILE* out, FILE* err) = lmsc_pf_assign_files;
void (*p_lmsc_pf_assign_files_default)(void) = lmsc_pf_assign_files_default;
void (*p_lmsc_pf_init_files)(void) = lmsc_pf_init_files;

#endif /* LIB_MISC_FUNC_PTRS */

#if LIB_MISC_TESTING
int main(int argc, char* argv[])
{
    int r = (*p_lmsc_pfoall)("cur max path==%d\n"
        , get_max_per_path("."));
    pfeall("printed %d chars\n", r);

    return 0;
}
#endif

