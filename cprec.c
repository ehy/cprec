/* 
   cprec - A recursive directory hierarchy copier; much like 'cp -Rp'.

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

#define _FILE_OFFSET_BITS 64
#define _LARGEFILE_SOURCE

/*
 * hdr_cfg.h includes "system.h" which includes
 * "config.h" (#ifdef HAVE_CONFIG_H, and
 * configure script arranges -DHAVE_CONFIG_H in $(CC));
 * also, hdr_cfg.h includes <sys/types.h> before "system.h"
 * which "system.h" wants previously included
 */
#include "hdr_cfg.h"
#include <stddef.h>
#if HAVE_GETOPT_H
#	include <getopt.h>
#else
#	include "gngetopt.h"
#endif
#include <unistd.h>

#ifndef EXIT_SUCCESS
#define EXIT_SUCCESS 0
#endif
#ifndef EXIT_FAILURE
#define EXIT_FAILURE 1
#endif

/* Prototypes for functions defined in xmalloc.c. */
#include "xmalloc.h"

/* this program's various incs */
#include "cprec.h"
#include "lib_misc.h"
#include "dl_drd.h"
#include "cpf.h"
#include "ino.h"
#include "block_hash.h"
#include "apue_ftw.h"
#include "walk.h"
#include "meta_set.h"
#include "path_set.h"

/* Prototypes for functions defined herein. */
static void usage(int status);
static int  decode_switches(int argc, char* argv[]);
/* main for recursive copy of fs hierarchy */
static int cprec(int texist, int tisdir);
/* setup dvd reader library, open dvd device */
static drd_reader_t* init_lib_drd(void);
/* print some info on hard links */
static void print_hlink_info(void);

/* The name the program was run with, stripped of any leading path. */
const char* program_name = "cprec";

/* alternative to macro */
size_t		block_read_count = BLOCK_READ_CNT;

/* badblock retry read count */
size_t          retrybadblk = 32;

/* for meta data funcs */
dire_p topdir;

/* main memory */
unsigned char* global_buffer;
unsigned char* global_aligned_buffer;
size_t         global_buffer_size;
size_t         global_buffer_align;


/* Option flags and variables */
int nfdresv = 8;   /* reserve this from ftw() for other use */
int nfdmax  = 64;  /* use no more than this number of dir fd */
/* flagging whether to quit on some errors, or ignore and go on: */
int ign_dnr = 0;   /* ignore directories not readable */
int ign_ns  = 0;   /* ignore stat() failures -- REMOVE THIS */
int ign_ex  = 0;   /* ignore EEXIST errors writing output --ignore-existing */
/* whether to ignore certain irregulars -- (sockets are NEVER copied) */
int ign_sl  = 0;   /* ignore symbolic links --ignore-symlinks */
int ign_hl  = 0;   /* ignore hard links --ignore-hardlinks */
int ign_sf  = 0;   /* ignore special files --ignore-specials */
/* other flags: */
int ign_lc  = 0;   /* ignore lower case 'video_ts' and its entries */
int do_ioerrs = 0; /* desperate measures in response to I/O errors */

/* The DVD drive device node, or symlink, as appropriate */
#ifndef DEFAULT_DVD_NODE
#define DEFAULT_DVD_NODE "/dev/dvd"
#endif
const char* dvdname =    DEFAULT_DVD_NODE; /* set by --node */
const char* dvdnamedef = DEFAULT_DVD_NODE; /* not to be set */
#if ! HAVE_LIBDVDREAD
const char* drd_libname;	/* --libdvdr */
#endif
const char* desired_title_s;	/* --dvdbackup */
int desired_title;		/* --dvdbackup (converted) */
int want_quiet;			/* --quiet, --silent */
int want_verbose;		/* --verbose */
/* dry-run is unmaintained; makes segfaults */
/* it is still tested, so it must remain 0 */
int want_dry_run = 0;		/* --dry-run */
int simple_copy = 1;		/* --simple-copy */
int force = 0;     /* -f; ignore read()/open() errors + overwrite */
int preserve = 0;  /* -p; preserve metadata if permitted */

/* getopt_long return codes */
enum {DUMMY_CODE=129
      ,DRYRUN_CODE
      ,DIRECTORY_CODE
};

/* statbuf for target argument */
struct stat tsb;

static struct option const long_options[] =
{
	{"node", required_argument, 0, 'n'},
	{"quiet", no_argument, 0, 'q'},
	{"silent", no_argument, 0, 'q'},
	{"verbose", no_argument, 0, 'v'},
	{"simple-copy", no_argument, 0, 's'},
	{"force", no_argument, 0, 'f'},
	{"preserve", no_argument, 0, 'p'},
/* dry-run is unmaintained; makes segfaults
	{"dry-run", no_argument, 0, DRYRUN_CODE},
*/
	{"dvdbackup", required_argument, 0, 'd'},
#if ! HAVE_LIBDVDREAD
	{"libdvdr", required_argument, 0, 'L'},
#endif
	{"ignore-existing", no_argument, 0, 'E'},
	{"ignore-hardlinks", no_argument, 0, 'H'},
	{"ignore-symlinks", no_argument, 0, 'S'},
	{"ignore-specials", no_argument, 0, 'D'},
	{"ignore-nonreadable", no_argument, 0, 'N'},
	{"help", no_argument, 0, 'h'},
	{"version", no_argument, 0, 'V'},
	{NULL, 0, NULL, 0}
};

/* The source arg data */
typedef struct src_arg_st {
	const char*	s;
	time_t		a, m;
	mode_t		t;
	uid_t		u;
	gid_t		g;
	dev_t		d, r;
	ino_t		i;
	nlink_t		n;
	int		e;
} SARG;
/* The source arg */
const char*	source_name;
SARG*		source_args;
int		source_count;
int		source_index;
/* the last arument, the target */
const char*	target;
#define SARG2STAT(sa, st) (st).st_atime=(sa).a; \
	(st).st_mtime=(sa).m; \
	(st).st_mode=(sa).t; \
	(st).st_uid=(sa).u; \
	(st).st_gid=(sa).g; \
	(st).st_dev=(sa).d; \
	(st).st_rdev=(sa).r; \
	(st).st_ino=(sa).i; \
	(st).st_nlink=(sa).n;
#define STAT2SARG(sa, st) (st).st_atime=(sa).a; \
	(sa).m=(st).st_mtime; \
	(sa).t=(st).st_mode; \
	(sa).u=(st).st_uid; \
	(sa).g=(st).st_gid; \
	(sa).d=(st).st_dev; \
	(sa).r=(st).st_rdev; \
	(sa).i=(st).st_ino; \
	(sa).n=(st).st_nlink;


/* print some info on hard links */
static void
print_hlink_info(void)
{
	unsigned ntbl;
	unsigned minentlen;
	unsigned maxentlen;
	unsigned nnotfull;
	unsigned nitems;
	unsigned r = ino_status(
		&ntbl,
		&minentlen,
		&maxentlen,
		&nnotfull,
		&nitems
	);

	if ( r == 0 ) {
		return;
	}

	pfoopt(_("found %u files with multiple links\n"), nitems);
	pfoopt(_("%u items without all links seen\n"), nnotfull);
	pf_dbg(_("dbg: found %u files with multiple links\n"), nitems);
	pf_dbg(_("dbg: %u of %u table entries used\n"), r, ntbl);
	pf_dbg(_("dbg: minimum bucket length %u\n"), minentlen);
	pf_dbg(_("dbg: maximum bucket length %u\n"), maxentlen);
	pf_dbg(_("dbg: %u items without all links seen\n"), nnotfull);
}

/* setup dvd reader library, open dvd device */
static drd_reader_t*
init_lib_drd(void)
{
#if ! HAVE_LIBDVDREAD
	int		rdrd;
#endif /* HAVE_LIBDVDREAD */
	drd_reader_t*	dvdreader = NULL;

	/* this might be nec., not sure */
	setenv("DVDCSS_CACHE", "off", 1);

#if ! HAVE_LIBDVDREAD
	if ( drd_libname == NULL )
		drd_libname = drd_altname;
	
	rdrd = open_drd(drd_libname, get_drd_defflags());

	if ( rdrd ) {
		pfeall(_("%s: failed loading %s\n"),
			program_name, drd_libname);
		return NULL;
	} else {
		int nf;

		pfoopt(_("%s: using %s for dvdread library\n"),
			program_name, drd_libname);
		
		nf = load_drd_syms();
		if ( nf ) {
			pfeall(_("%s: failed loading %d symbols from %s\n"),
				program_name, nf, drd_libname);
			return NULL;
		}
		
		if ( DVDVersion == NULL ) {
			pfoopt(_("%s: dvdread library has no DVDVersion()\n")
				_("\tnote version < %s API unknown\n"),
				program_name, "0.9.4");
		} else {
			int v = DVDVersion();
			pfoopt(_("%s: %s version %d.%d.%d found\n"),
				program_name, drd_libname,
				(v / 10000) % 100,
				(v / 100) % 100,
				v % 100);
		}
	}

	if ( (dvdreader = DVDOpen(dvdname)) == NULL ) {
		pfeall(_("%s: failed opening %s as dvd with %s\n"),
			program_name, dvdname, drd_libname);
	}

#else

#if HAVE_DVDVERSION
	{
		int v = DVDVersion();
		pfoopt(_("%s: %s version %d.%d.%d found\n"),
			program_name, "libdvdread",
			(v / 10000) % 100,
			(v / 100) % 100,
			v % 100);
	}
#elif DVDREAD_VERSION
	{
		int v = DVDREAD_VERSION;
		pfoopt(_("%s: compiled with %s version %d.%d.%d (header)\n"),
			program_name, "libdvdread",
			(v / 10000) % 100,
			(v / 100) % 100,
			v % 100);
	}
#else
	pfoopt(_("%s: %s version unknown\n"), program_name, "libdvdread");
#endif

	if ( (dvdreader = DVDOpen(dvdname)) == NULL ) {
		pfeall(_("%s: failed opening %s as dvd\n"),
			program_name, dvdname);
	}

#endif /* HAVE_LIBDVDREAD */

	return dvdreader;
}

/* main for recursive copy of fs hierarchy */
static int
cprec(int texist, int tisdir)
{
	int		doregmask = 0;
	unsigned 	regmask = 0;
	const char*	penv;
	drd_reader_t*	dvdreader = NULL;
	unsigned char*	buf;
	dire_t		top;

	/* Initialize libdvdread */
	if ( !simple_copy && !want_dry_run && desired_title_s ) {
		dvdreader = init_lib_drd();
		if ( dvdreader == NULL )
			return EXIT_FAILURE;
	}

	global_buffer_align = xget_page_size();
	global_buffer_size = (size_t)drd_VIDEO_LB_LEN * BLOCK_READ_CNT +
	  global_buffer_align - 1;
	if ( global_buffer_size % global_buffer_align ) {
		global_buffer_size += global_buffer_align -
		  (global_buffer_size % global_buffer_align);
	}
#	if HAVE_POSIX_MEMALIGN
	if ( posix_memalign((void**)&buf,
	     global_buffer_align, global_buffer_size) ) {
		pfeall(_("%s: posix_memalign failed, trying xmalloc\n"),
		  program_name);
		/* go to internal method of getting aligned memory */
#	endif
	/* global pointer */
	global_buffer = xmalloc(global_buffer_size);
	/* aligned pointer */
	buf = mk_aligned_ptr(global_buffer, global_buffer_align);
#	if HAVE_POSIX_MEMALIGN
	} else {
		global_buffer = buf;
		pf_dbg(_("dbg: posix_memalign of %zu at %p\n"),
		  global_buffer_size, (void*)buf);
	}
#	endif
	global_aligned_buffer = buf;
	
	/* set region mask? */
	if ( !simple_copy ) {
		if ( (penv = getenv("DVD_SETREGM")) != NULL ) {
			doregmask = 1;
			switch ( *penv ) {
			case '1':
				regmask = regmA;
				break;
			case '2':
				regmask = regmN;
				break;
			case '3':
				regmask = regm2;
				break;
			default:
				regmask = regm;
			}
			pfoopt(_("Will set reg-cat to 0x%02X\n"), regmask);
		} else {
			regmask = regm;
			doregmask = 0;
		}
	}

	/* desperate measures in response to I/O errors? */
	/* do not try $CPREC_DESPERATE > 1 -- bad code */
	if ( (penv = getenv("CPREC_DESPERATE")) != NULL ) {
		switch ( *penv ) {
			case '2':
				do_ioerrs = 2;
				force = 1;
				break;
			case '1':
				do_ioerrs = 1;
				force = 1;
				break;
			default:
				do_ioerrs = 0;
				break;
		}
		if ( do_ioerrs ) {
			if ( (penv = getenv("CPREC_RETRYBLOCKS")) != 0 ) {
				long lv;

				errno = 0;
				lv = strtol(penv, 0, 0);
				
				if ( errno || lv < 1 || lv > block_read_count ) {
					pfeall(
					_("\"%s\"==\"%s\" - using default %zu\n")
					,"CPREC_RETRYBLOCKS"
					, penv, retrybadblk);
				} else {
					retrybadblk = (size_t)lv;
					pfeopt(
					_("using CPREC_RETRYBLOCKS %zu\n"),
					retrybadblk);
				}
			}
			pfoopt(
		  _("Will desperately try to continue with I/O errors, %d\n")
			, do_ioerrs);
		}
	} else {	
		do_ioerrs = 0;
	}

	for ( source_index = 0; source_index < source_count; source_index++ ) {
	source_name = source_args[source_index].s;
	
	if ( source_args[source_index].e ) {
		pfeall(_("%s: source argument \"%s\" error - %s\n"),
			program_name, source_name,
			strerror(source_args[source_index].e));
		if ( force )
			continue;
		return EXIT_FAILURE;
	}

	set_paths(source_name, target);
	if ( expaths ) {
		pfeall(_("%s: path argument(s) too long: \"%s\", \"%s\"\n"),
			program_name, mntd, outd);
		if ( force )
			continue;
		return EXIT_FAILURE;
	}
	
	if ( 0 && desired_title ) {
		if ( source_count > 1 ) {
			pfeall(_("%s: too many source arguments (%d)\n"),
				program_name, source_count);
			return EXIT_FAILURE;
		}
	} else if ( texist && tisdir ) {
		/* source copy into existing directory */
		if ( force && !want_dry_run ) {
			/* try adding write permission */
			pf_dbg(_("dbg: force writable %s == %d\n"),
				outd, chmod(outd, tsb.st_mode | 0700));
		}
		/*  special case: if vobs are found under source arg,
		 *  and video DVD backup is requested -
		 *  do not create out directory with name of
		 *  source directory; allow usage such as:
		 *  'cprec ~/extrastuff /mnt/dvd0 ./backuprootdir'
		 *  we want ./backuprootdir to contain 'VIDEO_TS'
		 *  etc., not 'dvd0', and we want 'extrastuff'
		 *  created under ./backuprootdir
		 *  of course this differs from a plain old copy
		 *  'cprec src0 src1 src2 target' for which all
		 *  sources are to be created under target
		 */
		if ( !(okvid && desired_title_s) || simple_copy ) {
			size_t len, buflen;
			const char* p;

			p = strrchr(mntd, '/');

			if ( p == NULL )
				p = mntd;
			else
				p++;
			len = strlen(p);
			buflen = outdbufdlen - outdlen - 1;
			if ( buflen <= len ) {
				pfeall(
				_("%s: output name too long: %s, %s\n"),
					program_name, p, outd);
				return EXIT_FAILURE;
			}

			if ( outdlen > 0 && outd[outdlen - 1] == '/' ) {
				outd[--outdlen] = '\0';
				buflen++;
			}
			outd[outdlen++] = '/';
			if ( strlcpy(&outd[outdlen], p, buflen) >= buflen ) {
				pfeall(_("%s: internal error\n"),
					program_name);
				return EXIT_FAILURE;
			}
			outdlen += len;
		}
	}

	top.sb = xmalloc(sizeof(*top.sb) + outdlen + 1);
	top.path = (char*)top.sb + sizeof(*top.sb);
	strlcpy(top.path, outd, outdlen + 1);
	top.ndirs = 0;
	top.pdirs = NULL;
	top.alloc = 0;
	top.ppare = NULL;
	topdir = &top;

	pf_dbg(_("dbg: %s -> %s\n"), mntd, top.path);

	/* fake the top stat buf */
	SARG2STAT(source_args[source_index], *top.sb)

	if ( S_ISDIR(top.sb->st_mode) ) {
		if ( desired_title ) {
			/* -d selection: the following walk()
			 * will serve only for the video entries,
			 * the ouput directory must be made here:
			 */
			if ( handle_file(outd, top.sb, FTW_D) )
				return EXIT_FAILURE;
			/* don't use the VIDEO_TS directory
			 * for the select copy
			 */
			if ( strlcpy(vidd, outd, viddbufdlen) >= viddbufdlen ) {
				pfeall(
				_("%s: internal string length error"),
					program_name);
				return EXIT_FAILURE;
			}
			viddlen = outdlen;
		}
		walk();
	} else {
		int e, flag = (S_ISLNK(top.sb->st_mode)) ? FTW_SL : FTW_F;
		
		e = handle_file(mntd, top.sb, flag);
		if ( e ) {
			pfeall(_("%s: error on %s\n"), program_name, mntd);
			if ( !force )
				return EXIT_FAILURE;
		}
		free(top.sb);
		continue;
	}
	if ( !simple_copy && okvid ) {
		copy_all_vobs(dvdreader, buf);
		if ( !want_dry_run && doregmask ) {
			wr_regmask(vidd, viddlen, regmask);
		}
	}
	
	if ( !want_dry_run && preserve ) {
		pf_dbg(_("dbg: 2: rec_d_meta(&top) -> %s\n"), top.path);
		rec_d_meta(&top); /* also frees allocations */
	} else {
		free(top.sb);
	}

	pf_dbg(_("dbg: freevidentries()\n"));
	freevidentries();
	} /* for source_index */

	if ( !simple_copy && !want_dry_run && dvdreader != NULL ) {
		DVDClose(dvdreader);
		dvdreader = NULL;
	}

	print_hlink_info();
	ino_free_storage();
        blk_free_storage();

	if ( numbadblk )
		pfeopt(_("%s: found %lu bad blocks\n"),
			program_name, numbadblk);
	
	return 0;
}

int
main(int argc, char* argv[])
{
	int i;
	int texist = 0, tisdir = 0;

	if ( argv[0] && *argv[0] ) {
		char* p = strrchr(argv[0], '/');
		program_name = (p && *++p) ? p : argv[0];
	}

	setlocale(LC_ALL, "");

	pf_init_files();

	i = decode_switches(argc, argv);

	if ( desired_title_s != NULL ) {
		long n;
		char* ep;

		if ( s_tol(desired_title_s, &n, &ep, 10) ) {
			pfeall(_("%s: bad -d argument - %s (%s)\n"),
				program_name, desired_title_s,
				strerror(errno));
			usage(EXIT_FAILURE);
		}

		if ( n >= 0 && n <= 100 )
			desired_title = (int)n;
		else {
			pfeall(_("%s: bad -d argument - %s\n"),
				program_name, desired_title_s);
			usage(EXIT_FAILURE);
		}
	}

	pf_dbg(_("dbg: optind %d of %d\n"), i, argc);
	if ( i >= argc ) {
		pfeall(_("%s: source and target arguments required\n"),
			program_name);
		usage(EXIT_FAILURE);
	}
	if ( i == (argc - 1) ) {
		pfeall(_("%s: target argument required\n"),
			program_name);
		usage(EXIT_FAILURE);
	}

	source_args = xmalloc(sizeof(SARG) * (argc-i));
	for ( source_count = 0; i < argc; i++ ) {
		source_args[source_count].s = argv[i];
		if ( lstat(argv[i], &tsb) ) {
			source_args[source_count].e = errno;
		} else {
			STAT2SARG(source_args[source_count], tsb)
			source_args[source_count].e = 0;
		}
		source_count++;
	}
	target = source_args[--source_count].s;

	pf_dbg(_("dbg: %d sources -> %s\n"), source_count, target);

	/* handle cases
	 */
	if ( strcmp(target, ".") && strcmp(target, "./") &&
		strcmp(target, "..") && strcmp(target, "../") ) {
	/* it's not the dot dirs: does it exist? and
	 * what is it?
	 */
		if ( source_args[source_count].e == ENOENT ) {
			/* we must create it and
			 * must have 1 source arg
			 */
			if ( source_count > 1 ) {
				pfeall(
				_("%s: extra arguments (%d)\n"),
					program_name,
					source_count - 1);
				usage(EXIT_FAILURE);
			}
		} else if ( source_args[source_count].e ) {
			pfeall(_("%s: error with %s (%s)\n"),
				program_name, target,
				strerror(source_args[source_count].e));
			usage(EXIT_FAILURE);
		} else {
			/* target exists */
			texist = 1;
			if ( S_ISDIR(source_args[source_count].t) )
				tisdir = 1;
			if ( !tisdir && source_count > 1 ) {
				pfeall(
				_("%s: target %s is not a directory\n"),
					program_name, target);
				usage(EXIT_FAILURE);
			}
		}
	} else {
		if ( source_args[source_count].e ) {
			pfeall(_("%s: failed stat(%s) - %s\n"),
				program_name, target,
				strerror(source_args[source_count].e));
			return EXIT_FAILURE;
		}
		texist = tisdir = 1;
	}

	/* do the work */
	pf_setup(want_verbose > want_quiet, want_quiet == 0);
	return cprec(texist, tisdir);
}

/* Set all the option flags according to the switches specified.
   Return the index of the first non-option argument.  */

static int
decode_switches(int argc, char* argv[])
{
	int c;
	char* dvd = NULL;

	while ( (c = getopt_long(argc, argv, 
			   "n:"	/* node -- devnode */
			   "q"	/* quiet or silent */
			   "s"	/* simple copy */
			   "f"	/* force */
			   "p"	/* preserve */
			   "d:"	/* dvdbackup */
			   "v"	/* verbose */
#if ! HAVE_LIBDVDREAD
			   "L:"	/* libdvdr */
#endif
			   "E"	/* ignore-existing */
			   "S"	/* ignore-symlinks */
			   "H"	/* ignore-hardlinks */
			   "D"	/* ignore-specials */
			   "N"	/* ignore-nonreadable */
			   "h"	/* help */
			   "V",	/* version */
			   long_options, (int*)0)) != EOF )
	{
		switch (c)
		{
			case 'n':		/* --node */
				dvd = optarg;
				break;
			case 'q':		/* --quiet, --silent */
				want_quiet += 1;
				break;
			case 's':		/* --simple-copy */
				simple_copy = 1;
				break;
			case 'f':		/* --force */
				force = 1;
				ign_ex = 1;
				/* ign_sf was set here erroneously:
				ign_sf = 1;
				*/
				ign_ns = 1;
				ign_dnr = 1;
				break;
			case 'p':		/* --preserve */
				preserve = 1;
				break;
			case 'v':		/* --verbose */
				want_verbose += 1;
				break;
			/* dry-run is disabled; case will not match */
			case DRYRUN_CODE:	/* --dry-run */
				want_dry_run = 1;
				break;
			case 'd':		/* --dvdbackup */
				desired_title_s = optarg;
				simple_copy = 0;
				break;
#if ! HAVE_LIBDVDREAD
			case 'L':		/* --libdvdr */
				drd_libname = optarg;
				break;
#endif
			case 'E':		/* --ignore-existing */
				ign_ex = 1;
				break;
			case 'S':		/* --ignore-symlinks */
				ign_sl = 1;
				break;
			case 'H':		/* --ignore-hardlinks */
				ign_hl = 1;
				break;
			case 'D':		/* --ignore-specials */
				ign_sf = 1;
				break;
			case 'N':		/* --ignore-nonreadable */
				ign_dnr = 1;
				break;
			case 'V':
				printf("%s %s\n", program_name, VERSION);
				exit(0);

			case 'h':
				usage(0);

			default:
				usage(EXIT_FAILURE);
		}
	}

	if ( dvd != NULL )
		dvdname = dvd;
	return optind;
}


static void
usage(int status)
{
  	printf(_("%s - \
A recursive directory hierarchy copier; much like 'cp -R'.\n"), program_name);
  	printf(_("Usage: %s [OPTION] <SOURCE ...> <TARGET>\n"), program_name);

/* dry-run is unmaintained; makes segfaults */
/*  --dry-run                  take no real actions\n\ */
/* dry-run was 1st after "Options" */

  	printf(_("\
Options:\n\
  -q, --quiet, --silent      inhibit usual output\n\
  -v, --verbose              print more information\n\
  -s, --simple-copy          simple recursive copy (non dvd, default)\n\
  -f, --force                ignore open errors, overwrite existing\n\
  -p, --preserve             preserve time and mode\n\
  -d, --dvdbackup N          do video DVD backup (select title N\n\
                             if 0<N<=100, whole backup if N=0);\n\
                             requires -n NODENAME if %s is not correct\n\
  -n, --node NODENAME        device node for video DVD backup;\n\
                             required if -d N is given and\n\
                             %s is not the correct device node\n\
  -E, --ignore-existing      ignore existing output files\n\
  -S, --ignore-symlinks      ignore symbolic links; copy target\n\
  -H, --ignore-hardlinks     ignore hard links; make new copies\n\
  -D, --ignore-specials      ignore devices and pipes\n\
  -N, --ignore-nonreadable   ignore not readable source directories\n\
  %s-h, --help                 display this help and exit\n\
  -V, --version              output version information and exit\n\
%s"),
dvdnamedef, dvdnamedef,
#if ! HAVE_LIBDVDREAD
_("-L, --libdvdr NAME         use NAME as dvdread library\n  "),
#else
"",
#endif
"");
  	exit(status);
}
