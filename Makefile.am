bin_PROGRAMS=cprec
cprec_SOURCES=cprec.c cprec.h apue_ftw.c apue_ftw.h cpf.c cpf.h ino.c ino.h block_hash.c block_hash.h meta_set.h meta_set.c path_set.h path_set.c lib_misc.h lib_misc.c walk.h walk.c dl_drd.h dl_drd.c cprec.1 xmalloc.c xmalloc.h hdr_cfg.h system.h aclocal.m4 getopt.c getopt1.c getopt.h

#  uncomment the following if cprec requires the math library
#cprec_LDADD=-lm

EXTRA_DIST=cprec.lsm.in cprec.spec.in cprec.texinfo

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
