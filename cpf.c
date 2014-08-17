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

#include "hdr_cfg.h"

#if ! HAVE_STDINT_H
typedef u_int64_t uint64_t;
typedef u_int32_t uint32_t;
#endif

/* this program's various incs */
#include "cprec.h"
#include "meta_set.h"
#include "path_set.h"
#include "walk.h"
#include "lib_misc.h"
#include "dl_drd.h"
#include "block_hash.h"
#include "xmalloc.h"
#include "cpf.h"

/* region code stuff */
#define VMGIDLEN 12              /* 1st 12: 'DVDVIDEO-VMG' */
#define CATOFF   0x00000022LU    /* vmg category offset */
#define CATRD    4U              /* vmg category read size */

const unsigned regm  = REGM;
const unsigned regmA = REGMA;
const unsigned regmN = REGMN;
const unsigned regm2 = REGM2;

const size_t blk_sz = drd_VIDEO_LB_LEN;

/* found bad blocks? */
unsigned long numbadblk = 0;

/* these pairs are used in ifo copy error handling */
struct { const char* c, * r; } ifo_cmps[] = {
	{ "BUP", "IFO" }, { "bup", "ifo" },
	{ "IFO", "BUP" }, { "ifo", "bup" }
};

/* static procedures */
static int disc_block_check(uint32_t blk, const char* nbuf, uint32_t fsz);
static ssize_t copy_vob_badblks(drd_file_t* dvdfile
		, const char* outfname
		, int infd, int outfd
		, unsigned char* buf
		, size_t blkcnt, long* poff);
static ssize_t copy_vob_fd(drd_file_t* dvdfile
		, const char* outfname
		, int infd, int outfd
		, unsigned char* buf
		, size_t blkcnt, long* poff);

/* string safety return checks; fatal err */
#define SCPYCHK(d, s, c) \
	{ \
		size_t n = c; \
		if ( n <= strlcpy(d, s, n) ) { \
			pfeall( \
				_("%s: internal string error in pointer or size (line %u)\n"), \
				program_name, __LINE__); \
			exit(60); \
		} \
	}
/* for snprintf into nbuf: use as NBP((args to snprintf)), no ; */
#define NBP(ARGS) \
	{ \
		int n = snprintf ARGS ; \
		if ( n >= nbufbufdlen || n < 0 ) { \
			pfeall( \
				_("%s: internal string error in pointer or size (line %u)\n"), \
				program_name, __LINE__); \
			exit(60); \
		} \
	}
/* for snprintf into 'pn', a pointer into mntd -- as above macro */
#define PNP(ARGS) \
	{ \
		int c = (int)PNREM; int n = snprintf ARGS ; \
		if ( n <= c || n < 0 ) { \
			pfeall( \
				_("%s: internal string error in pointer or size (line %u)\n"), \
				program_name, __LINE__); \
			exit(60); \
		} \
	}

/* flags to open output files */
#define OPENFL O_RDWR|O_CREAT|O_EXCL|O_TRUNC|O_NOFOLLOW|O_LARGEFILE

void
copy_all_vobs(drd_reader_t* dvdreader, unsigned char* buf)
{
	titlist_p	pt;
	long		i1;
	struct stat	sb;
	drd_read_t	dom;
	char*		pn;
	int		i, j, maxtitle, do0;
	drd_file_t*	dvdfile = NULL;
	ssize_t		nblk = 0;
	unsigned long	ifo_badbl = 0, bup_badbl = 0;

	/* If no vobs were found then don't bother */
	if ( !okvid ) {
		pf_dbg(_("dbg: copy_all_vobs() with no vobs (%s)\n"),
			mntd);
		return;
	}
	/* If paths are unreasonable we cannot proceed */
	if ( expaths ) {
		pfeopt(_("%s: paths are too long - \"%s\", \"%s\"\n"),
			program_name, mntd, outd);
		return;
	}

	/* pn is a pointer into a buffer: careful with this! */
	#define PNREM ((size_t)MAX((ssize_t)0, ((ssize_t)mntdbufdlen - (ssize_t)(pn - mntd))))
	pn = &mntd[mntdlen];
	*pn++ = '/';
	*pn = '\0';

	/* 'desired_title' is user selection with -d, default 0,
	 * meaning `all' so VIDEO_TS/VIDEO_TS.VOB is included;
	 * 100 means only that and none of the numbered vobs;
	 * anything else (clamped at arg parsing) selects numbered
	 * vob so VIDEO_TS/VIDEO_TS.VOB is excluded
	 */
	do0 = 0;
	if ( desired_title == 100 || desired_title == 0 ) {
		do0 = 1;
	}

	if ( do0 ) {
		const char*	fnstr[3] = {
			"VIDEO_TS/VIDEO_TS.IFO",
			"VIDEO_TS/VIDEO_TS.BUP",
			"VIDEO_TS/VIDEO_TS.VOB"
		};
		const char*	fmtsl[3] = {
			"%s/video_ts.ifo",
			"%s/video_ts.bup",
			"%s/video_ts.vob"
		};
		const char*	fmtsu[3] = {
			"%s/VIDEO_TS.IFO",
			"%s/VIDEO_TS.BUP",
			"%s/VIDEO_TS.VOB"
		};
		drd_read_t	doms[3] = {
			drd_READ_INFO_FILE,
			drd_READ_INFO_BACKUP_FILE,
			drd_READ_MENU_VOBS
		};
		uint32_t blk, fsz;

		for ( i = desired_title == 0 ? 0 : 2; i < 3; i++ ) {
		SCPYCHK(pn, fnstr[i], PNREM);
		if ( statihack(mntd, pn, &sb) ) {
			if ( errno == ENOENT ) {
				pfeopt(_("%s: %s does not exist\n"),
					program_name, mntd);
				continue;
			} else {
				pfeall(_("%s: failed to stat() %s - %s\n"),
					program_name, mntd, strerror(errno));
				if ( force ) {
					continue;
				} else {
					DVDClose(dvdreader);
					exit(1);
				}
			}
		}

		if ( strcmp(pn, fnstr[i]) ) {
			NBP((nbuf, nbufbufdlen,
				ign_lc ? fmtsl[i] : fmtsu[i], vidd))
			fnlower = 1;
		} else {
			NBP((nbuf, nbufbufdlen, fmtsu[i], vidd))
		}

		pfoopt(_("X %s size %zu\n"), nbuf, sb.st_size);

		/* check for multiple 'links' to file; 1st seen 2010 */
		blk = UDFFindFile(dvdreader, pn-1, &fsz);
		if ( blk ) {
			int r = disc_block_check(blk, nbuf, fsz);
			if ( r > 0 ) {
				if ( !force || r >= 10 )
					exit(r);
				pfeall(_(
				  "%s: continuing due to force option, "
				  "but output might be very large, and "
				  "might not make a proper UDF fs.\n"),
				  program_name);
			} else if ( r < 0 ) {
				continue;
			}
		}

		errno = 0;
		dom = doms[i];
		dvdfile = DVDOpenFile(dvdreader, 0, dom);
		if ( dvdfile == 0 ) {
			/* hoping errno is relevant */
			pfeall(_("%s: failed opening %s - %s\n"),
			  program_name, fnstr[i], strerror(errno));
			if ( force )
				continue;
			DVDClose(dvdreader);
			exit(5);
		}

		if ( (nblk = DVDFileSize(dvdfile)) < 0 ) {
			pfeall(_("%s: failed getting block size of %s\n"),
				program_name, nbuf);
			DVDCloseFile(dvdfile);
			if ( force )
				continue;
			DVDClose(dvdreader);
			exit(6);
		}

		i1 = 0;
		if ( !want_dry_run ) {
		if ( copy_vob(dvdfile, nbuf, buf, nblk, &i1) != nblk ) {
			pfeall(
			  _("%s: failed \"%s\" copy (%ld blocks)\n"),
			  program_name, fnstr[i], (long)nblk);
			DVDCloseFile(dvdfile);
			if ( force )
				continue;
			DVDClose(dvdreader);
			exit(7);
		}
		}

		DVDCloseFile(dvdfile);

		/* try preserving metadata -- never fatal on error */
		set_f_meta(nbuf, &sb);

		} /* for ( i = desired_title == 0 ? 0 : 2; [...] */
	} /* do0 */

	i = desired_title;
	maxtitle = get_max_videntry() + 1;
	if ( i == 0 ) {
		/* user/default selection of all vobs */
		i = 1;
	} else if ( i < 100 ) {
		/* user selection of numbered vobs, 100 excluding all */
		maxtitle = MIN(maxtitle, i + 1);
	}
	for ( ; i < maxtitle; i++ ) {
		do0 = 1;

		for ( pt = tit0; pt != NULL; pt = pt->pnext ) {
			if ( pt->chnum == i )
				break;
		}
		
		if ( pt == NULL ) /* done */
			continue;

		/* do IFO */
                while ( do0 && pt->has_ifo ) {
		uint32_t blk, fsz;

		PNP((pn, PNREM, "VIDEO_TS/VTS_%02d_%d.IFO", i, 0))
		if ( statihack(mntd, pn, &(pt->ifos[0])) ) {
			if ( errno == ENOENT ) {
				do0 = 0;
			} else {
				perror(mntd);
				pfeall(_("%s: failed stat(%s) - %s\n"),
					program_name, mntd, strerror(errno));
				if ( force )
					do0 = 0;
				else
					exit(1);
			}
		}

		if ( fnlower && ign_lc )
			NBP((nbuf, nbufbufdlen, "%s/vts_%02d_%d.ifo", vidd, i, 0))
		else
			NBP((nbuf, nbufbufdlen, "%s/VTS_%02d_%d.IFO", vidd, i, 0))

		pfoopt(_("X %s size %zu\n"), nbuf, pt->ifos[0].st_size);

		/* check for multiple 'links' to file; 1st seen 2010 */
		blk = UDFFindFile(dvdreader, pn-1, &fsz);
		if ( blk ) {
			int r = disc_block_check(blk, nbuf, fsz);
			if ( r > 0 ) {
				if ( !force || r >= 10 )
					exit(r);
				pfeall(_(
				  "%s: continuing due to force option, "
				  "but output might be very large, and "
				  "might not make a proper UDF fs.\n"),
				  program_name);
			} else if ( r < 0 ) {
				break;
			}
		}

		dom = drd_READ_INFO_FILE;
		dvdfile = DVDOpenFile(dvdreader, i, dom);
		if ( dvdfile == 0 ) {
			pfeall(_("%s: failed opening IFO of title %d\n"),
				program_name, i);
			if ( force )
				break;
			DVDClose(dvdreader);
			exit(8);
		}

		if ( (nblk = DVDFileSize(dvdfile)) < 0 ) {
			pfeall(_("%s: failed getting block size of %s\n"),
				program_name, nbuf);
			DVDCloseFile(dvdfile);
			if ( force )
				break;
			DVDClose(dvdreader);
			exit(9);
		}

		i1 = 0;
		ifo_badbl = numbadblk;
		if ( copy_vob(dvdfile, nbuf, buf, nblk, &i1) != nblk ) {
			pfeall(_("%s: failed in IFO copy (%ld blocks)\n"),
				program_name, (long)nblk);
			DVDCloseFile(dvdfile);
			if ( force )
				break;
			DVDClose(dvdreader);
			exit(10);
		}
		ifo_badbl = numbadblk - ifo_badbl;

		DVDCloseFile(dvdfile);

		/* try preserving metadata -- never fatal on error */
		set_f_meta(nbuf, &(pt->ifos[0]));
		break;
		} /* do0 */
                /* end do IFO */	

		/* do BUP */
                while ( do0 && pt->has_bup ) {
		uint32_t blk, fsz;

		PNP((pn, PNREM, "VIDEO_TS/VTS_%02d_%d.BUP", i, 0))
		if ( statihack(mntd, pn, &(pt->bups[0])) ) {
			if ( errno == ENOENT ) {
				do0 = 0;
			} else {
				perror(mntd);
				pfeall(_("%s: failed stat(%s) - %s\n"),
					program_name, mntd, strerror(errno));
				if ( force )
					do0 = 0;
				else
					exit(1);
			}
		}

		if ( fnlower && ign_lc )
			NBP((nbuf, nbufbufdlen, "%s/vts_%02d_%d.bup", vidd, i, 0))
		else
			NBP((nbuf, nbufbufdlen, "%s/VTS_%02d_%d.BUP", vidd, i, 0))

		pfoopt(_("X %s size %zu\n"), nbuf, pt->bups[0].st_size);

		/* check for multiple 'links' to file; 1st seen 2010 */
		blk = UDFFindFile(dvdreader, pn-1, &fsz);
		if ( blk ) {
			int r = disc_block_check(blk, nbuf, fsz);
			if ( r > 0 ) {
				if ( !force || r >= 10 )
					exit(r);
				pfeall(_(
				  "%s: continuing due to force option, "
				  "but output might be very large, and "
				  "might not make a proper UDF fs.\n"),
				  program_name);
			} else if ( r < 0 ) {
				break;
			}
		}

		dom = drd_READ_INFO_BACKUP_FILE;
		dvdfile = DVDOpenFile(dvdreader, i, dom);
		if ( dvdfile == 0 ) {
			pfeall(_("%s: failed opening BUP of title %d\n"),
				program_name, i);
			if ( force )
				break;
			DVDClose(dvdreader);
			exit(8);
		}

		if ( (nblk = DVDFileSize(dvdfile)) < 0 ) {
			pfeall(_("%s: failed getting block size of %s\n"),
				program_name, nbuf);
			DVDCloseFile(dvdfile);
			if ( force )
				break;
			DVDClose(dvdreader);
			exit(9);
		}

		i1 = 0;
		bup_badbl = numbadblk;
		if ( copy_vob(dvdfile, nbuf, buf, nblk, &i1) != nblk ) {
			pfeall(_("%s: failed in BUP copy (%ld blocks)\n"),
				program_name, (long)nblk);
			DVDCloseFile(dvdfile);
			if ( force )
				break;
			DVDClose(dvdreader);
			exit(10);
		}
		bup_badbl = numbadblk - bup_badbl;

		DVDCloseFile(dvdfile);

		/* If both ifo and bup are damaged, that's bad.  Vobs
		 * can have some bad or zeroed blocks, and any machine
		 * should recover, but the ifo's have the important code
		 * and data for playing the set; hence, the backup bup.
		 * Continue anyway if force in effect (disc might still
		 * be usable, e.g. ifo is not part of main titleset).
		 */
		if ( ifo_badbl && bup_badbl ) {
			pfeall(_("%s: both IFO and BUP had bad blocks "
				"(%llu, %llu bad blocks)\n"),
				program_name, ifo_badbl, bup_badbl);
			if ( force )
				break;
			DVDClose(dvdreader);
			exit(10);
		/* If only one but not both are damaged, copy the good
		 * over the bad, since they are identical.
		 */
		} else if ( ifo_badbl || bup_badbl ) {
			size_t i;
			char* p;
			char* dst = x_strdup(nbuf); /* no ret on err */

			/*
			 * Note: filename *must* have expected suffix at this point,
			 * hence the literal 4 at strlcpy().
			 */
			p = strrchr(ifo_badbl ? dst : nbuf, '.');
			if ( p++ == NULL ) {
				/* At this point there is no longer
				 * any reason to live.
				 */
				abort();
			}
			for ( i = 0; i < A_SIZE(ifo_cmps); i++ ) {
				if ( ! strcmp(p, ifo_cmps[i].c) ) {
					strlcpy(p, ifo_cmps[i].r, 4);
					break;
				}
			}
			if ( i >= A_SIZE(ifo_cmps) ) {
				/* At this point there is no longer
				 * any reason to live.
				 */
				abort();
			}

			pfeall(_("%s: copying %s to %s (bad blocks)\n"),
				program_name, nbuf, dst);

			if ( copy_file(nbuf, dst) ) {
				pfeall(_("%s: copy %s to %s failed\n"),
					program_name, nbuf, dst);
				free(dst);
				if ( force )
					break;
				DVDClose(dvdreader);
				exit(10);
			}

			set_f_meta(ifo_badbl ? dst : nbuf,
				&(pt->ifos[0]));
			set_f_meta(bup_badbl ? dst : nbuf,
				&(pt->bups[0]));

			free(dst);
		} else {
			/* try preserving metadata -- never fatal */
			set_f_meta(nbuf, &(pt->bups[0]));
		}

		break;
		} /* do0 */
                /* end do BUP */
		
		PNP((pn, PNREM, "VIDEO_TS/VTS_%02d_%d.VOB", i, 0))
		if ( statihack(mntd, pn, &(pt->vobs[0])) ) {
			if ( errno == ENOENT ) {
				do0 = 0;
			} else {
				perror(mntd);
				pfeall(_("%s: failed stat(%s) - %s\n"),
					program_name, mntd, strerror(errno));
				if ( force )
					do0 = 0;
				else
					exit(1);
			}
		}

		if ( do0 ) {
		if ( fnlower && ign_lc )
			NBP((nbuf, nbufbufdlen, "%s/vts_%02d_%d.vob", vidd, i, 0))
		else
			NBP((nbuf, nbufbufdlen, "%s/VTS_%02d_%d.VOB", vidd, i, 0))

		pfoopt(_("X %s size %zu\n"), nbuf, pt->vobs[0].st_size);
		} /* do0 */

		while ( do0 && !want_dry_run ) {
		uint32_t blk, fsz;
		/* check for multiple 'links' to file; 1st seen 2010 */
		blk = UDFFindFile(dvdreader, pn-1, &fsz);
		if ( blk ) {
			int r = disc_block_check(blk, nbuf, fsz);
			if ( r > 0 ) {
				if ( !force || r >= 10 )
					exit(r);
				pfeall(_(
				  "%s: continuing due to force option, "
				  "but output might be very large, and "
				  "might not make a proper UDF fs.\n"),
				  program_name);
			} else if ( r < 0 ) {
				break;
			}
		}

		dom = drd_READ_MENU_VOBS;
		dvdfile = DVDOpenFile(dvdreader, i, dom);
		if ( dvdfile == 0 ) {
			/* EH: Tue Apr 27 10:53:44 EDT 2010
			 * Some video DVDs have one or more zero size VTS_??_0.VOB
			 * files (menu vob for title).  DVDOpenFile() above might
			 * OR MIGHT NOT fail (return 0) for such files.  WHY?
			 * IAC, check st_size for 0 and if so handle it here.
			 */
			if ( pt->vobs[0].st_size == 0 ) {
				int td;

				pfeopt(_("%s: creating zero size %s\n"),
					program_name, nbuf);
				td = open(nbuf, O_CREAT|O_EXCL|O_TRUNC|O_WRONLY, 0666);
				if ( td < 0 && force && errno == EEXIST ) {
					td = open(nbuf, O_CREAT|O_TRUNC|O_WRONLY, 0666);
					if ( td >= 0 )
						pfoopt(_("%s: truncated extant %s\n"),
							program_name, nbuf);
				}
				if ( td < 0 ) {
					pfeall(_("%s: failed creating %s - %s\n"),
						program_name, nbuf, strerror(errno));
					if ( force )
						break;
					DVDClose(dvdreader);
					exit(8);
				}
				close(td);

				/* try preserving metadata -- never fatal on error */
				set_f_meta(nbuf, &(pt->vobs[0]));
				break;
			} /* st_size == 0 */

			pfeall(_("%s: failed opening menu of title %d\n"),
				program_name, i);
			if ( force )
				break;
			DVDClose(dvdreader);
			exit(8);
		}

		if ( (nblk = DVDFileSize(dvdfile)) < 0 ) {
			pfeall(_("%s: failed getting block size of %s\n"),
				program_name, nbuf);
			DVDCloseFile(dvdfile);
			if ( force )
				break;
			DVDClose(dvdreader);
			exit(9);
		}

		i1 = 0;
		if ( copy_vob(dvdfile, nbuf, buf, nblk, &i1) != nblk ) {
			pfeall(_("%s: failed to copy VOB at %ld blocks\n"),
				program_name, (long)nblk);
			DVDCloseFile(dvdfile);
			if ( force )
				break;
			DVDClose(dvdreader);
			exit(10);
		}

		DVDCloseFile(dvdfile);

		/* try preserving metadata -- never fatal on error */
		set_f_meta(nbuf, &(pt->vobs[0]));
		break; /* no loop */
		} /* do0 */

		if ( !want_dry_run ) {
		dom = drd_READ_TITLE_VOBS;
		dvdfile = DVDOpenFile(dvdreader, i, dom);
		if ( dvdfile == 0 ) {
			pfeall(_("%s: failed opening title %d\n"),
				program_name, i);
			if ( force )
				continue;
			DVDClose(dvdreader);
			exit(11);
		}

		if ( (nblk = DVDFileSize(dvdfile)) < 0 ) {
			pfeall(_("%s: failed getting block size of %s\n"),
				program_name, nbuf);
			DVDCloseFile(dvdfile);
			if ( force )
				continue;
			DVDClose(dvdreader);
			exit(12);
		}
		} /* !want_dry_run */

		i1 = 0;
		for ( j = 1; j <= pt->num; j++ ) {
		uint32_t blk, fsz;
		size_t sz;

		PNP((pn, PNREM, "VIDEO_TS/VTS_%02d_%d.VOB", i, j))
		if ( statihack(mntd, pn, &(pt->vobs[j])) ) {
			if ( errno == ENOENT )
				continue;
			perror(mntd);
			pfeall(_("%s: error in stat() of %s\n"),
				program_name, mntd);
			DVDCloseFile(dvdfile);
			if ( force )
				continue;
			DVDClose(dvdreader);
			exit(14);
		}
		if ( fnlower && ign_lc )
			NBP((nbuf, nbufbufdlen, "%s/vts_%02d_%d.vob", vidd, i, j))
		else
			NBP((nbuf, nbufbufdlen, "%s/VTS_%02d_%d.VOB", vidd, i, j))

		/* check for multiple 'links' to file; 1st seen 2010 */
		blk = UDFFindFile(dvdreader, pn-1, &fsz);
		if ( blk ) {
			int r = disc_block_check(blk, nbuf, fsz);
			if ( r > 0 ) {
				if ( !force || r >= 10 )
					exit(r);
				pfeall(_(
				  "%s: continuing due to force option, "
				  "but output might be very large, and "
				  "might not make a proper UDF fs.\n"),
				  program_name);
			} else if ( r < 0 ) {
				nblk -= fsz / blk_sz;
				continue;
			}
		}

		sz = pt->vobs[j].st_size;
		pfoopt(_("X %s size %zu\n")
			, nbuf, pt->vobs[j].st_size);

		if ( sz % blk_sz ) {
			pfeall(_("%s: error in size %zu of %s\n"),
				program_name, sz, mntd);
			pfeall(_("%s: %zu %% %u == %zu\n"),
				program_name,
				sz,
				(unsigned)blk_sz,
				sz % blk_sz);
			DVDCloseFile(dvdfile);
			if ( force )
				continue;
			DVDClose(dvdreader);
			exit(15);
		}

		if ( !want_dry_run ) {
		sz /= blk_sz;

		if ( copy_vob(dvdfile, nbuf, buf, sz, &i1) != sz ) {
			pfeall(
			_("%s: failed in VOB copy, %zu blocks\n"),
				program_name, sz);
			DVDCloseFile(dvdfile);
			if ( force )
				continue;
			DVDClose(dvdreader);
			exit(16);
		}
		nblk -= sz;

		/* try preserving metadata -- never fatal on error */
		set_f_meta(nbuf, &(pt->vobs[j]));
		} /* !want_dry_run */
		} /* for ( j = 1; j <= pt->num; j++ ) { */

		if ( !want_dry_run ) {
			DVDCloseFile(dvdfile);

			if ( nblk ) {
				pfeall(_("%s: %ld stray blocks from %s\n")
					, program_name, (long)nblk, nbuf);
				if ( force )
					continue;
				exit(17);
			}
		} /* !want_dry_run */
	}
}

ssize_t
copy_vob(
	drd_file_t* dvdfile,
	const char* out,
	unsigned char* buf,
	size_t blkcnt,
	long* poff
	)
{
	int o;
	size_t cnt;

	if ( (o = open(out, OPENFL, 0666)) < 0 ) {
		int e = errno;

		if ( e == EEXIST && force ) {
			struct stat sb;

			pfoopt(_("%s: %s exists, using force\n"),
				program_name, out);

			if ( stat(out, &sb) ) {
				pfeopt(_("%s: stat(%s) failed -- %s\n"),
					program_name, out, strerror(errno));
				sb.st_mode = 0600;
				sb.st_atime = sb.st_mtime = sb.st_ctime = 0;
			}

			chmod(out, sb.st_mode | 0600);
			if ( unlink(out) ) {
				pfeopt(_("%s: unlink(%s) failed -- %s\n"),
					program_name, out, strerror(errno));
				chmod(out, sb.st_mode);
				return -1;
			}
			
			return copy_vob(dvdfile, out, buf, blkcnt, poff);
		}
		
		perror(out);

		if ( e != EEXIST || !ign_ex )
			return -1;
		
		*poff += blkcnt;
		return blkcnt;
	}
	
	errno = 0;

	cnt = copy_vob_fd(dvdfile, out, -1, o, buf, blkcnt, poff);

	if ( close(o) ) {
		perror(out);
		return -1;
	}

	return cnt;
}

int
copy_bup_ifo(char* src, const char* dest)
{
	int ret;
	size_t i;
	char buf[8];
	char* t, * s, * r, * q, * p = strrchr(src, '.');
	
	if ( p == NULL || strlen(p) != 4 )
		return -1;
	
	q = p - sizeof("/VIDEO_TS/VIDEO_TS") + 1;
	if ( q != strstr(src, "/VIDEO_TS/") && q != strstr(src, "/video_ts/") )
		return -1;

	strlcpy(buf, p, A_SIZE(buf));
	
	r = x_strdup(dest);
	s = strrchr(r, '.');
	if ( s == NULL ) {
		free(r);
		r = NULL;
	}
	
	p++; /* '.' is not in cmp strings */
	for ( i = 0; i < A_SIZE(ifo_cmps); i++ ) {
		if ( ! strcmp(p, ifo_cmps[i].c) ) {
			strlcpy(p, ifo_cmps[i].r, 4);
			if ( r && s ) {
				strlcpy(s, ifo_cmps[i].r, 4);
			}
			break;
		}
	}
	if ( i >= A_SIZE(ifo_cmps) ) {
		if ( r ) {
			free(r);
		}
		return -1;
	}
	--p;

	if ( r ) {
		struct stat tsb;
		
		if ( !stat(r, &tsb) && tsb.st_size > 0 )
			t = r;
		else
			t = src;
	} else {
		t = src;
	}

	pfeopt(_("%s: trying %s -> %s\n"), program_name, t, dest);
	ret = copy_file(t, dest);

	if ( ret ) {
		unlink(dest);
		if ( do_ioerrs > 1 ) {
			pfeall(_("%s: trying forceful copy %s -> %s\n"),
				program_name, t, dest);
			ret = copy_file_force(t, dest);
		}
	}
	if ( ret ) {
		pfeall(_("%s: failed copy %s -> %s\n"),
			program_name, t, dest);
	}

	strlcpy(p, buf, strlen(buf) + 1);
	if ( r )
		free(r);
	
	return ret;
}

int
copy_file_force(const char* src, const char* dest)
{
	int ifd, ofd;
	ssize_t szi, szo;
	unsigned char* buf;
	struct stat sb;
	size_t n, wrcnt, blcnt, rem;
	
	buf = global_aligned_buffer;

	ifd = open(src, O_RDONLY|O_LARGEFILE);
	if ( ifd < 0 ) {
		pfeall(
			_("%s: %s open()ing: %s\n"),
			program_name, strerror(errno), src);
		exit(20);
	}

	if ( fstat(ifd, &sb) ) {
		pfeall(
			_("%s: %s fstat()ing: %s\n"),
			program_name, strerror(errno), src);
		exit(21);
	}
	
	ofd = open(dest, O_WRONLY|O_CREAT|O_TRUNC|O_NOFOLLOW|O_LARGEFILE, 0666);
	if ( ofd < 0 ) {
		pfeall(
			_("%s: %s open()ing: %s\n"),
			program_name, strerror(errno), dest);
		exit(22);
	}
	
	wrcnt = blk_sz;
	blcnt = sb.st_size / wrcnt;
	rem = sb.st_size % wrcnt;

	for ( n = 0; n < blcnt; n++ ) {
		szi = read_all(ifd, buf, wrcnt);
		if ( szi < 0 ) {
			size_t l = n + 1;
			if ( errno != EIO ) {
				pfeall(
					_("%s: %s read()ing: %s\n"),
					program_name, strerror(errno), src);
				exit(23);
			}
			while ( l < blcnt && lseek(ifd,wrcnt*l,SEEK_SET) < 0 ) {
				l++;
			}
			pfeopt(
				_("%s: writing %lu null blocks at block %lu\n"),
				program_name,
				(unsigned long)l - n,
				(unsigned long)n);
			memset(buf, 0, wrcnt);
			szi = wrcnt;
			for ( ; n < l; n++ ) {
				szo = write_all(ofd, buf, szi);
				if ( szo != szi ) {
					pfeall(
						_("%s: %s write()ing: %s\n"),
						program_name,
						strerror(errno), dest);
					exit(24);
				}				
			}
			n--;
			continue;
		} else if ( szi < wrcnt ) {
			/* why short read ? */
			pfeall(
				_("%s: internal error: wtf at block %lu\n"),
				program_name,
				(unsigned long)n);
			
			exit(25);
		}
		szo = write_all(ofd, buf, szi);
		if ( szo != szi ) {
			pfeall(
				_("%s: %s write()ing: %s\n"),
				program_name, strerror(errno), dest);
			exit(26);
		}
	}

	if ( rem ) {
		szi = read_all(ifd, buf, rem);
		if ( szi < 0 ) {
			if ( errno != EIO ) {
				pfeall(
					_("%s: %s read()ing: %s\n"),
					program_name, strerror(errno), src);
				exit(27);
			}
			pfeopt(
				_("%s: writing %lu nulls at end\n"),
				program_name, (unsigned long)rem);
			memset(buf, 0, rem);
			szi = rem;
		} else if ( szi < rem ) {
			/* why short read ? */
			pfeall(
				_("%s: internal error: wtf at end\n"),
				program_name);
			
			exit(28);
		}
		szo = write_all(ofd, buf, szi);
		if ( szo != szi ) {
			pfeall(
				_("%s: %s write()ing: %s\n"),
				program_name, strerror(errno), dest);
			exit(29);
		}
	}

	if ( close(ifd) ) {
		pfeall(_("%s: %s close()ing: %s\n"),
			program_name, strerror(errno), src);
		exit(30);
	}
	if ( close(ofd) ) {
		pfeall(_("%s: %s close()ing: %s\n"),
			program_name, strerror(errno), dest);
		exit(31);
	}
	
	/* try preserving metadata -- never fatal on error */
	set_f_meta(dest, &sb);
	
	return 0;
}

int
copy_file(const char* src, const char* dest)
{
	int ifd, ofd;
	ssize_t szi, szo;
	unsigned char* buf;
	struct stat sb;
	const size_t wrcnt = block_read_count * blk_sz;
	
	buf = global_aligned_buffer;

	ifd = open(src, O_RDONLY|O_LARGEFILE);
	if ( ifd < 0 ) {
		int e = errno;
		if ( e == EPERM && force ) {
			pfoopt(_("%s: %s exists, using force\n"),
				program_name, src);

			if ( stat(src, &sb) ) {
				pfeopt(_("%s: stat(%s) failed -- %s\n"),
					program_name, src, strerror(errno));
				sb.st_mode = 0400;
				sb.st_atime = sb.st_mtime = sb.st_ctime = 0;
			}

			chmod(src, sb.st_mode | 0400);
			ifd = open(src, O_RDONLY|O_LARGEFILE);
			chmod(src, sb.st_mode);
			if ( ifd < 0 ) {
				pfeall(_("%s: %s open(O_RDONLY)ing: %s\n"),
					program_name, strerror(errno), src);
				return -1;
			}
		} else if ( !force ) {
			pfeall(_("%s: %s open(O_RDONLY)ing: %s\n"),
				program_name, strerror(errno), src);
			exit(40);
		} else {
			pfeall(_("%s: %s open(O_RDONLY)ing: %s\n"),
				program_name, strerror(errno), src);
			return -1;
		}
	}

	/* for set_f_meta */
	if ( fstat(ifd, &sb) ) {
		pfeall(_("%s: %s fstat()ing: %s\n"),
			program_name, strerror(errno), src);
		if ( force ) {
			sb.st_mode = 0400;
			sb.st_atime = sb.st_mtime = sb.st_ctime = 0;
		} else
			exit(41);
	}
	
	if ( (ofd = open(dest, OPENFL, 0666)) < 0 ) {
		int e = errno;

		pfeall(_("%s: %s open(O_RDWR)ing: %s\n"),
			program_name, strerror(errno), dest);

		close(ifd);
		if ( e == EEXIST && force ) {
			pfoopt(_("%s: %s exists, using force\n"),
				program_name, dest);

			if ( stat(dest, &sb) ) {
				pfeopt(_("%s: stat(%s) failed -- %s\n"),
					program_name, dest, strerror(errno));
				sb.st_mode = 0600;
				sb.st_atime = sb.st_mtime = sb.st_ctime = 0;
			}

			chmod(dest, sb.st_mode | 0600);
			if ( unlink(dest) ) {
				pfeopt(_("%s: unlink(%s) failed -- %s\n"),
					program_name, dest, strerror(errno));
				chmod(dest, sb.st_mode);
				return -1;
			}

			return copy_file(src, dest);
		}

		if ( e == EEXIST && ign_ex ) {
			/* try preserving metadata -- never fatal on error */
			set_f_meta(dest, &sb);

			return 0;
		}

		if ( force )
			return -1;
		exit(42);
	}
	
	while ( (szi = read_all(ifd, buf, wrcnt)) > 0 ) {
		szo = write_all(ofd, buf, szi);
		if ( szo != szi ) {
			pfeall(_("%s: %s write()ing: %s\n"),
				program_name, strerror(errno), dest);
			if ( force ) {
				close(ifd);
				close(ofd);
				return -1;
			}
			exit(43);
		}
	}

	if ( szi != 0 ) {
		int e = errno;
		pfeopt(_("%s: %s read()ing: %s\n"),
			program_name, strerror(errno), src);
		errno = e;
		/* In this case if err is EIO let caller handle it */
		if ( errno == EIO || force ) {
			close(ifd);
			close(ofd);
			return -1;
		}
		exit(44);
	}
	
	if ( close(ifd) ) {
		pfeall(_("%s: %s close()ing: %s\n"),
			program_name, strerror(errno), src);
		if ( !force )
			exit(45);
	}
	if ( close(ofd) ) {
		pfeall(_("%s: %s close()ing: %s\n"),
			program_name, strerror(errno), dest);
		if ( !force )
			exit(46);
	}
	
	/* try preserving metadata -- never fatal on error */
	set_f_meta(dest, &sb);
	
	return 0;
}

void
wr_regmask(char* d, int dlen, unsigned val)
{
	const char* nms[3] = { "VIDEO_TS.IFO", "VIDEO_TS.BUP", NULL };
	const char* id = "DVDVIDEO-VMG";
	const char* p;
	int i;
	size_t m;
	struct stat sb;
	union {
		char     c[16];
		uint32_t u[4];
	} uc;

	if ( dlen < 1 )
		return;
	if ( d[dlen - 1] != '/' ) {
		d[dlen++] = '/';
		d[dlen] = '\0';
	}
	
	m = PATH_MAX + 1 - dlen;

	for ( i = 0; (p = nms[i]) != NULL; i++ ) {
		int f = strlcpy(&d[dlen], p, m);
		
		if ( f >= m ) {
			pfeall(_("%s: name too long: %s + %s\n"),
				program_name, d, p);
			exit(60);
		}
		
		if ( stat(d, &sb) ) {
			perror(d);
			exit(61);
		}
		
		if ( chown(d, getuid(), sb.st_gid) ) {
			perror(d);
			exit(62);
		}
		
		if ( chmod(d, sb.st_mode | S_IRUSR | S_IWUSR) ) {
			perror(d);
			exit(63);
		}
		
		if ( (f = open(d, O_RDWR | O_LARGEFILE)) < 0 ) {
			perror(d);
			exit(64);
		}
		
		if ( read_all(f, uc.c, VMGIDLEN) != VMGIDLEN ) {
			perror(d);
			pfeall(_("%s: read of %u bytes failed on %s\n"),
				program_name, VMGIDLEN, p);
			exit(65);
		}
		
		uc.c[VMGIDLEN] = '\0';
		if ( strcmp(uc.c, id) ) {
			pfeopt(_("%s: wrong file id on %s:\n\twanted")
				_(" 0x%08lX%08lX%08lX (%s), got")
				_(" 0x%08lX%08lX%08lX\n\tnot changing %s\n"),
				program_name, d,
				(unsigned long)*(const uint32_t*)(&id[0]),
				(unsigned long)*(const uint32_t*)(&id[4]),
				(unsigned long)*(const uint32_t*)(&id[8]),
				id,
				(unsigned long)uc.u[0],
				(unsigned long)uc.u[1],
				(unsigned long)uc.u[2],
				d);

			if ( close(f) < 0 ) {
				perror(d);
				pfeall(_("%s: close() failed on %s\n"),
					program_name, p);
				exit(50);
			}
			
			set_f_meta(d, &sb);
			continue;
		}
		
		if ( lseek(f, CATOFF, SEEK_SET) != CATOFF ) {
			perror(d);
			pfeall(_("%s: seek (%d) to %lu failed on %s\n"),
				program_name, 1, CATOFF, p);
			exit(51);
		}
		
		if ( read_all(f, uc.c, CATRD) != CATRD ) {
			perror(d);
			pfeall(_("%s: read of %u bytes failed on %s\n"),
				program_name, CATRD, p);
			exit(52);
		}
		
		pfoopt(_("Read category 0x%08lX from %s\n"), uc.u[0], d);
		
		if ( uc.c[1] == (char)(val & 0xFFU) ) {
			pfoopt(_("Found desired value 0x%02X, no change\n"),
				(unsigned)uc.c[1]);

			if ( close(f) < 0 ) {
				perror(d);
				pfeall(_("%s: close() failed on %s\n"),
					program_name, p);
				exit(53);
			}
			
			set_f_meta(d, &sb);
			continue;
		}
		uc.c[1] = (char)(val & 0xFFU);
		
		if ( lseek(f, CATOFF, SEEK_SET) != CATOFF ) {
			perror(d);
			pfeall(_("%s: seek (%d) to %lu failed on %s\n"),
				program_name, 2, CATOFF, p);
			exit(54);
		}
		
		if ( write_all(f, uc.c, CATRD) != CATRD ) {
			perror(d);
			pfeall(_("%s: write of %u bytes failed on %s\n"),
				program_name, CATRD, p);
			exit(55);
		}
		
		if ( close(f) < 0 ) {
			perror(d);
			pfeall(_("%s: close() failed on %s\n"),
				program_name, p);
			exit(56);
		}
		
		pfoopt(_("Wrote category 0x%08lX to %s\n"), uc.u[0], d);
		
		set_f_meta(d, &sb);
	}
}

/* static procedures */

/* if poff==0 do fd copy else do vob copy */
/*
 *  call when read fails with io error; assume optical medium fault.
 *  zero the destination buffer and try reading one block at a time.
 *  if read fails w/ EIO advanvce one block (writing zeroes).
 *  return -1 for errors other than EIO.
 */
static ssize_t
copy_vob_badblks(
	drd_file_t* dvdfile,
	const char* outfname,
	int inp, int out,
	unsigned char* buf,
	size_t blkcnt,
	long* poff
	)
{
	time_t tm1, tm2;
	size_t nbr;
	off_t rdp;
	unsigned long good = 0, bad = 0;
	size_t cnt = blkcnt;
	unsigned char* prd = buf;

	tm1 = time(0);

	if ( inp >= 0 && (rdp = lseek(inp, 0, SEEK_CUR)) < 0 ) {
		int t = errno;
		perror("lseek cur in copy_vob_badblks");
		errno = t;
		return -1;
	}

	nbr = retrybadblk;

	while ( cnt ) {
		ssize_t nb;
		nbr = MIN(nbr, cnt);
		
		if ( poff ) {
			nb = DVDReadBlocks(dvdfile, *poff, nbr, prd);
		} else if ( inp >= 0 ) {
			ssize_t ssz = read_all(inp, prd, nbr * blk_sz);
			if ( ssz <= 0 ) {
				nb = ssz;
			} else {
				ssize_t rmd = ssz % blk_sz;
				if ( rmd ) {
					int t = errno;
					perror("read_all in copy_badblocks");
					errno = t;
					return -1;
				}
				nb = ssz / blk_sz;
			}
		} else {
			pfeall(_("FATAL internal error: inp == %d\n"),
				inp);
			errno = EINVAL;
			return -1;
		}
		
		if ( nb == 0 ) {
			break;
		} else if ( nb < 0 ) {
			if ( errno != EIO ) {
				perror(outfname);
				return -1;
			}

			memset(prd, 0, nbr * blk_sz);

			nb = nbr;
			bad += nb;
		} else {
			good += nb;
		}
		
		if ( poff ) {
			*poff += (long)nb;
		}

		cnt -= nb;
		nb  *= blk_sz;
		prd += nb;
		rdp += nb;

		if ( inp >= 0 && lseek(inp, rdp, SEEK_SET) != rdp ) {
			int t = errno;
			perror("lseek set in copy_badblocks");
			errno = t;
			return -1;
		}
	}

	cnt = blkcnt - cnt;
	nbr = cnt * blk_sz;

	if ( write_all(out, buf, nbr) != nbr ) {
		perror(outfname);
		return -1;
	}
	
	numbadblk += bad;
	tm2 = time(0);
	pfeall(
		_("%lu bad blocks zeroed in read of %lu "
		"(%g good blocks in %llu seconds) for %s\n"),
		bad, (unsigned long)blkcnt,
		(double)good / (double)blkcnt,
		(unsigned long long)tm2 - tm1,
		outfname);
	
	return cnt;
}

static ssize_t
copy_vob_fd(
	drd_file_t* dvdfile,
	const char* outfname,
	int inp, int out,
	unsigned char* buf,
	size_t blkcnt,
	long* poff
	)
{
	size_t cnt = blkcnt;

	errno = 0;

	while ( cnt ) {
		ssize_t nb;
		size_t  nbr = MIN(cnt, block_read_count);
		
		if ( poff ) {
			nb = DVDReadBlocks(dvdfile, *poff, nbr, buf);
		} else if ( inp >= 0 ) {
			ssize_t ssz = read_all(inp, buf, nbr * blk_sz);
			if ( ssz <= 0 ) {
				nb = ssz;
			} else {
				ssize_t rmd = ssz % blk_sz;
				if ( rmd ) {
					lseek(inp, (off_t)0 - rmd, SEEK_CUR);
				}
				nb = ssz / blk_sz;
			}
		} else {
			pfeall(_("FATAL internal error: inp == %d\n"),
				inp);
			errno = EINVAL;
			return -1;
		}
		
		if ( nb <= 0 ) {
			perror(outfname);
			errno = 0;
			/* call desperation procedure:
			 * will write bogus data for failed
			 * reads on the premise that still
			 * a video dvd _might_ remain usable
			 */
			if ( do_ioerrs ) {
				nb = copy_vob_badblks(dvdfile, outfname,
					inp, out, buf, nbr, poff);
				if ( nb > 0 ) {
					cnt -= nb;
					continue;
				}	
			}	

			eputs(_("DVD bad blocks: cannot salvage\n"));

			return -1;
		}

		if ( poff ) {
			*poff += (long)nb;
		}
		cnt -= nb;
		nb *= blk_sz;

		if ( write_all(out, buf, nb) != nb ) {
			perror(outfname);
	
			return -1;
		}
	}

	return blkcnt - cnt;
}

/*
 * Check a dvd video file block to see if it is
 * associated with another name, as has been seen
 * on some discs.
 * Also, zero size files might have the same block as
 * the next.
 *
 * If block was already seen; make hard link (in output) and
 * if successful return -1; if not seen before return 0.
 * On failure return positive >= decimal 10 if program should
 * not continue, or < 10 if program may continue with 'force' opt.
 */
static int
disc_block_check(uint32_t blk, const char* nbuf, uint32_t fsz)
{
	const BHI* pbhi = blk_check(
				(blkhash_t)blk, nbuf, (filesize_t)fsz);
	if ( pbhi && pbhi->bh_count > 1 ) {
		/* another name points to this file! */
		pfoall(_("%s: multiple names \"%s\" == \"%s\", "
			"%zu bytes at source disc block 0x%08X\n"),
			program_name, nbuf, pbhi->bh_name,
			(size_t)fsz, (unsigned)blk);

		if ( link(pbhi->bh_name, nbuf) ) {
			pfeall(
			  _("%s: failed link \"%s\", \"%s\" - %s\n"),
			  program_name,
			  pbhi->bh_name, nbuf, strerror(errno));

			return 8;
		}

		return -1;
	} else if ( pbhi == NULL ) {
		pfeall(
		  _("%s: failed inserting \"%s\" into hash table\n"),
		  program_name, nbuf);

		return 10;
	} else {
		int nnzsz = 0;
		const BHI* pa[32];
		unsigned num = A_SIZE(pa);
		unsigned nr = blk_scan((blkhash_t)blk, pa, num);
		
		if ( nr > 1 ) {
			unsigned i;
			filesize_t lastnzsz = 0;
			pfoopt(
			  _("source disc block 0x%08X has %u names:"),
			  (unsigned)blk, nr);
			for ( i = 0; i < nr; i++ ) {
				filesize_t csz = pa[i]->bh_size;
				pfoopt(_(" %zu bytes as \"%s\""),
				  (size_t)csz, pa[i]->bh_name);
				
				if ( csz > 0 && csz != lastnzsz ) {
					if ( lastnzsz ) {
						nnzsz++;
					}
					lastnzsz = csz;
				}
			}
			if ( nr >= num ) {
				pfoopt(_(" (there might be more)"));
			}
			pfoopt("\n");
		}
		
		if ( nnzsz ) {
			pfeall(
			  _("%s: source disc block 0x%08X has "
			  "multiple names and %d non-zero sizes; "
			  "this cannot be represented in the "
			  "output file system\n"),
			  program_name, (unsigned)blk, nnzsz);
			
			return 9;
		}
	}

	return 0;
}
