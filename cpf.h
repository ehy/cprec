/* 
   cpf.[hc] - copy functions

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

#ifndef _CPF_H_
#define _CPF_H_ 1

/* optional region setting */
#define REGM  0x00U    /* unrestricted */
#define REGMA 0xfeU    /* all regions only */
#define REGMN 0x11U    /* restricts Central+South Amer., Oceana, Caribean */
#define REGM2 0xfdU    /* restricts all but region 2 */
extern const unsigned regm;
extern const unsigned regmA;
extern const unsigned regmN;
extern const unsigned regm2;

/* found bad blocks? */
extern unsigned long numbadblk;

void	    copy_all_vobs(drd_reader_t* dvdreader, unsigned char* buf);
ssize_t	    copy_vob(drd_file_t* dvdfile
		, const char* out, unsigned char* buf
		, size_t blkcnt, long* poff);
int	    copy_file(const char* src, const char* dest);
int	    copy_file_force(const char* src, const char* dest);
int	    copy_bup_ifo(char* src, const char* dest);
void	    wr_regmask(char* d, int dlen, unsigned val);

#endif /* _CPF_H_ */
