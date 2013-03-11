/**********************************************************************\
	apue_ftw --	like ftw(), but	differing in symlink handling.
			
			The name acknowledges, by its prefix, that
			the ftw() example in Stevens' APUE was the
			starting point, however different it might
			appear now.
			
			Ack too to GNU, which was looked for
			descriptor limiting (and license).

	Copyright (C) Edward V. Hynan Jr., Nov 11 2006

	The GNU GPL v2 or greater is your licence to use this code.
\**********************************************************************/

#ifndef _APUE_FTW_H_
#define _APUE_FTW_H_ 1

/* include <sys/types.h> and <sys/stat.h> before this */

#undef	FTW_F			/* file other than the following */
#undef	FTW_D			/* directory */
#undef	FTW_DNR			/* directory that can't be read */
#undef	FTW_NS			/* file that we can't stat */
#undef	FTW_SL			/* symbolic link */

#define	FTW_F	1		/* file other than the following */
#define	FTW_D	2		/* directory */
#define	FTW_DNR	3		/* directory that can't be read */
#define	FTW_NS	4		/* file that we can't stat */
#define	FTW_SL	5		/* symbolic link */

/*
 * Descend through the hierarchy, starting at "pathname".
 * The caller's func() is called for every file.
 */
int
apue_ftw(
	const char* pathname,
	int (*func)(const char*, const struct stat*, int),
	int nopenfd);

#endif /* _APUE_FTW_H_ */
