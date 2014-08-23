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

#include "hdr_cfg.h"

/* this program's various incs */
#include "cprec.h"
#include "meta_set.h"
#include "path_set.h"
#include "lib_misc.h"
#include "walk.h"
#undef   ftw
#include "apue_ftw.h"
#define  ftw apue_ftw
#include "dl_drd.h"
#include "cpf.h"
#include "ino.h"
#include "block_hash.h"
#include "xmalloc.h"

#define GOT_FAIL	-1
#define GOT_F	   1
#define GOT_D	   2
#define GOT_DNR	 3
#define GOT_SL	  4
#define GOT_HL	  5
#define GOT_NS	  6
#define GOT_ERRS	7
#define GOT_ERRD	8


static int  ftwcb(const char*, const struct stat*, int);
static int
setvidentry(const char* nam, const char* path, const struct stat* sb);

/* saving learned title info in list */
int titlecnt = 0;
titlist_p tit0;
unsigned long cnt = 0;
/* set when walking in VIDEO_TS */
unsigned int  invid = 0;
/* set when vob files are found */
unsigned int  okvid = 0;

void
walk(void)
{
	int nofd;

	nofd = get_nofd(nfdresv);
	if ( nofd == 0 ) {
		pfeall(_("%s: no files!\n"), program_name);
		exit(1);
	}
	if ( nofd < 0 ) {
		pfeall(_("%s: too few files (%d)!\n"), program_name, 0 - nofd);
		exit(1);
	}
	nofd = MIN(nofd, nfdmax);

	switch ( ftw(mntd, ftwcb, nofd) ) {
		case GOT_DNR:
			pfeall(_("%s: got unreadable directory (FTW_DNR)\n")
				, program_name);
			if ( force )
				break;
			exit(1);

		case GOT_NS:
			pfeall(_("%s: got un-stat()able entry (FTW_NS)\n")
				, program_name);
			if ( force )
				break;
			exit(1);

		case GOT_SL:
			pfeall(_("%s: symbolic link error walking hierarchy\n")
				, program_name);
			if ( force )
				break;
			exit(1);

		 case GOT_HL:
			pfeall(_("%s: hard link error walking hierarchy\n")
				, program_name);
			if ( force )
				break;
			exit(1);

		case GOT_ERRS:
			pfeall(_("%s: source error walking hierarchy\n")
				, program_name);
			if ( force )
				break;
			exit(1);

		case GOT_ERRD:
			pfeall(_("%s: destination error walking hierarchy\n")
				, program_name);
			if ( force )
				break;
			exit(1);

		case GOT_FAIL:
			pfeall(_("%s: failure walking hierarchy\n")
				, program_name);
			if ( force )
				break;
			exit(1);
		default:
			break;
	}
}

int
get_max_videntry(void)
{
	titlist_p pl;
	int r = -1;

	for ( pl = tit0; pl != NULL; pl = pl->pnext ) {
		r = MAX(r, pl->chnum);
	}

	return r;
}

void
freevidentries(void)
{
	titlist_p pl = tit0;
	while ( pl ) {
		titlist_p p2 = pl->pnext;
		free(pl);
		pl = p2;
	}
	tit0 = NULL;
	titlecnt = okvid = 0;
}

static int
setvidentry(const char* nam, const char* path, const struct stat* sb)
{
	int i, j;
	long l;
	const char* p;
	char* ep;
	titlist_p pl, plast;
	int is_vob = 0, is_ifo = 0, is_bup = 0;

	if ( strncasecmp(nam, "VTS_", 4) ) {
		pf_dbg(_("dbg %s: setvidentry called with %s, %s\n"),
			program_name, nam, path);
		return -1;
	}
	p = nam + 4;
	if ( s_tol(p, &l, &ep, 10) ) {
		pf_dbg(_("dbg %s: setvidentry long int %ld: %s: %s\n"),
			program_name, l, nam, strerror(errno));
		return -1;
	}
	if ( l < 0 || l >= 100 ) {
		pf_dbg(_("dbg %s: setvidentry long int %ld: %s\n"),
			program_name, l, nam);
		return -1;
	}
	if ( *ep != '_' ) {
		pf_dbg(_("dbg %s: setvidentry called with %s, %s (%s)\n"),
			program_name, nam, path, ep?ep:"NULL");
		return -1;
	}
	i = (int)l;
	p = ep + 1;
	if ( s_tol(p, &l, &ep, 10) ) {
		pf_dbg(_("dbg %s: setvidentry long int %ld: %s: %s\n"),
			program_name, l, nam, strerror(errno));
		return -1;
	}
	if ( l < 0 || l >= 10 ) {
		pf_dbg(_("dbg %s: setvidentry long int %ld: %s\n"),
			program_name, l, nam);
		return -1;
	}
	if ( !ep || (strcasecmp(ep, ".VOB")
		&& strcasecmp(ep, ".IFO") && strcasecmp(ep, ".BUP") ) ) {
		pf_dbg(_("dbg %s: setvidentry called with %s, %s (%s)\n"),
			program_name, nam, path, ep?ep:"NULL");
		return -1;
	}
	j = (int)l;
	if ( !strcasecmp(ep, ".IFO") ) {
		is_ifo = 1;
	} else if ( !strcasecmp(ep, ".BUP") ) {
		is_bup = 1;
	} else if ( !strcasecmp(ep, ".VOB") ) {
		is_vob = 1;
	}

	if ( tit0 == NULL ) {
		tit0 = xmalloc(sizeof(titlist_t));
		tit0->pprev = tit0->pnext = NULL;
		tit0->chnum = i;
		tit0->num = -1;
		tit0->has_ifo = 0;
		tit0->has_bup = 0;
		titlecnt = 1;
	}

	pl = tit0;
	plast = NULL;

	do {
		if ( pl->chnum == i )
			break;
		plast = pl;
	} while ( (pl = pl->pnext) != NULL );

	if ( pl == NULL ) { /* not found */		
		pl = xmalloc(sizeof(titlist_t));
		pl->pprev = plast;
		pl->pnext = NULL;
		pl->chnum = i;
		pl->num = -1;
		pl->has_ifo = 0;
		pl->has_bup = 0;
		if ( plast != NULL )
			plast->pnext = pl;
		titlecnt++;
	}

	if ( is_ifo && j == 0 ) {
		memcpy(&(pl->ifos[0]), sb, sizeof(struct stat));
		pl->has_ifo = 1;
	} else if ( is_bup && j == 0 ) {
		memcpy(&(pl->bups[0]), sb, sizeof(struct stat));
		pl->has_bup = 1;
	} else if ( is_vob ) {
		memcpy(&(pl->vobs[j]), sb, sizeof(struct stat));
	}
	pl->num = MAX(pl->num, j);

	pf_dbg(_("dbg %s: setvidentry did set %02d,%d %s\n"),
		program_name, i, j, path);

	return 0;
}

static int
ftwcb(const char* file, const struct stat* sb, int flag)
{
	size_t		sz;
	const char*	psrc;
	char*		pdst;

	++cnt;

	psrc = &file[mntdlen];

	if ( *psrc == '/' ) {
		/* contents of first callback w/ ftw(arg) */
		int l;

		if ( mntdlen > 0 && mntd[mntdlen - 1] == '/' ) {
			--mntdlen;
		}

		l = (int)mntdbufdlen - mntdlen - 1;
		if ( l <= 0 ) {
			mntd[mntdlen] = '\0';
			pfeall(_("%s: source name error: %s\n"),
				program_name, mntd);
			return GOT_ERRS;
		}
		psrc = &file[mntdlen + 1];
		mntd[mntdlen] = '/';
		sz = strlcpy(&mntd[mntdlen + 1], psrc, l);
		if ( sz >= l ) {
			pfeall(_("%s: found source name too long (%ld): %s\n"),
				program_name, (long)sz, psrc);
			return GOT_ERRS;
		}

		if ( outdlen > 0 && outd[outdlen - 1] == '/' ) {
			--outdlen;
		}

		l = (int)outdbufdlen - outdlen - 1;
		if ( l <= 0 ) {
			outd[outdlen] = '\0';
			pfeall(_("%s: target name error: %s\n"),
				program_name, outd);
			return GOT_ERRD;
		}
		pdst = &outd[outdlen];
		*pdst++ = '/';
		sz = strlcpy(pdst, psrc, l);
		if ( sz >= l ) {
			pfeall(
			_("%s: found destination name too long (%ld): %s\n"),
				program_name, (long)sz, psrc);
			outd[outdlen] = '\0';
			return GOT_ERRD;
		}
	} else {
		/* first callback w/ ftw(arg) itself */
		psrc = file;
		pdst = outd;
	}

	if ( !simple_copy && strncmp(psrc, "VIDEO_TS", sizeof("VIDEO_TS")-1)
		&&  strncmp(psrc, "video_ts", sizeof("video_ts")-1) ) {
		pf_dbg(_("dbg: unset invid for %s, %s\n"), psrc, file);
		invid  = 0;
	}

	if ( !simple_copy && invid && !ign_lc )
		l2U(pdst);

	if ( flag == FTW_D ) {
		if ( !simple_copy &&
		     (!strcmp(psrc, "VIDEO_TS") ||
		     !strcmp(psrc, "video_ts")) ) {
			pf_dbg(_("dbg: set invid for %s, %s\n"), psrc, file);
			invid  = 1;
			if ( !ign_lc )
				l2U(pdst);
			if ( desired_title ) {
				/* do not mkdir */
				pf_dbg(_("dbg: no mkdir(\"%s\")\n"), outd);
				return 0;
			}
		}
	}

	/* with a -d selection ignore all but dvd video items */
	if ( okvid && !simple_copy && !invid && desired_title )
		return 0;

	pf_dbg(_("dbg: mntd \"%s\" outd \"%s\"\n"), mntd, outd);
	return handle_file(file, sb, flag);
}

int
handle_file(const char* file, const struct stat* sb, int flag)
{
	int e, r;

	/* try hard link handling for non-directories */
	if ( sb->st_nlink > 1 && !ign_hl
		&& flag != FTW_D && flag != FTW_NS && flag != FTW_DNR ) {
		const IDP* p = ino_check(sb, outd);

		if ( p == NULL ) {
			/* should not happen */
			pfeall(_("%s: failed hard link handling of %s\n"),
				program_name, mntd);
			return GOT_HL;
		} else if ( p->id_count == 1 ) {
			/* 1st seen with this inode,device pair */
			pfoopt(_("found %s with %llu hard links\n"),
				mntd, CAST_ULL(sb->st_nlink));
			/* fall through and copy */
		} else if ( p->id_count < get_max_hlink(p->id_path0) ) {
			/* p holds 1st name associated with
			 * this inode,device pair
			 * link instead of copy
			 */
			pfoopt(_("hard link %s to %s, %llu of %llu\n"),
				outd, p->id_path0,
				CAST_ULL(p->id_count),
				CAST_ULL(p->id_nlink));

			if ( want_dry_run ) {
				return 0;
			}

			if ( link(p->id_path0, outd) ) {
				pfeall(_("%s: failed link(%s, %s): %s\n"),
					program_name, p->id_path0, outd, strerror(errno));
				if ( !force )
					return GOT_HL;
				pfoopt(_("%s: copy %s, failed link to %s\n"),
					program_name, outd, p->id_path0);
				/* fall through and copy */
			}

			return 0;
		} else {
			/* get_max_hlink(p->id_path0) too few */
			pfeopt(
				_("cannot hard link %s to %s, %llu %s %lld links\n"),
				outd, p->id_path0,
				CAST_ULL(p->id_count),
				_("greater than maximum"),
				CAST_LL(get_max_hlink(p->id_path0)));
			if ( !force )
				return GOT_HL;
			/* fall through and copy */
		}
	}

	switch ( flag ) {
	case FTW_D:
		pfoopt(_("mkdir %s\n"), outd);

		if ( want_dry_run )
			break;

		if ( (r = mkdir(outd, 0777)) && (e = errno) != EEXIST ) {
			pfeopt(_("%s: mkdir(%s) failed - %s\n"),
				program_name, outd, strerror(e));
			if ( !force )
				return GOT_ERRD;
		} else if ( r ) {
			pfeopt(_("%s: mkdir(%s) failed - %s\n"),
				program_name, outd, strerror(e));
			if ( force )
				chmod(outd, sb->st_mode | 0700);
		}
		if ( force ) {
			pf_dbg(_("dbg: chmod(%s, |0700) == %d\n"),
				outd, chmod(outd, sb->st_mode | 0700));
		}

		set_dire_t(outd, sb);
		break;

	case FTW_DNR:
		if ( ign_dnr )
			pfeopt(_("%s: unreadable directory %s\n"),
				program_name, file);
		else {
			pfeall(_("%s: unreadable directory %s\n"),
				program_name, file);
			return GOT_DNR;
		}
		break;

	case FTW_F:
		/* first: handle non-regular files */
		/* FIXME: needs work to handle various
		 * special types, e.g. BSD whiteouts.
		 * default fall through to reg. file code.
		 */
		if ( !S_ISREG(sb->st_mode) &&
			(S_ISBLK(sb->st_mode) ||
			S_ISCHR(sb->st_mode) ||
			S_ISFIFO(sb->st_mode) ||
			S_ISSOCK(sb->st_mode))
		) {
			/* no sockets */
			if ( S_ISSOCK(sb->st_mode) ) {
				pfeall(_("%s: ignoring socket %s\n"),
					program_name, file);
				/* no failure for sockets */
				break;
			}

			if ( ign_sf ) {
				pfoopt(_("%s: ignoring special file %s\n"),
					program_name, file);
				/* no failure by option */
				break;
			}

			if ( want_dry_run )
				break;

#if HAVE_MKFIFO
			if ( S_ISFIFO(sb->st_mode) ) {
				pfoopt(_("%s: creating fifo %s\n"),
					program_name, outd);

				if ( mkfifo(outd, sb->st_mode) ) {
					pfeall(_("%s: failed fifo %s - %s\n"),
						program_name, outd, strerror(errno));
					if ( !force )
						return GOT_FAIL;
				} else {
					/* try preserving metadata --
					   never fatal on error
					 */
					set_f_meta(outd, sb);
				}
				break;
			}
#endif

			pfoopt(_("%s: creating device node %s\n"),
				program_name, outd);

			if ( mknod(outd, sb->st_mode, sb->st_rdev) ) {
				pfeall(_("%s: failed device node %s - %s\n"),
					program_name, outd, strerror(errno));
				if ( !force )
					return GOT_FAIL;
			} else
				/* try preserving metadata --
				   never fatal on error
				 */
				set_f_meta(outd, sb);

			break;
		} else if ( !S_ISREG(sb->st_mode) ) {
			pfeall(_("%s: ignoring special file %s\n"),
				program_name, file);
			break;
		}

		/* a regular file . . . */
		if ( !simple_copy && invid ) {
			const char* q = strrchr(file, '/');
			const char* p = strrchr(file, '.');

			if ( q == NULL )
				q = "";
			else
				q++;

			if ( p == NULL )
				p = "";

			if ( desired_title && desired_title < 100
			  && (!strcasecmp(p, ".IFO")
			   || !strcasecmp(p, ".BUP")) ) {
				/* in this case the user selected vobs
				 * specifically, and ifo are not copied
				 */
				break;
			}

			if ( !strcasecmp(p, ".VOB")
			  || !strcasecmp(p, ".IFO")
			  || !strcasecmp(p, ".BUP") ) {
				if ( !strncasecmp(q, "VIDEO_TS.", 9)
				  || !setvidentry(q, mntd, sb) ) {
					okvid = 1;
					break;
				} else {
					pfeall(_("%s: "
					  "found \"%s\" in "
					  "VIDEO_TS directory\n"),
					  program_name, file);
				}
			}
		}

		pfoopt(_("copy file to %s\n"), outd);

		if ( want_dry_run )
			break;

		if ( copy_file(mntd, outd) ) {
			if ( !simple_copy && do_ioerrs ) {
				if ( !copy_bup_ifo(mntd, outd) )
					break;
			}

			pfeall(_("%s: failed copy %s to %s\n"),
				program_name, mntd, outd);
			return GOT_FAIL;
		}
		break;

	case FTW_NS:
		if ( ign_ns ) {
			pfeopt(_("%s: stat() failed on %s\n"),
				program_name, file);
		} else {
			pfeall(_("%s: stat() failed on %s\n"),
				program_name, file);
			return GOT_NS;
		}
		break;

	case FTW_SL:
		if ( ign_sl ) {
			pfeopt(_("%s: symbolic link %s; copying target\n"),
				program_name, file);

			if ( want_dry_run )
				break;

			if ( copy_file(mntd, outd) ) {
				pfeall(_("%s: failed copy %s to %s\n"),
					program_name, mntd, outd);
				return GOT_FAIL;
			}
		}

		#if HAVE_READLINK && HAVE_SYMLINK
		else {
			int r = readlink(file, nbuf, nbufbufdlen - 1);
			if ( r == -1 ) {
				pfeall(_("%s: failed readlink(%s,,): %s\n"),
					program_name, file, strerror(errno));
				return GOT_SL;
			}
			nbuf[r] = '\0';
			pfoopt(_("symlink %s to %s\n"), outd, nbuf);

			if ( want_dry_run )
				break;

			if ( symlink(nbuf, outd) ) {
				if ( errno == EEXIST && ign_ex )
					break;
				pfeall(_("%s: failed symlink(%s, %s): %s\n"),
					program_name, nbuf, outd, strerror(errno));
				return GOT_SL;
			} else {
				/* try preserving metadata --
				   never fatal on error
				 */
				set_f_meta(outd, sb);
			}
		}
		#else
		else {
			pfeall(_("%s: unexpected symbolic link %s\n"),
				program_name, file);
			return GOT_SL;
		}
		#endif
		break;
	default:
		pfeall(_("%s: unknown flag %d for %s\n"),
			program_name, flag, file);
		return GOT_FAIL;
	}

	return 0;
}
