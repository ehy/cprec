bin_PROGRAMS=cprec

cprec_SOURCES=cprec.c cprec.h apue_ftw.c apue_ftw.h cpf.c cpf.h ino.c ino.h block_hash.c block_hash.h meta_set.h meta_set.c path_set.h path_set.c walk.h walk.c dl_drd.h dl_drd.c cprec.1 xmalloc.c xmalloc.h hdr_cfg.h system.h aclocal.m4
if NEED_GETOPT_C
cprec_SOURCES+=gngetopt.h getopt.c
endif
if NEED_GETOPT_LONG_C
cprec_SOURCES+=getopt1.c
endif

if WITH_DD_DVD
bin_PROGRAMS+= dd-dvd
dd_dvd_SOURCES=dd-dvd.cc dd-dvd.cc98 dl_drd.h dl_drd.c dd-dvd.1
dd_dvd_LDADD = lib_misc/lib_misc.a
if NEED_GETOPT_C
dd_dvd_SOURCES+=gngetopt.h getopt.c
endif
if NEED_GETOPT_LONG_C
dd_dvd_SOURCES+=getopt1.c
endif
endif

#  uncomment the following if cprec requires the math library
#cprec_LDADD=-lm
cprec_LDADD = lib_misc/lib_misc.a

# commented see below
#EXTRA_DIST=cprec.lsm.in cprec.spec.in cprec.texinfo

SUBDIRS = lib_misc

AM_CPPFLAGS = -I$(srcdir)/lib_misc


#  if you write a self-test script named `chk', uncomment the
#  following and add `chk' to the EXTRA_DIST list
#TESTS=chk

#  build and install the .info pages
# EH: 1-13: disable .info until time to write it;
# note that presently cprec.info seems absent
# from any *clean target -- must fix that if
# this is re-enabled.
#info_TEXINFOS = cprec.texinfo
#cprec_TEXINFOS = gpl.texinfo

#  install the man pages
man_MANS=cprec.1
if WITH_DD_DVD
man_MANS+=dd-dvd.1
endif
