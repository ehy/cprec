# This library is not meant for installation on system
noinst_LIBRARIES = lib_misc.a
# but of course it is meant to be built
lib_LIBRARIES = lib_misc.a
lib_misc_a_SOURCES=lib_misc.c lib_misc.h lmsc_chcase.c lmsc_get_max_hlink.c lmsc_get_max_path.c lmsc_get_nofd.c lmsc_get_page_size.c lmsc_mk_aligned_ptr.c lmsc_pfio.c lmsc_statihack.c lmsc_s_tol.c lmsc_strlcpy.c lmsc_wrall.c

#  uncomment the following if lib_misc requires the math library
#lib_misc_LDADD=-lm

#  if you write a self-test script named `chk', uncomment the
#  following and add `chk' to the EXTRA_DIST list
#TESTS=chk

EXTRA_DIST = Makefile.posix

