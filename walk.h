/* 
   walk.[hc] - tree walking funcs.

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

#ifndef _WALK_H_
#define _WALK_H_ 1

/* saving learned title info in list */
extern int titlecnt;
typedef struct stat vobf_t;
typedef struct titlist {
	struct titlist* pnext, * pprev;
	short  num, chnum;
	short  has_ifo, has_bup;
	vobf_t vobs[10];
	vobf_t ifos[1];
	vobf_t bups[1];
} titlist_t, * titlist_p;

extern titlist_p tit0;

/* set when walking in VIDEO_TS */
extern unsigned int  invid;
/* set when vob files are found */
extern unsigned int  okvid;

/* procedure prototypes */
void walk(void);
int  handle_file(const char* file, const struct stat* sb, int flag);
void freevidentries(void);
int  get_max_videntry(void);

#endif /* _WALK_H_ */
