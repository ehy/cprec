/**********************************************************************\
	apue_ftw --	like ftw(), but	differing in symlink handling.
			
			The name acknowledges, by its prefix, that
			the ftw() example in Stevens' APUE was the
			starting point, however different it might
			appear now.
			
			Ack too to GNU, which was looked to for
			descriptor limiting (and license).

	Copyright (C) Edward V. Hynan Jr., Nov 11 2006

	The GNU GPL v2 or greater is your licence to use this code.
\**********************************************************************/

#include "config.h"

#include "hdr_cfg.h"
#include "apue_ftw.h"
#include "lib_misc.h"

/* the following cpp lines straight from autoconf manual */
/* commented but left for example: autogen tool provided file
 * system.h which defines an equivalent of below, but with
 * 'NLENGTH' rather than 'NAMELEN'
#include <sys/types.h>
#ifdef HAVE_DIRENT_H
# include <dirent.h>
# define NAMLEN(dirent) strlen ((dirent)->d_name)
#else
# define dirent direct
# define NAMLEN(dirent) ((dirent)->d_namlen)
# ifdef HAVE_SYS_NDIR_H
#  include <sys/ndir.h>
# endif
# ifdef HAVE_SYS_DIR_H
#  include <sys/dir.h>
# endif
# ifdef HAVE_NDIR_H
#  include <ndir.h>
# endif
#endif
 * end commented
 */
/* end straight from autoconf manual */

/* some systems known to have dirp->d_namlen,
 * namely 4.4BSD derivatives not constrained to,
 * or in spite of, posix
 */
#if defined(__NetBSD__) || defined(__OpenBSD__) || defined(__FreeBSD__)
# undef NLENGTH
# define NLENGTH(dirent) ((dirent)->d_namlen)
#endif

/* should be config'd, but paranoia . . . */
#ifndef NLENGTH
# define NLENGTH(dirent) strlen((dirent)->d_name)
#endif

/*
 * The *BSD* manual for telldir(3) states that the telldir() return
 * is valid only for the currently open DIR*, and is invalid after
 * closedir(), and they mean it!  That kills the descriptor limiting
 * code using the library functions.  With #undef'd HAVE_SEEKDIR and
 * HAVE_TELLDIR alternate code simply keeps a count and uses Xseekdir()
 * (below) which just readdir()s up to the count, hoping that the dir
 * entrys will be returned in the same order.  Note that the library
 * function using code seemed to work as expected under Linux/GLibc.
 *
 * Of course it is safest to give an ndir argument large enough to
 * handle the deepest descent.
 *
 * EH: Sat Jul 19 12:37:20 UTC 2008
 */
#undef HAVE_SEEKDIR
#undef HAVE_TELLDIR

/* moot -- see above */
#if ! HAVE_SEEKDIR
#	define seekdir Xseekdir
static void Xseekdir(DIR* p, off_t c);
#endif

#if CLOSEDIR_VOID
static int iclosedir(DIR* p);
#else
#define iclosedir closedir
#endif

typedef	int	cbf_t(const char*, const struct stat*, int);

typedef struct _invariant_args {
	char*		path;
	size_t		pathlen;
	size_t		pathstrlen;
	int		nfd;
	DIR**		dpv;
	cbf_t*		func;
	struct stat	sb;
} SIVA;

static int dopath(SIVA* S, int lvl);

int
apue_ftw(const char* pathname, cbf_t* func, int nopenfd)
{
	int 	ret;
	SIVA	S;

	/* lstat: see comment below */
	if ( lstat(pathname, &S.sb) < 0 ) {
		return errno == EACCES ?
			func(S.path, &S.sb, FTW_NS) : -1;
	}

	if ( S_ISDIR(S.sb.st_mode) ) {
		/* func from lib_misc: calls patchconf(PATH_MAX) */
		int pm = get_max_per_path(pathname);

		if ( pm <= 0 ) {
			if ( ! errno )
				errno = EINVAL;
			return -1;
		}

		S.pathstrlen = strlen(pathname);
		S.pathlen = (size_t)pm + S.pathstrlen + 1;
	} else {
		S.pathstrlen = strlen(pathname);
		S.pathlen = S.pathstrlen + 1;
	}

	S.path = malloc(S.pathlen);
	if ( S.path == NULL ) {
		return -1;
	}
	
	if ( strlcpy(S.path, pathname, S.pathlen) >= S.pathlen ) {
		errno = EINVAL;
		return -1;
	}

	do {
		/* A symbolic link.  Not followed in this implementation:
		** if a dvd's udf or iso9660 filesystem has RR extension
		** and symlinks, then the link either points to
		** something on the disk, or they point outside the disk
		** and we don't want a target outside the disk fs.
		*/
		if ( S_ISLNK(S.sb.st_mode) ) {
			ret = func(S.path, &S.sb, FTW_SL);
			break;
		}

		/* not a directory */
		if ( S_ISDIR(S.sb.st_mode) == 0 ) {
			ret = func(S.path, &S.sb, FTW_F);
			break;
		}

		if ( nopenfd < 1 )
			nopenfd = 1;

		S.dpv = calloc(nopenfd, sizeof(DIR*));
		if ( S.dpv == NULL ) {
			ret = -1;
			break;
		}

		S.nfd = nopenfd;
		S.func = func;
		ret = dopath(&S, 0);
		
		free(S.dpv);
	} while ( 0 );
	
	free(S.path);
	
	return ret;
}

/*
** Descend through the hierarchy, starting at "S->path".
** "S->path" cannot be anything other than a directory.
** Call S->func(), for S->path with stat buf as received.
** Subsequently open S->path calling S->func for each non-dir,
** recursing for each dir.
*/
static int
dopath(SIVA* S, int lvl)
{
	struct dirent*	dirp;
	int		ret, dind;
	size_t		plen;
	off_t		doff;
	char*		ptr;

	/*
	** this is called with a directory.  First call S->func() for the
	** directory, then process each filename in the directory.
	*/
	if ( (ret = S->func(S->path, &S->sb, FTW_D)) != 0 )
		return ret;

	dind = lvl % S->nfd;
	if ( S->dpv[dind] != NULL ) {
		int e = errno;
		if ( iclosedir(S->dpv[dind]) )
			perror(S->path); /* leaked & confused */
		errno = e;
	}
	if ( (S->dpv[dind] = opendir(S->path)) == NULL )
		return errno == EACCES ?
			S->func(S->path, &S->sb, FTW_DNR) : -1;

	/* point to end of S->path */
	plen = strlen(S->path);
	ptr = S->path + plen;
	if ( ptr[-1] != '/' ) {
		*ptr++ = '/';
		*ptr = '\0';
		plen++;
	}

	/* read directory */
	doff = 0;
	while ( (dirp = readdir(S->dpv[dind])) != NULL ) {
		size_t nlen;
		ssize_t ptr_sz = (ssize_t)S->pathlen - (ssize_t)(ptr - S->path);
		
		#ifndef HAVE_SEEKDIR
		doff++;
		#endif

		/* ignore dot and dot-dot */
		if ( dirp->d_name[0] == '.' && (dirp->d_name[1] == '\0' ||
			(dirp->d_name[1] == '.' && dirp->d_name[2] == '\0')) )
			continue;

		/* append name */
		nlen = NLENGTH(dirp);
		if ( ptr_sz < 0
			|| (plen + nlen) >= S->pathlen
			|| ptr_sz <= strlcpy(ptr, dirp->d_name, ptr_sz) ) {
			#ifdef ENAMETOOLONG
	  		errno = ENAMETOOLONG;
			#else
	  		errno = ENOMEM;
			#endif
			ret = -1;
			break;
		}

		/* lstat: see next comment */
		if ( lstat(S->path, &S->sb) < 0 ) {
			ret = errno == EACCES ?
				S->func(S->path, &S->sb, FTW_NS) : -1;
			if ( ret ) {
				break;
			}
			continue;
		}

		/* A symbolic link.  Not followed in this implementation:
		** if a dvd's udf or iso9660 filesystem has RR extension
		** and symlinks, then the link either points relatively to
		** something on the disk, or they point outside the disk
		** and we don't care about a target outside the disk fs.
		*/
		if ( S_ISLNK(S->sb.st_mode) ) {
			if ( (ret = S->func(S->path, &S->sb, FTW_SL)) != 0 ) {
				break;
			}
			continue;
		}

		/* not a directory */
		if ( S_ISDIR(S->sb.st_mode) == 0 ) {
			if ( (ret = S->func(S->path, &S->sb, FTW_F)) != 0 ) {
				break;
			}
			continue;
		}

		/* directory, go recursive */
		#if HAVE_TELLDIR
		doff = telldir(S->dpv[dind]);
		#endif
		if ( doff == -1 ) {
			perror(S->path);
			ret = -1;
			break;
		}
		ret = dopath(S, lvl + 1);
		if ( ret != 0 )
			break;	/* cancelled by S->func() */
		if ( S->dpv[dind] == NULL ) {
			int e;
			ptr[-1] = '\0';
			if ( (S->dpv[dind] = opendir(S->path)) == NULL ) {
				perror(S->path);
				return -1;
			}
			e = errno;
			errno = 0;
			seekdir(S->dpv[dind], doff);
			if ( errno ) {
				perror(S->path);
				ret = -1;
				break;
			}
			errno = e;
			ptr[-1] = '/';
		}
	}
	
	/* erase current change of string */
	ptr[-1] = '\0';

	if ( S->dpv[dind] != NULL && iclosedir(S->dpv[dind]) < 0 ) {
		perror(S->path);
		ret = -1;
	}
	S->dpv[dind] = NULL;

	return ret;
}

#if ! HAVE_SEEKDIR
static void Xseekdir(DIR* p, off_t c)
{
	if ( c < 0 )
		return;

	while ( c-- ) {
		if ( readdir(p) == NULL )
			break;
	}
}
#endif

#if CLOSEDIR_VOID
static int iclosedir(DIR* p)
{
	closedir(p);
	return 0;
}
#endif
