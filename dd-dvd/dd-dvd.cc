//
//
/* 
   dd-dvd.c++ -- 'dd' a video DVD using libdvdread API on video related
   data so that libdvdread may employ libdvdcss if available

   Copyright (C) 2010 Ed Hynan

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


#include <string>
#include <vector>
#include <list>
#include <map>
#include <algorithm>
#include <functional>
#include <utility>
#include <stdexcept>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <cerrno>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>

#   if defined(__sun) && ! defined(__linux)
#      include <sys/mnttab.h>
#      ifndef MNTTAB
#         error "on sun MNTTAB macro is expected in sys/mnttab.h: FIXME"
#      endif
#   elif ! NEED_GETFSFILE
#      include <fstab.h>
#   endif

#include <dvdread/dvd_reader.h>

#   if 	HAVE_DVD_UDF_H
#include <dvdread/dvd_udf.h>
#   else  // if 	HAVE_DVD_UDF_H
// Ubuntu libdvdread package includes dvd_udf.h in installation;
// OpenBSD 4.4 for example does not -- add proto and hope for link
extern "C" {
uint32_t
UDFFindFile(dvd_reader_t *device, char *filename, uint32_t *size);
}
#   endif // if 	HAVE_DVD_UDF_H

#ifndef STDOUT_FILENO
#   define STDOUT_FILENO 1
#endif

#if defined(_SC_PAGE_SIZE) && ! defined(_SC_PAGESIZE)
#   define _SC_PAGESIZE _SC_PAGE_SIZE
#endif
#ifdef _SC_PAGESIZE
#   define HAVE_SYSCONF 1
#else // untested; just fail if false
#   define HAVE_GETPAGESIZE 1
#endif

using namespace std;
using namespace rel_ops;

template <class T> class auto_array {
    T* p;
public:
    auto_array(T* parray = 0) : p(parray) {}
    auto_array(size_t sz) : p(new T[sz]) {}
    ~auto_array() { delete[] p; }
    operator T* () { return p; }
    operator const T* () const { return p; }
};

const size_t blk_sz = DVD_VIDEO_LB_LEN; // this is 2048

const size_t block_read_count = 4096;

typedef dvd_reader_t* dvd_reader_p;

size_t numbadblk = 0;
size_t retrybadblk = 2;
int verbose;
bool dryrun = false;
unsigned char* iobuffer;

const char vtfdir[] = "/VIDEO_TS/";
const char vtftpl[] = "/VIDEO_TS/VTS_01_1.VOB";
const char vtfmnu[] = "/VIDEO_TS/VIDEO_TS.%s";
const char vtffmt[] = "VTS_%02u_%u.%s";
const char* vtfext[3] = { "IFO", "VOB", "BUP" };

char vtfbuf[sizeof(vtftpl)];

enum vtf_type {
	vtf_ifo = 0, vtf_vob = 1, vtf_bup = 2
};

char*
mk_vtf_path(unsigned ts, unsigned tn, vtf_type ft = vtf_vob)
{
	if ( ts == 0 ) {
		snprintf(vtfbuf, sizeof(vtfbuf), vtfmnu, vtfext[ft]);
		return vtfbuf;
	}

	char* p = vtfbuf;

	strncpy(p, vtfdir, sizeof(vtfbuf));
	p += sizeof(vtfdir) - 1;
	snprintf(p, sizeof(vtfbuf) - (sizeof(vtfdir) - 1),
		vtffmt, ts, tn, vtfext[ft]);

	return vtfbuf;
}

int
get_page_size()
{
	int s;

#if HAVE_SYSCONF
	s = (int)sysconf(_SC_PAGESIZE);
        if ( s < 0 ) {
		perror("sysconf(_SC_PAGESIZE)");
        }
#elif HAVE_GETPAGESIZE
	s = getpagesize();
        if ( s < 0 ) {
		perror("getpagesize()");
        }
#else
#	error "Fix get_page_size() somehow!"
#endif
        if ( s <= 0 ) {
		exit(EXIT_FAILURE);
        }

	return s;
}

unsigned char*
mk_aligned_ptr(unsigned char* up)
{
	const size_t p_sz = sizeof(char*);
	int pgsz = get_page_size();

	if ( p_sz == 8 ) {
		up += pgsz - ((uint64_t)up & (uint64_t)(pgsz-1));
	} else if ( p_sz == 4 ) {
		up += pgsz - ((uint32_t)(uint64_t)up & (uint32_t)(pgsz-1));
	} else {
		fprintf(stderr, "cannot handle pointer size %u\n",
			unsigned(p_sz));
		exit(EXIT_FAILURE);
	}

	return up;
}

ssize_t
write_all(int fd, void* buf, size_t count)
{
        ssize_t rem, tw;
        char* p = static_cast<char*>(buf);

        for ( rem = count; rem; ) {
                tw = write(fd, &p[count-rem], rem);
                if ( tw < 0 ) {
                        if ( errno == EAGAIN || errno == EINTR ) {
                                #if DEBUG_IO_INTR
				perror("continuing interrupted write");
				#endif
				continue;
			}
                        return tw;
                }
                rem -= tw;
        }

        return count;
}

ssize_t
read_all(int fd, void* buf, size_t count)
{
        ssize_t rem, tw;
        char* p = static_cast<char*>(buf);

        for ( rem = count; rem; ) {
                tw = read(fd, &p[count-rem], rem);
                if ( tw < 0 ) {
                        if ( errno == EAGAIN || errno == EINTR ) {
                                #if DEBUG_IO_INTR
                                perror("continuing interrupted read");
				#endif
                                continue;
			}
                        return tw;
                }
		if ( tw == 0 ) {
			return count - rem;
		}
                rem -= tw;
        }

        return count;
}


// not just VOB actually; ifo/bup too
class vt_file {
public:
	uint32_t block, size;
	unsigned nset, nfile;
	vtf_type type;
	string name;

	vt_file(const vt_file& o)
	{ *this = o; }

	vt_file(string nm, uint32_t blk, uint32_t sz,
		unsigned setn, unsigned filen, vtf_type typ = vtf_vob)
	 : block(blk), size(sz), nset(setn), nfile(filen), name(nm), type(typ)
	{ }

	bool isvob() const { return type == vtf_vob; }

	bool isifo() const { return type == vtf_ifo; }

	bool isbup() const { return type == vtf_bup; }

	// bogus == and < but suits purpose herein
	bool operator == (const vt_file& o) const {
		return block == o.block;
	}

	bool operator < (const vt_file& o) const {
		return block < o.block;
	}

	const vt_file&
	operator = (const vt_file& o) {
		block = o.block;
		size = o.size;
		nset = o.nset;
		nfile = o.nfile;
		type = o.type;
		name = o.name;
		return *this;
	}
};

typedef list<vt_file> file_list;

// set of vt_file: groups of VOB from each VTS, as they
// contain contiguous a/v data (excluding *_0.VOB, the menu)
// and appear in sequence in the filesystem.
// *.{IFO,BUP} and VIDEO_TS.VOB are handled separately and so
// their 'sets' have single files
class vtf_set {
public:
	unsigned nset;
	vtf_type type;
	file_list lst;
	uint32_t block_1st;

	vtf_set(unsigned setn = 0, vtf_type typ = vtf_vob)
	 : nset(setn), type(typ), block_1st(0)
	{ }

	vtf_set(const vtf_set& o)
	{ *this = o; }

	vtf_set(const file_list& flist)
	 : nset(0), type(vtf_vob), lst(flist), block_1st(0)
	{
		lst.sort();
		file_list::iterator i = lst.begin();
		if ( i != lst.end() ) {
			nset = (*i).nset;
			type = (*i).type;
			block_1st = (*i).block;
		}
	}

	void addfile(const vt_file& fil) throw(invalid_argument)
	{
		if ( fil.nset != nset || fil.type != type ) {
			throw invalid_argument("VT set mismatch");
		}
		if ( find(lst.begin(), lst.end(), fil) == lst.end() ) {
			lst.push_back(fil);
			lst.sort();
		}
		block_1st = lst.front().block;
	}

	vt_file& operator [](int ix) throw(invalid_argument)
	{
		if ( ix < 0 || ix >= count() ) {
			throw invalid_argument(
				"VT set index out of range");
		}
		file_list::iterator i = lst.begin();
		file_list::iterator e = lst.end();
		for ( unsigned n = 0; i != e; n++, i++ ) {
			if ( n == unsigned(ix) ) {
				return *i;
			}
		}
		throw invalid_argument("VT set index invalid");
	}

	const vt_file& operator [](int ix) const throw(invalid_argument)
	{
		if ( ix < 0 || ix >= count() ) {
			throw invalid_argument(
				"VT set index out of range");
		}
		file_list::const_iterator i = lst.begin();
		file_list::const_iterator e = lst.end();
		for ( unsigned n = 0; i != e; n++, i++ ) {
			if ( n == unsigned(ix) ) {
				return *i;
			}
		}
		throw invalid_argument("VT set index invalid");
	}

	size_t count() const { return lst.size(); }

	void print(const char* pfx = "") const
	{
		file_list::const_iterator i = lst.begin();
		file_list::const_iterator e = lst.end();
		for ( ; i != e; i++ ) {
			const vt_file& vf = *i;
			fprintf(stderr, "%s%s %u: %s\n",
				pfx,
				vtfext[vf.type],
				vf.nfile,
				vf.name.c_str());
		}
	}

	bool operator == (const vtf_set& o) const {
		return (nset == o.nset) && (type == o.type);
	}

	bool operator < (const vtf_set& o) const {
		return (nset < o.nset) ||
			((nset == o.nset) && (type < o.type));
	}

	const vtf_set&
	operator = (const vtf_set& o) {
		nset = o.nset;
		type = o.type;
		lst = o.lst;
		block_1st = o.block_1st;
		return *this;
	}
};


// map index for map of vtf_set objects; so that
// index may include not only VTS number, but
// type, allowing separation of VTS_## ifo, vob, and bup
class vtf_set_index {
public:
	unsigned nset;
	vtf_type type;

	vtf_set_index(unsigned ns = 0, vtf_type typ = vtf_vob)
	 : nset(ns), type(typ) {}

	vtf_set_index(const vtf_set_index& o) { *this = o; }

	const vtf_set_index&
	operator = (const vtf_set_index& o)
	{
		nset = o.nset;
		type = o.type;
		return *this;
	}

	bool operator == (const vtf_set_index& o) const
	{
		return (nset == o.nset) && (type == o.type);
	}

	bool operator < (const vtf_set_index& o) const
	{
		return (nset < o.nset) ||
			((nset == o.nset) && (type < o.type));
	}

	operator unsigned() const
	{
		return (nset << 8) | unsigned(type);
	}
};

typedef vector<vtf_set_index> setnum_list;
// may use map<vtf_set_index, vtf_set> or map<unsigned, vtf_set>;
// vtf_set_index::operator unsigned() value will compare < and ==
// same as vtf_set_index object -- unsigned key might make smaller
// code and and guard against flaky std::map or compiler, but
// vtf_set_index key prevents unintended unsigned argument.
//typedef map<unsigned, vtf_set> vt_set_map;
typedef map<vtf_set_index, vtf_set> vt_set_map;

void
setmap_build(const file_list& flst, setnum_list& slst, vt_set_map& smap)
{
	file_list::const_iterator i = flst.begin();
	file_list::const_iterator e = flst.end();
	for ( ; i != e; i++ ) {
		unsigned ns = (*i).nset;
		vtf_type ty = (*i).type;

		vtf_set_index ix(ns, ty);

		if ( smap.find(ix) == smap.end() ) {
			slst.push_back(ix);
			vtf_set set(ns, ty);
			smap[ix] = set;
		}

		smap.find(ix)->second.addfile(*i);
	}
}

void
setmap_print(const setnum_list& slst, const vt_set_map& smap)
{
	fprintf(stderr, "\nVideo file groups:\n");

	vt_set_map::const_iterator es = smap.end();
	for ( size_t n = 0; n < slst.size(); n++ ) {
		vtf_set_index ix(slst[n]);

		fprintf(stderr, "  VT set %02u (%s) containing:\n",
			ix.nset,
			vtfext[ix.type]);

		vt_set_map::const_iterator vs = smap.find(ix);
		if ( vs != es ) {
			vs->second.print("    ");
		}
	}
}

void
list_add_file(file_list& lst, const vt_file& fil)
{
	file_list::iterator i = lst.begin();
	file_list::iterator e = lst.end();

	for ( ; i != e; i++ ) {
		if ( *i != fil ) {
			continue;
		}
		if ( (*i).size < fil.size ) {
			*i = fil;
		}
		break;
	}

	if ( i == e ) {
		lst.push_back(fil);
	}
}

void
list_sort(file_list& lst)
{
	lst.sort();
}

void
list_print(file_list& lst)
{
	fputs("The following VTS files have been found:\n",
		stderr);
	fputs("####       block        size                    name\n",
		stderr);
	fputs("====================================================\n",
		stderr);

	file_list::iterator i = lst.begin();
	file_list::iterator e = lst.end();

	for ( unsigned n = 0; i != e; i++, n++ ) {
		fprintf(stderr, "%03u)  %10llu  %10llu  %s\n"
		    , n
		    , (unsigned long long)(*i).block
		    , (unsigned long long)(*i).size
		    , (*i).name.c_str()
		    );
	}
}

void
list_build(file_list& lst, dvd_reader_p drd)
{
	char* pnm;
	uint32_t blk, sz;
	
	for ( unsigned setn = 0; setn < 100; setn++ ) {
		// IFO
		pnm = mk_vtf_path(setn, 0, vtf_ifo);
		blk = ::UDFFindFile(drd, pnm, &sz);
		if ( blk != 0 ) {
			string nm(pnm);
			vt_file vf(nm, blk, sz, setn, 0, vtf_ifo);
			list_add_file(lst, vf);
		}

		// BUP
		pnm = mk_vtf_path(setn, 0, vtf_bup);
		blk = ::UDFFindFile(drd, pnm, &sz);
		if ( blk != 0 ) {
			string nm(pnm);
			vt_file vf(nm, blk, sz, setn, 0, vtf_bup);
			list_add_file(lst, vf);
		}

		// VOB
		for ( unsigned fn = 0; fn < 10; fn++ ) {
			if ( setn == 0 && fn > 0 ) {
				break;
			}
			pnm = mk_vtf_path(setn, fn);
			string nm(pnm);
			blk = ::UDFFindFile(drd, pnm, &sz);
			if ( blk == 0 ) {
				continue;
			}

			vt_file vf(nm, blk, sz, setn, fn);
			list_add_file(lst, vf);
		}
	}

	list_sort(lst);
}

/* if poff==0 do fd copy else do vob copy */
/*
 *  call when read fails with io error; assume optical medium fault.
 *  zero the destination buffer and try reading one block at a time.
 *  if read fails w/ EIO advanvce one block (writing zeroes).
 *  return -1 for errors other than EIO.
 */
ssize_t
copy_vob_badblks(
	dvd_file_t* dvdfile,
	int inp, int out,
	unsigned char* buf,
	size_t blkcnt,
	int* poff = 0
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
		perror("lseek cur in copy_badblocks");
		errno = t;
		return -1;
	}

	nbr = retrybadblk;

	while ( cnt ) {
		ssize_t nb;
		nbr = min(nbr, cnt);
		
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
			fprintf(stderr, "FATAL internal error: inp == %d\n",
				inp);
			errno = EINVAL;
			return -1;
		}
		
		if ( nb == 0 ) {
			break;
		} else if ( nb < 0 ) {
			if ( errno != EIO ) {
				perror(poff ?
					"dvdread in copy_badblocks" :
					"read in copy_badblocks"
				);
				return -1;
			}

			memset(prd, 0, nbr * blk_sz);

			nb = nbr;
			bad += nb;
		} else {
			good += nb;
		}
		
		if ( poff ) {
			*poff += (int)nb;
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
		perror("write in copy_badblks");				
		return -1;
	}
	
	numbadblk += bad;
	tm2 = time(0);
	fprintf(stderr,
		"%lu bad blocks zeroed in read of %lu "
		"(%g good blocks) in %llu seconds\n",
		bad, (unsigned long)blkcnt,
		(double)good / (double)blkcnt,
		(unsigned long long)tm2 - tm1);
	
	return cnt;
}


// copy IFO of BUP with DVDReadBytes()
ssize_t
copy_ifo(
	dvd_file_t* dvdfile,
	int inp, int out,
	unsigned char* buf,
	size_t blkcnt,
	int* poff = 0
	)
{
	unsigned nxrd = 0;
	const unsigned lxrd = 512;
	size_t cnt = blkcnt;

	errno = 0;
	DVDFileSeek(dvdfile, int32_t(0));

	while ( cnt ) {
		//ssize_t nb;
		size_t  nbr = min(cnt, block_read_count);
		size_t bcnt = nbr * blk_sz;
		
		while ( bcnt ) {
			ssize_t bret = DVDReadBytes(
				dvdfile, buf, bcnt);
			if ( bret < 0 ) {
				perror("DVDReadBytes");
				return -1;
			}
			bcnt -= bret;

			while ( bret ) {
				ssize_t wret = write_all(out, buf, bret);
				if ( wret < 0 ) {
					perror("DVDReadBytes->write");
					return -1;
				}
				bret -= wret;
			}
		}
		
		cnt -= nbr;
	}

	return blkcnt - cnt;
}

// if poff==0 do fd copy else do vob copy
ssize_t
copy_vob(
	dvd_file_t* dvdfile,
	int inp, int out,
	unsigned char* buf,
	size_t blkcnt,
	int* poff = 0
	)
{
	size_t cnt = blkcnt;

	errno = 0;

	while ( cnt ) {
		ssize_t nb;
		size_t  nbr = min(cnt, block_read_count);
		
		if ( poff ) {
			nb = DVDReadBlocks(dvdfile, *poff, nbr, buf);
		} else {
			ssize_t ssz = read_all(inp, buf, nbr * blk_sz);
			if ( ssz <= 0 ) {
				nb = ssz;
			} else {
				ssize_t rmd = ssz % blk_sz;
				if ( rmd ) {
					lseek(inp, off_t(0) - rmd, SEEK_CUR);
				}
				nb = ssz / blk_sz;
			}
		}
		
		if ( nb <= 0 ) {
			perror("DVD read");
			errno = 0;
			/* call desperation procedure:
			 * will write bogus data for failed
			 * reads on the premise that still
			 * a video dvd _might_ remain usable
			 */
			nb = copy_vob_badblks(
				dvdfile, inp, out, buf, nbr, poff);
			if ( nb > 0 ) {
				cnt -= nb;
				continue;
			}	

			perror("DVD bad blocks: cannot salvage");

			return -1;
		}

		if ( poff ) {
			*poff += (int)nb;
		}
		cnt -= nb;
		nb *= blk_sz;

		if ( write_all(out, buf, nb) != nb ) {
			perror("write DVD data");
	
			return -1;
		}
	}

	return blkcnt - cnt;
}

off_t
dd_ops_print(const setnum_list& slst, const vt_set_map& smap, size_t tot_blks)
{
	fprintf(stderr, "\nDD operations on %zu blocks:\n",
		tot_blks);

	off_t fptr = 0;

	for ( unsigned n = 0; n < slst.size(); n++ ) {
		vtf_set_index ix(slst[n]);
		const vtf_set& vs = smap.find(ix)->second;

		fprintf(stderr, "file group %02u:%s, %zu files:\n",
			vs.nset, vtfext[vs.type], vs.count());

		for ( size_t nvf = 0; nvf < vs.count(); nvf++ ) {
			const vt_file& vf = vs[nvf];

                        // basic error checks
			if ( off_t(vf.block) < fptr ) {
				fprintf(stderr,
				    "internal error: wanted block %llu"
                                    ", had %llu (new offset < current)\n",
					(unsigned long long)fptr,
					(unsigned long long)vf.block);
				exit(EXIT_FAILURE);
			}
			if ( vf.size % blk_sz ) {
				fprintf(stderr,
				    "input error: vob(%u,%u) size %%"
                                    " blocks size == %llu (file size"
                                    " not multiple of blocks)\n",
					vf.nset, vf.nfile,
					(unsigned long long)(vf.size % blk_sz));
				exit(EXIT_FAILURE);
			}

			// if space between vts files, do DD copy
			size_t ddbsz = size_t(vf.block) - fptr;
			if ( ddbsz ) {
				fprintf(stderr,
				    "DD at %llu to %llu:"
				    " %zu blocks, %zu bytes\n",
					(unsigned long long)fptr,
					(unsigned long long)fptr + ddbsz,
					ddbsz,
					ddbsz * blk_sz);
				fptr += off_t(ddbsz);
			}

			// copy DVD type data:
                        // setup libdvdread 'domain'
			vtf_type ftype = vf.type;
			const char* sdom;
			if ( ftype == vtf_vob ) {
				sdom =   vf.nfile ?
					"DVD_READ_TITLE_VOBS" :
					"DVD_READ_MENU_VOBS";
			} else if ( ftype == vtf_ifo ) {
				sdom = "DVD_READ_INFO_FILE";
			} else {
				sdom = "DVD_READ_INFO_BACKUP_FILE";
			}
			
			size_t rsz = vf.size / blk_sz;
			fprintf(stderr,
			    "%s(%u, %u) at %llu to %llu:"
			    " %llu blocks, %llu bytes"
			    " in domain %s\n",
				vtfext[vf.type], vf.nset, vf.nfile,
				(unsigned long long)fptr,
				(unsigned long long)fptr + rsz,
				(unsigned long long)rsz,
				(unsigned long long)vf.size,
				sdom);
			fptr += rsz;
		}
	}

	// final dd of remaining data
	if ( size_t(fptr) < tot_blks ) {
		size_t ddbsz = off_t(tot_blks) - fptr;
		fprintf(stderr,
		    "DD remainder at %llu to %llu: %zu blocks, %zu bytes\n",
			(unsigned long long)fptr,
			(unsigned long long)fptr + ddbsz,
			ddbsz,
			ddbsz * blk_sz);
		fptr += off_t(ddbsz);
	}
	if ( size_t(fptr) > tot_blks ) {
		fprintf(stderr,
		    "ERROR: write offset > total blocks: %llu > %zu\n",
			(unsigned long long)fptr, tot_blks);
		exit(EXIT_FAILURE);
	}

	fprintf(stderr, "DD operations: %llu blocks, %llu bytes to write\n",
		(unsigned long long)fptr,
		(unsigned long long)fptr * blk_sz);

	return fptr;
}

off_t
dd_ops_exec(
	const setnum_list& slst,
	const vt_set_map& smap,
	size_t tot_blks,
	dvd_reader_p dvd, int inp, int out
	)
{
	fprintf(stderr, "\nDD of %zu block filesystem:\n",
		tot_blks);

	off_t fptr = 0;

	for ( unsigned n = 0; n < slst.size(); n++ ) {
		vtf_set_index ix(slst[n]);
		const vtf_set& vs = smap.find(ix)->second;

		fprintf(stderr, "file group %02u:%s, %zu files:\n",
			vs.nset, vtfext[vs.type], vs.count());

		int setoff = 0;
		for ( size_t nvf = 0; nvf < vs.count(); nvf++ ) {
			const vt_file& vf = vs[nvf];
			
                        // basic error checks
                        if ( off_t(vf.block) < fptr ) {
				fprintf(stderr,
				    "internal error: wanted block %llu"
                                    ", had %llu (new offset < current)\n",
					(unsigned long long)fptr,
					(unsigned long long)vf.block);
				exit(EXIT_FAILURE);
			}
			if ( vf.size % blk_sz ) {
				fprintf(stderr,
				    "input error: vob(%u,%u) size %%"
                                    " blocks size == %llu (file size"
                                    " not multiple of blocks)\n",
					vf.nset, vf.nfile,
					(unsigned long long)(vf.size % blk_sz));
				exit(EXIT_FAILURE);
			}

			// if space between vts files, do DD copy
			size_t ddbsz = size_t(vf.block) - fptr;
			if ( ddbsz ) {
				fprintf(stderr,
				    "DD at %llu to %llu:"
				    " %zu blocks, %zu bytes\n",
					(unsigned long long)fptr,
					(unsigned long long)fptr + ddbsz,
					ddbsz,
					ddbsz * blk_sz);

				off_t pos = fptr * blk_sz;
				off_t ret = lseek(inp, pos, SEEK_SET);
				if ( ret != pos ) {
					fprintf(stderr,
					    "failed input seek to %llu\n",
						(unsigned long long)pos);
					exit(EXIT_FAILURE);
				}
				ret = copy_vob(0, inp, out, iobuffer, ddbsz, 0);
				if ( ret != ddbsz ) {
					fprintf(stderr,
					    "DD failed at block %llu, %zu\n",
						(unsigned long long)fptr,
						ddbsz);
					exit(EXIT_FAILURE);
				}
				fptr += off_t(ddbsz);
			}

			// copy DVD type data:
                        // setup libdvdread 'domain'
			vtf_type ftype = vf.type;
			dvd_read_domain_t dom;
			const char* sdom;
			if ( ftype == vtf_vob ) {
				dom =   vf.nfile ?
					DVD_READ_TITLE_VOBS :
					DVD_READ_MENU_VOBS;
				sdom =   vf.nfile ?
					"DVD_READ_TITLE_VOBS" :
					"DVD_READ_MENU_VOBS";
			} else if ( ftype == vtf_ifo ) {
				dom = DVD_READ_INFO_FILE;
				sdom = "DVD_READ_INFO_FILE";
			} else {
				dom = DVD_READ_INFO_BACKUP_FILE;
				sdom = "DVD_READ_INFO_BACKUP_FILE";
			}
			
			// copy DVD type data:
                        // open libdvdread 'domain'
			dvd_file_t* df = DVDOpenFile(dvd, int(vf.nset), dom);
			if ( df == 0 ) {
				fprintf(stderr,
				    "failed to open title %u at block %llu\n",
					vf.nset,
					(unsigned long long)vf.block);
				exit(EXIT_FAILURE);
			}

			// copy DVD type data:
                        // use libdvdread API (within copy*()) per file type
			size_t szr;
			size_t rsz = vf.size / blk_sz;
			fprintf(stderr,
			    "%s(%u, %u) at %llu to %llu:"
			    " %llu blocks, %llu bytes"
			    " in domain %s\n",
				vtfext[vf.type], vf.nset, vf.nfile,
				(unsigned long long)fptr,
				(unsigned long long)fptr + rsz,
				(unsigned long long)rsz,
				(unsigned long long)vf.size,
				sdom);
			int t = 0;
			if ( vf.nfile == 0 ) {
				szr = ftype == vtf_vob
				? copy_vob(df, -1, out, iobuffer, rsz, &t)
				: copy_ifo(df, -1, out, iobuffer, rsz, &t);
			} else {
				szr = ftype == vtf_vob
				? copy_vob(df, -1, out, iobuffer, rsz, &setoff)
				: copy_ifo(df, -1, out, iobuffer, rsz, &t);
			}

			// copy DVD type data:
                        // error check
			if ( szr != rsz ) {
				fprintf(stderr,
				    "failed copy title %u.%u at block %llu\n",
					vf.nset, vf.nfile,
					(unsigned long long)vf.block);
				exit(EXIT_FAILURE);
			}

			// update pointer and loop
                        fptr += rsz;
			DVDCloseFile(df);
		}
	}

	// final dd of remaining data
	if ( size_t(fptr) < tot_blks ) {
		size_t ddbsz = off_t(tot_blks) - fptr;
		fprintf(stderr,
		    "DD remainder at %llu to %llu: %zu blocks, %zu bytes\n",
			(unsigned long long)fptr,
			(unsigned long long)fptr + ddbsz,
			ddbsz,
			ddbsz * blk_sz);

		off_t pos = fptr * blk_sz;
		off_t ret = lseek(inp, pos, SEEK_SET);
		if ( ret != pos ) {
			fprintf(stderr,
				"failed input seek to %llu\n",
				(unsigned long long)pos);
			exit(EXIT_FAILURE);
		}
		ret = copy_vob(0, inp, out, iobuffer, ddbsz, 0);
		if ( ret != ddbsz ) {
			fprintf(stderr,
				"DD failed at block %llu, %zu\n",
				(unsigned long long)fptr,
				ddbsz);
			exit(EXIT_FAILURE);
		}
		fptr += off_t(ddbsz);
	}

	if ( size_t(fptr) > tot_blks ) {
		fprintf(stderr,
		    "ERROR: write offset > total blocks: %llu > %zu\n",
			(unsigned long long)fptr, tot_blks);
		exit(EXIT_FAILURE);
	}

	fprintf(stderr, "DONE: %llu blocks, %llu bytes written\n",
		(unsigned long long)fptr,
		(unsigned long long)fptr * blk_sz);

	return fptr;
}

size_t
get_vol_blocks(int fd)
{
	off_t ocur = lseek(fd, 0, SEEK_CUR);
	if ( ocur < 0 ) {
		perror("lseek(SEEK_CUR)");
		// no fail return: exit
		exit(EXIT_FAILURE);
	}

	const off_t seek1 = 2048 * 16;
        if ( lseek(fd, seek1, SEEK_SET) != seek1 ) {
                perror("lseek(SEEK_SET)");
                exit(EXIT_FAILURE);
        }

        if ( read_all(fd, iobuffer, 2048) != 2048 ) {
                perror("read(2048)");
                exit(EXIT_FAILURE);
        }

        const size_t boff = 84;
        const size_t loff = 80;

        unsigned char* pd;

        pd = &iobuffer[loff];
        uint32_t lblk = (uint32_t(pd[0]) <<  0) | (uint32_t(pd[1]) <<  8) |
                        (uint32_t(pd[2]) << 16) | (uint32_t(pd[3]) <<  24);

        pd = &iobuffer[boff];
        uint32_t bblk = (uint32_t(pd[0]) << 24) | (uint32_t(pd[1]) << 16) |
                        (uint32_t(pd[2]) <<  8) | (uint32_t(pd[3]) <<  0);

	// optional sanity check:
	if ( lblk != bblk ) {
		fprintf(stderr, "failed to get volume block count\n");
		exit(EXIT_FAILURE);
	}

	ocur = lseek(fd, ocur, SEEK_SET);
	if ( ocur < 0 ) {
		perror("lseek(SEEK_SET)");
		// no fail return: exit
		exit(EXIT_FAILURE);
	}

	return size_t(bblk);
}

bool
get_mount_dev(const char* mtpt, string& name)
{
#   if defined(__sun) && ! defined(__linux)
	FILE* fp = fopen(MNTTAB, "r");
	if ( fp == 0 ) {
		perror(MNTTAB);
		fprintf(stderr, "cannot open %s\n", MNTTAB);
		return false;
	}
	struct mnttab sm;
	int gr;
	while ( (gr = getmntent(fp, &sm)) == 0 ) {
		if ( strcmp(mtpt, sm.mnt_mountp) ) {
			continue;
		}
		name = sm.mnt_special;
		fprintf(stderr,
			"using device %s for argument %s\n",
			sm.mnt_special, mtpt);
		fclose(fp);
		return true;
	}
	if ( gr > 0 ) {
		perror("getmntent");
	}
	fclose(fp);
	fprintf(stderr, "cannot find device for %s\n", mtpt);
	return false;
#   elif ! NEED_GETFSFILE
	struct fstab* stp = getfsfile(mtpt);
	if ( stp == 0 ) {
		fprintf(stderr,
			"cannot find device for %s\n",
			mtpt);
		endfsent();
		return false;
	}
	name = stp->fs_spec;
	fprintf(stderr,
		"using device %s for argument %s\n",
		stp->fs_spec, mtpt);
	endfsent();
	return true;
#   else
	return false;
#   endif
}

int
main(int argc, char* argv[])
{
	if ( argc < 2 ) {
		fprintf(stderr, "input device argument needed!\n");
		fprintf(stderr, "optional next argument of output\n");
		return EXIT_FAILURE;
	} else if ( argc > 3 ) {
		fprintf(stderr, "input device argument needed!\n");
		fprintf(stderr, "optional next argument of output\n");
		fprintf(stderr, "too many arguments!\n");
		return EXIT_FAILURE;
	}

	struct stat sb;
	if ( stat(argv[1], &sb) ) {
		perror(argv[1]);
		return EXIT_FAILURE;
	}

	auto_array<unsigned char> buffalloc(
		block_read_count * blk_sz + get_page_size()
		);
	iobuffer = mk_aligned_ptr(buffalloc);

	// allowing character dev too, as it might work on BSD
	string inname;
	if ( S_ISREG(sb.st_mode) ||
	     S_ISCHR(sb.st_mode) || S_ISBLK(sb.st_mode) ) {
		inname = argv[1];
	} else if ( S_ISDIR(sb.st_mode) ) {
		if ( get_mount_dev(argv[1], inname) == false ) {
			fprintf(stderr, "if %s is the mount point"
				" of a DVD device, give device name"
				" instead\n", argv[1]);
			return EXIT_FAILURE;
		}
	} else {
		fprintf(stderr, "unsupported file type %s\n",
			argv[1]);
		return EXIT_FAILURE;
	}

	{
		const char* ep;
		if ( (ep = getenv("DDD_DRYRUN")) != 0 ) {
			if ( strcasecmp(ep, "0") &&
			     strcasecmp(ep, "no") &&
			     strcasecmp(ep, "false") ) {
				dryrun = true;
			}
		}
		if ( (ep = getenv("DDD_VERBOSE")) != 0 ) {
			if ( !strcasecmp(ep, "0") ||
			     !strcasecmp(ep, "no") ||
			     !strcasecmp(ep, "false") ) {
				verbose = 0;
			} else {
				int v;
				switch ( *ep ) {
					case '0': v = 0; break;
					case '1': v = 1; break;
					case '2': v = 2; break;
					case '3': v = 3; break;
					default:  v = 4; break;
				}
				verbose = v;
			}
		}
		if ( (ep = getenv("DDD_RETRYBLOCKS")) != 0 ) {
			errno = 0;
			long lv = strtol(ep, 0, 0);
			
			if ( errno || lv < 1 || lv > block_read_count ) {
				perror("bad \"DDD_RETRYBLOCKS\" value");
				fprintf(stderr,
					"using default %zu\n", retrybadblk);
			} else {
				retrybadblk = static_cast<size_t>(lv);
				fprintf(stderr,
					"using DDD_RETRYBLOCKS %zu\n",
					retrybadblk);
			}
		}
	}

	int out, inp = open(inname.c_str(), O_RDONLY);
	if ( inp < 0 ) {
		perror(inname.c_str());
		return EXIT_FAILURE;
	}
	if ( dryrun || argc == 2 ) {
		out = STDOUT_FILENO;
	} else {
		out = open(argv[2], O_TRUNC|O_CREAT|O_WRONLY, 0666);
	}
	if ( out < 0 ) {
		perror(argv[2]);
		close(inp);
		return EXIT_FAILURE;
	}
	if ( verbose && dryrun && argc > 2 ) {
		fprintf(stderr, "in dry run: output %s not opened\n",
			argv[2]);
	}

	// cannot get size from struct stat: get it from ISO 9660 field
	size_t volblks = get_vol_blocks(inp);

	dvd_reader_p drd = DVDOpen(inname.c_str());
	if ( drd == 0 ) {
		fprintf(stderr, "failed opening %s\n", inname.c_str());
		return EXIT_FAILURE;
	}

	file_list filelist;
	list_build(filelist, drd);
	if ( dryrun || verbose >= 1 ) {
		list_print(filelist);
	}

	setnum_list setlist;
	vt_set_map setmap;
	setmap_build(filelist, setlist, setmap);
	if ( dryrun || verbose >= 2 ) {
		setmap_print(setlist, setmap);
	}

	off_t wrbl;
	if ( dryrun || verbose >= 3 ) {
		wrbl = dd_ops_print(setlist, setmap, volblks);
		if ( wrbl != volblks ) {
			fprintf(stderr,
			    "FAIL: %llu written; expected %zu\n",
				(unsigned long long)(wrbl * blk_sz),
				volblks * blk_sz);
			return EXIT_FAILURE;
		}
	}

	if ( !dryrun ) {
		wrbl =
		  dd_ops_exec(setlist, setmap, volblks, drd, inp, out);
		if ( wrbl != volblks ) {
			fprintf(stderr,
			    "FAIL: %llu written; expected %zu\n",
				(unsigned long long)(wrbl * blk_sz),
				volblks * blk_sz);
			return EXIT_FAILURE;
		}
	}

	if ( numbadblk ) {
		fprintf(stderr,
		    "found %zu bad blocks in %s; zeroed in output\n",
		    numbadblk,
		    inname.c_str());
	}

	DVDClose(drd);
	close(inp);
	if ( close(out) ) {
		perror("close output");
		return EXIT_FAILURE;
	}

	return EXIT_SUCCESS;
}

