/*
   dd-dvd.cc -- backup to disk a video DVD image

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
#include <sstream>
#include <vector>
#include <list>
#include <map>
#include <algorithm>
#include <functional>
#include <utility>
#include <stdexcept>
#include <climits>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <cerrno>
#include <cstddef>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>

extern "C" {
#    include "hdr_cfg.h"
}
#include "lib_misc.h"
#include "dl_drd.h"
#include "vd_cpf.h"

#if HAVE_GETOPT_H
#    include <getopt.h>
#else
#    include "gngetopt.h"
#endif

#ifndef STDOUT_FILENO
#   define STDOUT_FILENO 1
#endif

#ifndef EXIT_SUCCESS
#define EXIT_SUCCESS 0
#endif
#ifndef EXIT_FAILURE
#define EXIT_FAILURE 1
#endif

/* by default, eliminate C++98 throw() specs --
 * they're deprecated in C++11 -- if wanted, then
 * #define _THROW(x) throw(x)
 */
#ifndef _THROW
#define _THROW(x)
#endif

/* PACKAGE_VERSION is an autoconf macro */
const char version[] = PACKAGE_VERSION;

/* NOTE: the ridiculous (char*) casts are to quieten
 * the compiler on Sun/Oracle (OpenIndiana) because
 * broken headers have omitted 'const' in the struct option definition.
 */
#if defined(__sun)
#define CPCAST (char*)
#else
#define CPCAST
#endif
static struct option const long_options[] =
{
    {CPCAST "quiet", no_argument, 0, 'q'},
    {CPCAST "silent", no_argument, 0, 'q'},
    {CPCAST "verbose", no_argument, 0, 'v'},
    {CPCAST "dry-run", no_argument, 0, 'n'},
    {CPCAST "block-read-count", required_argument, 0, 'b'},
    {CPCAST "retry-block-count", required_argument, 0, 'r'},
#if ! HAVE_LIBDVDREAD
    {CPCAST "libdvdr", required_argument, 0, 'L'},
#endif
    {CPCAST "help", no_argument, 0, 'h'},
    {CPCAST "version", no_argument, 0, 'V'},
    {NULL, 0, NULL, 0}
};
#undef CPCAST

const char default_program_name[] = "dd-dvd";
extern "C" { const char* program_name = default_program_name; }

using namespace std;
using namespace rel_ops;

string inname;   // name of input
string outname;  // name of output

template <class T> class auto_array {
    T* p;
public:
    auto_array(T* parray = 0) : p(parray) {}
    auto_array(size_t sz) : p(new T[sz]) {}
    ~auto_array() { delete[] p; }
    T* getp() { return p; }
    const T* getp() const { return p; }
    operator T* () { return p; }
    operator const T* () const { return p; }
};

const size_t blk_sz = drd_VIDEO_LB_LEN; // this is 2048

const size_t def_block_read_count = 4096;
const size_t max_block_read_count = 4096 * 8;
size_t block_read_count = def_block_read_count;

typedef drd_reader_t* dvd_reader_p;

const char* drd_libname = 0;

size_t numbadblk = 0;

const size_t def_retrybadblk = 48; // was 2, which can be abusive
size_t retrybadblk = def_retrybadblk;
int verbose = 0;
bool dryrun = false;
bool bequiet = false;
unsigned char* iobuffer;
// for front end programs
bool io_linebuf = false;

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

size_t
page_size()
{
    static int s = 0;

    if ( s == 0 ) {
        s = get_page_size();

        if ( s <= 0 ) {
            s = 8192;
            pfeall(_("%s: warning, could not find page size, using %d\n"),
                program_name, s);
        }
    }

    return size_t(s);
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
     : block(blk), size(sz), nset(setn)
     , nfile(filen), type(typ), name(nm)
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

    void addfile(const vt_file& fil) _THROW(invalid_argument)
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

    vt_file& operator [](int ix) _THROW(invalid_argument)
    {
        if ( ix < 0 || size_t(ix) >= count() ) {
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

    const vt_file& operator [](int ix) const _THROW(invalid_argument)
    {
        if ( ix < 0 || size_t(ix) >= count() ) {
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
            pfeopt("%s%s %u: %s\n",
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
    pfeopt("\nVideo file groups:\n");

    vt_set_map::const_iterator es = smap.end();
    for ( size_t n = 0; n < slst.size(); n++ ) {
        vtf_set_index ix(slst[n]);

        pfeopt("  VT set %02u (%s) containing:\n",
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

inline void
list_sort(file_list& lst)
{
    lst.sort();
}

void
list_print(file_list& lst)
{
    eoputs(
        "The following VTS files have been found:\n"
        "####       block        size                    name\n"
        "====================================================\n");

    file_list::iterator i = lst.begin();
    file_list::iterator e = lst.end();

    for ( unsigned n = 0; i != e; i++, n++ ) {
        pfeopt("%03u)  %10llu  %10llu  %s\n"
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

// Just go through collected data and print, showing ops
// to be done, but do nothing else -- same function signature
// as dd_ops_exec() so that a selected call can be made
off_t
dd_ops_print(const setnum_list& slst, const vt_set_map& smap, size_t tot_blks)
{
    pfeopt("\nDD operations on %llu blocks:\n", CAST_ULL(tot_blks));

    off_t fptr = 0;

    for ( unsigned n = 0; n < slst.size(); n++ ) {
        vtf_set_index ix(slst[n]);
        const vtf_set& vs = smap.find(ix)->second;

        pfeopt("file group %02u:%s, %llu files:\n",
            vs.nset, vtfext[vs.type], CAST_ULL(vs.count()));

        for ( size_t nvf = 0; nvf < vs.count(); nvf++ ) {
            const vt_file& vf = vs[nvf];

            // basic error checks
            if ( off_t(vf.block) < fptr ) {
                pfeall(
                    "internal error: wanted block %llu"
                    ", had %llu (new offset < current)\n",
                    (unsigned long long)fptr,
                    (unsigned long long)vf.block);
                exit(EXIT_FAILURE);
            }
            if ( vf.size % blk_sz ) {
                pfeall(
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
                pfeopt(
                    "DD at %llu to %llu:"
                    " %llu blocks, %llu bytes\n",
                    (unsigned long long)fptr,
                    (unsigned long long)fptr + ddbsz,
                    CAST_ULL(ddbsz),
                    CAST_ULL(ddbsz) * blk_sz);
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
            pfeopt(
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
        pfeopt(
            "DD remainder at %llu to %llu: %llu blocks, %llu bytes\n",
            (unsigned long long)fptr,
            (unsigned long long)fptr + ddbsz,
            CAST_ULL(ddbsz),
            CAST_ULL(ddbsz) * blk_sz);
        fptr += off_t(ddbsz);
    }

    if ( size_t(fptr) > tot_blks ) {
        pfeall(
            "ERROR: write offset > total blocks: %llu > %llu\n",
            (unsigned long long)fptr, CAST_ULL(tot_blks));
        exit(EXIT_FAILURE);
    }

    pfeopt("DD operations: %llu blocks, %llu bytes to write\n",
        (unsigned long long)fptr,
        (unsigned long long)fptr * blk_sz);

    return fptr;
}

// Go through collected data and executes operations they require
off_t
dd_ops_exec(
    const setnum_list& slst,
    const vt_set_map& smap,
    size_t tot_blks,
    dvd_reader_p dvd, int inp, int out
    )
{
    pfeopt("\nDD of %llu block filesystem:\n", CAST_ULL(tot_blks));

    off_t fptr = 0;

    vd_rw_proc_args pargs;
    auto_array<char> inpnm(inname.length() + 1);
    auto_array<char> outnm(outname.length() + 1);

    strlcpy(inpnm, inname.c_str(), inname.length() + 1);
    strlcpy(outnm, outname.c_str(), outname.length() + 1);

    pargs.vd_out          = out        ;
    pargs.vd_program_name = program_name;
    pargs.vd_inp_fname    = inpnm;
    pargs.vd_out_fname    = outnm;
    pargs.vd_blknrd       = block_read_count;
    pargs.vd_blk_sz       = blk_sz     ;
    pargs.vd_retrybadblk  = retrybadblk;
    pargs.vd_numbadblk    = &numbadblk ;
    pargs.vd_buf          = iobuffer;

    for ( unsigned n = 0; n < slst.size(); n++ ) {
        vtf_set_index ix(slst[n]);
        const vtf_set& vs = smap.find(ix)->second;

        pfeopt("file group %02u:%s, %llu files:\n",
            vs.nset, vtfext[vs.type], CAST_ULL(vs.count()));

        int setoff = 0;
        for ( size_t nvf = 0; nvf < vs.count(); nvf++ ) {
            const vt_file& vf = vs[nvf];

            // basic error checks
            if ( off_t(vf.block) < fptr ) {
                pfeall(
                    "internal error: wanted block %llu"
                    ", had %llu (new offset < current)\n",
                    (unsigned long long)fptr,
                    (unsigned long long)vf.block);
                exit(EXIT_FAILURE);
            }
            if ( vf.size % blk_sz ) {
                pfeall(
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
                pfeopt(
                    "DD at %llu to %llu:"
                    " %llu blocks, %llu bytes\n",
                    (unsigned long long)fptr,
                    (unsigned long long)fptr + ddbsz,
                    CAST_ULL(ddbsz),
                    CAST_ULL(ddbsz) * blk_sz);

                off_t pos = fptr * blk_sz;
                off_t ret = lseek(inp, pos, SEEK_SET);
                if ( ret != pos ) {
                    pfeall(
                        "failed input seek to %llu\n",
                        (unsigned long long)pos);
                    exit(EXIT_FAILURE);
                }

                pargs.vd_dvdfile      = 0;
                pargs.vd_inp          = inp;
                pargs.vd_blkcnt       = ddbsz;
                pargs.vd_poff         = 0;

                ret = vd_rw_vob_blks(&pargs);

                if ( size_t(ret) != ddbsz ) {
                    pfeall(_("%s: read failed at block %llu, %llu\n"),
                        program_name,
                        (unsigned long long)fptr, CAST_ULL(ddbsz));
                    exit(EXIT_FAILURE);
                }

                fptr += off_t(ddbsz);
            }

            // copy DVD type data:
            // setup libdvdread 'domain'
            vtf_type ftype = vf.type;
            drd_read_t dom;
            const char* sdom;
            if ( ftype == vtf_vob ) {
                dom =   vf.nfile ?
                    drd_READ_TITLE_VOBS :
                    drd_READ_MENU_VOBS;
                sdom =   vf.nfile ?
                    "DVD_READ_TITLE_VOBS" :
                    "DVD_READ_MENU_VOBS";
            } else if ( ftype == vtf_ifo ) {
                dom = drd_READ_INFO_FILE;
                sdom = "DVD_READ_INFO_FILE";
            } else {
                dom = drd_READ_INFO_BACKUP_FILE;
                sdom = "DVD_READ_INFO_BACKUP_FILE";
            }

            // copy DVD type data:
            // open libdvdread 'domain'
            drd_file_t* df = DVDOpenFile(dvd, int(vf.nset), dom);
            if ( df == 0 ) {
                pfeall(
                    "failed to open title %u at block %llu\n",
                    vf.nset,
                    (unsigned long long)vf.block);
                exit(EXIT_FAILURE);
            }

            // copy DVD type data:
            // use libdvdread API per file type with
            // vd_rw_vob_blks() or vd_rw_ifo_blks()
            size_t szr;
            size_t rsz = vf.size / blk_sz;
            pfeopt(
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
            pargs.vd_dvdfile      = df;
            pargs.vd_inp          = -1;
            pargs.vd_blkcnt       = rsz;
            pargs.vd_poff         =
                vf.nfile > 0 && ftype == vtf_vob
                ? &setoff : &t;

            szr = ftype == vtf_vob
                ? vd_rw_vob_blks(&pargs)
                : vd_rw_ifo_blks(&pargs);

            // copy DVD type data:
            // error check
            if ( szr != rsz ) {
                pfeall(
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
        pfeopt(
            "DD remainder at %llu to %llu: %llu blocks, %llu bytes\n",
            (unsigned long long)fptr,
            (unsigned long long)fptr + ddbsz,
            CAST_ULL(ddbsz),
            CAST_ULL(ddbsz) * blk_sz);

        off_t pos = fptr * blk_sz;
        off_t ret = lseek(inp, pos, SEEK_SET);
        if ( ret != pos ) {
            pfeall(
                "failed input seek to %llu\n",
                (unsigned long long)pos);
            exit(EXIT_FAILURE);
        }

        pargs.vd_dvdfile      = 0;
        pargs.vd_inp          = inp;
        pargs.vd_blkcnt       = ddbsz;
        pargs.vd_poff         = 0;

        ret = vd_rw_vob_blks(&pargs);

        if ( size_t(ret) != ddbsz ) {
            pfeall("DD failed at block %llu, %llu\n",
                (unsigned long long)fptr, CAST_ULL(ddbsz));
            exit(EXIT_FAILURE);
        }

        fptr += off_t(ddbsz);
    }

    if ( size_t(fptr) > tot_blks ) {
        pfeall("ERROR: write offset > total blocks: %llu > %llu\n",
            (unsigned long long)fptr, CAST_ULL(tot_blks));
        exit(EXIT_FAILURE);
    }

    pfeopt("DONE: %llu blocks, %llu bytes written\n",
        (unsigned long long)fptr,
        (unsigned long long)fptr * blk_sz);

    return fptr;
}

// helper to get certain size fields that are stored
// as both little and big endian, one after the other
template<typename D, typename P> bool
get_lbe_val(D& result, const P* pfields)
{
    const size_t tsz = sizeof(D);
    const P* ple = pfields;
    const P* pbe = pfields + tsz;

    D le = 0;
    D be = 0;

    for ( size_t i = 0; i < tsz; ++i ) {
        size_t shle = i * 8;
        size_t shbe = (tsz - (i + 1)) * 8;

        le |= D(ple[i]) <<  shle;
        be |= D(pbe[i]) <<  shbe;
    }

    // sanity check:
    if ( be != le ) {
        pfeopt("failed to get little&big end field (le %lu, be %lu)\n",
            (unsigned long)le, (unsigned long)be);
        return false;
    }

    result = be;

    return true;
}

// helper for --dry-run info output
string&
rtrim(string& s, const char* not_of = " \a\b\t\f\v\n\r")
{
    string::size_type pos = s.find_last_not_of(not_of);

    if ( pos == string::npos ) {
        s = "";
        return s;
    }

    s.erase(pos + 1);

    return s;
}

// helper for --dry-run info output
string&
ltrim(string& s, const char* not_of = " \a\b\t\f\v\n\r")
{
    string::size_type pos = s.find_first_not_of(not_of);

    if ( pos == string::npos ) {
        s = "";
        return s;
    }

    s.erase(0, pos);

    return s;
}

// helper for --dry-run info output
inline string&
ends_trim(string& s, const char* not_of = " \a\b\t\f\v\n\r")
{
    return ltrim(rtrim(s, not_of), not_of);
}

// helper for --dry-run info output
// called by get_vol_blocks:
// buf is 2048 bytes that was read from offset 2048*16
//   on iso9660, and which contains the info to print,
// blocks is fs block count already calc'd in get_vol_blocks
void
print_volume_info(char* buf, size_t blocks = 0)
{
    static const struct {
        bool              bdate; // flag date fields: special
        size_t            off;
        string::size_type len;
        const char*       label;
    } dat[] = {
        {false, 8,    32, "system_id"},
        {false, 40,   32, "volume_id"},
        {false, 190, 128, "volume_set_id"},
        {false, 318, 128, "publisher_id"},
        {false, 446, 128, "data_preparer_id"},
        {false, 574, 128, "application_id"},
        {false, 702,  37, "copyright_id"},
        {false, 739,  37, "abstract_file_id"},
        {false, 776,  37, "bibliographical_id"},
        {true,  813,  17, "volume_creation_date"},
        {true,  830,  17, "last_modified_date"},
        {true,  847,  17, "expiry_date"},
        {true,  864,  17, "effective_date"}
    };

    for ( size_t i = 0; i < A_SIZE(dat); ++i ) {
        char* pcur = buf + dat[i].off;

        // slight complication in date fields: last char is
        // actually an 8-bit signed integer offset from GMT
        // in 15 minute units, negative west, else east
        string gmo("");

        if ( dat[i].bdate ) {
            size_t idx = dat[i].len - 1;
            int v = ((signed char*)pcur)[idx];

            pcur[idx] = '\0';

            if ( string(pcur).find_first_not_of("0") != string::npos ) {
                pcur[idx] = ' ';

                ostringstream ost;

                ost << " - GMT offset "
                    << (std::abs(v) * 15) << " minutes"
                    << (v == 0 ? "" : (v < 0 ? " west" : " east"));

                gmo = ost.str();
            } else {
                std::memset(pcur, ' ', dat[i].len);
            }
        }

        string s(pcur, dat[i].len);
        pfoopt("%s|%s\n", dat[i].label, (ends_trim(s) + gmo).c_str());
    }

    // print volume size in blocks
    if ( blocks == 0 ) {
        uint32_t fsblocks;
        // use unsigned char* because there is already an
        // instantiation of get_lbe_val template for that
        unsigned char* tbuf = (unsigned char*)buf;
        if ( get_lbe_val(fsblocks, tbuf + 80) ) {
            blocks = size_t(fsblocks);
        } else {
            // Note not stderr: if front end is using this,
            // it may detect 'FAILED'
            pfoopt("%s|FAILED\n", "filesystem_block_count");
            return;
        }
    }

    pfoopt("%s|%llu\n", "filesystem_block_count", CAST_ULL(blocks));
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

    // offset into iso 9660 fs for big,little endian fs size
    const size_t loff = 80;
    uint32_t fsblocks;
    if ( get_lbe_val(fsblocks, iobuffer + loff) == false ) {
        pfeall("%s: failed to get volume block count\n", program_name);
        exit(EXIT_FAILURE);
    }

    // dryrun: DVD files info is printed on stderr, and stdout
    // is not otherwise used -- as of 0.2.1 print other useful
    // info on stdout
    if ( dryrun ) {
        print_volume_info((char*)iobuffer);
    }

    ocur = lseek(fd, ocur, SEEK_SET);
    if ( ocur < 0 ) {
        perror("lseek(SEEK_SET)");
        // no fail return: exit
        exit(EXIT_FAILURE);
    }

    return size_t(fsblocks);
}

bool
get_mount_dev(const char* mtpt, string& name)
{
    int bufsize = get_max_path(); // from lib misc

    if ( bufsize <= 0 ) {
        pfeall("cannot get fs path maximum for %s\n", mtpt);
        return false;
    }

    size_t sz = static_cast<size_t>(bufsize);
    auto_array<char> buf(sz);

    errno = 0;
    if ( get_mnt_dev(mtpt, buf, sz) ) {
        if ( errno ) {
            pfeall("cannot find device for %s -- %s\n",
                mtpt, strerror(errno));
        } else {
            pfeall("cannot find device for %s\n", mtpt);
        }

        return false;
    }

    pfeall("using device %s for argument %s\n", buf.getp(), mtpt);

    // dryrun: DVD files info is printed on stderr, and stdout
    // is not otherwise used -- as of 0.2.1 print other useful
    // info on stdout
    if ( dryrun ) {
        pfoopt("input_arg|%s|%s\n", mtpt, buf.getp());
    }

    name = buf;
    return true;
}

void
env_checkvars()
{
    const char* ep;

    if ( (ep = getenv("DDD_DRYRUN")) != 0 ) {
        if ( strcasecmp(ep, "0") &&
             strcasecmp(ep, "no") &&
             strcasecmp(ep, "false") ) {
            dryrun = true;
        }
    }

    if ( (ep = getenv("DDD_LINEBUF")) != 0 ) {
        if ( strcasecmp(ep, "1") == 0 ||
             strcasecmp(ep, "yes") == 0 ||
             strcasecmp(ep, "true") == 0 ) {
            io_linebuf = true;
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

        if ( errno || lv < 1 || size_t(lv) > def_block_read_count ) {
            perror("bad \"DDD_RETRYBLOCKS\" value");
        } else {
            retrybadblk = static_cast<size_t>(lv);
            fprintf(stderr, "found DDD_RETRYBLOCKS=%llu\n",
                CAST_ULL(retrybadblk));
        }
    }
}

string
check_node(string nname)
{
#    if defined(__OpenBSD__) || defined(__NetBSD__)
    string::size_type pos = nname.rfind('/');
    if ( pos == string::npos ) {
        return nname;
    }
    if ( ++pos >= nname.length() ) {
        return nname;
    }
    if ( nname[pos] != 'r' ) {
        nname.insert(pos, "r");
    }
#    endif
    return nname;
}

/**
 ** options section
 */
static void
usage(int status)
{
      fprintf(stderr, _("%s - \
A simple utility to make a backup copy of a DVD filesystem.\n"), program_name);
      fprintf(stderr, _("Usage: %s [OPTIONS] SOURCE(device node) [TARGET]\n"), program_name);

      fprintf(stderr, _("\
Options:\n\
  -n, --dry-run              take no real actions\n\
  -q, --quiet, --silent      inhibit usual output\n\
  -v, --verbose              print information; repeat -v for yet more\n\
  -b, --block-read-count     2048 byte blocks per read operation\n\
                             (default %llu, maximum %llu)\n\
  -r. --retry-block-count    blocks per retry on IO errors\n\
                             (default %llu, 0 disables retrying)\n\
  %s-h, --help                 display this help and exit\n\
  -V, --version              output version information and exit\n\
%s"),
CAST_ULL(def_block_read_count),
CAST_ULL(max_block_read_count),
CAST_ULL(def_retrybadblk),
#if ! HAVE_LIBDVDREAD
_("-L, --libdvdr NAME         use NAME as dvdread library\n  "),
#else
"",
#endif
"\n  On some systems a mount point directory may be given for\n\
  the SOURCE argument if the medium is mounted.\n\n\
  The TARGET argument is optional: standard output is default.\n\n"
);

      exit(status);
}

/* Set all the option flags according to the switches specified.
 * Return the index of the first non-option argument.
 */
static int
get_options(int argc, char* argv[])
{
    int c;

    while ( (c = getopt_long(argc, argv,
               "n"    /* dry-run */
               "q"    /* quiet or silent */
               "v"    /* verbose */
               "b:"    /* read count */
               "r:"    /* retry count */
#if ! HAVE_LIBDVDREAD
               "L:"    /* libdvdr */
#endif
               "h"    /* help */
               "V",    /* version */
               long_options, (int*)0)) != EOF )
    {
        switch (c)
        {
            case 'n':        /* --dry-run */
                dryrun = true;
                break;
            case 'q':        /* --quiet, --silent */
                verbose = 0;
                bequiet = true;
                break;
            case 'v':        /* --verbose */
                bequiet = false;
                verbose += 1;
                break;
            case 'b':        /* --block-read-count */
                istringstream(optarg) >> block_read_count;
                break;
            case 'r':        /* --retry-block-count */
                istringstream(optarg) >> retrybadblk;
                break;
#if ! HAVE_LIBDVDREAD
            case 'L':        /* --libdvdr */
                drd_libname = optarg;
                break;
#endif
            case 'V':
                fprintf(stderr, "%s (%s) %s\n",
                    program_name, default_program_name, version);
                exit(EXIT_SUCCESS);
            case 'h':
                usage(EXIT_SUCCESS);
            default:
                usage(EXIT_FAILURE);
        }
    }

    return optind;
}

inline void
set_program_name(const char* p)
{
    if ( ! p || ! *p ) {
        return;
    }
    const char* q = strrchr(p, '/');
    program_name = (q && *++q) ? q : p;
}

int
main(int argc, char* argv[])
{
    set_program_name(argv[0]);

    /* get envireonment vars 1st so options override */
    env_checkvars();

    /* not a commandline opt, but may be set from env */
    if ( io_linebuf ) {
        /* NOTE setlinebuf() is not in C++ std:: */
        setlinebuf(stdout);
        setlinebuf(stderr);
    }

    /* options handling */
    int nopt = get_options(argc, argv);
    if ( argv[nopt] == 0 ) {
        usage(EXIT_FAILURE);
    }

    inname  = argv[nopt++];
    outname = argv[nopt] == 0 ? "" : argv[nopt++];

    if ( argv[nopt] != 0 ) {
        usage(EXIT_FAILURE);
    }

    /* setup stream helpers */
    // NO stdout messages! data goes there
    // (unless dryrun in effect)
    if ( bequiet ) {
        FILE* tf = fopen("/dev/null", "w");
        pf_assign_files(tf, tf);
    } else {
        if ( dryrun ) {
            pf_assign_files(stdout, stderr);
        } else {
            pf_assign_files(stderr, stderr);
        }
    }

    // NO stdout messages (unless dryrun)! data goes there
    if ( dryrun ) {
        pf_setup(1, verbose >= 1);
    } else {
        pf_setup(0, verbose >= 1);
    }

    // flag some verbosity optional in vd_cpf.c
    vd_cpf_verbose = verbose;

    // check for reasonable count args
    if ( block_read_count > max_block_read_count ) {
        // set to def rather than max assuming arg was monstrous error
        block_read_count = def_block_read_count;
        pfeall(_("%s: block read count too great, using %llu\n"),
            program_name, CAST_ULL(block_read_count));
    }
    if ( block_read_count == 0 ) {
        block_read_count = def_block_read_count;
        pfeall(_("%s: block read count was 0, using %llu\n"),
            program_name, CAST_ULL(block_read_count));
    }
    if ( retrybadblk >= block_read_count ) {
        retrybadblk = (block_read_count + 1) >> 1;
        pfeall(_("%s: retry block count too great, using %llu\n"),
            program_name, CAST_ULL(retrybadblk));
    }
    if ( verbose >= 3 ) {
        pfeall(_("%s: using block read count %llu\n"),
            program_name, CAST_ULL(block_read_count));
        pfeall(_("%s: using retry block count %llu\n"),
            program_name, CAST_ULL(retrybadblk));
    }

#if ! HAVE_LIBDVDREAD
    if ( drd_libname == 0 ) {
        drd_libname = drd_altname;
    }
    if ( open_drd(drd_libname, get_drd_defflags()) ) {
        pfeall(_("%s: failed loading %s (LD_LIBRARY_PATH?)\n"),
            program_name, drd_libname);
        return EXIT_FAILURE;
    }

    pfeopt(_("%s: using %s for dvdread library\n"),
        program_name, drd_libname);

    if ( int nf = load_drd_syms() ) {
        pfeall(_("%s: failed loading %d symbols from %s\n"),
            program_name, nf, drd_libname);
        return EXIT_FAILURE;
    }

    if ( DVDVersion == NULL ) {
        if ( verbose > 2 ) {
            pfeopt(_("%s: dvdread library %s has no DVDVersion()\n"),
                program_name, drd_libname);
        }
    } else {
        int v = DVDVersion();
        pfeopt(_("%s: %s version %d.%d.%d found\n"),
            program_name, drd_libname,
            (v / 10000) % 100,
            (v / 100) % 100,
            v % 100);
    }
#endif

    struct stat sb;
    if ( stat(inname.c_str(), &sb) ) {
        perror(inname.c_str());
        return EXIT_FAILURE;
    }

    // this prog is not for directories, but see if
    // dir is a mount anf get the device if so
    if ( S_ISDIR(sb.st_mode) ) {
        string tname(inname);
        // was the name a symlink?
        if ( ! lstat(inname.c_str(), &sb) && S_ISLNK(sb.st_mode) ) {
            const size_t sz = PATH_MAX + 1;
            auto_array<char> buf(sz);
            ssize_t len = readlink(inname.c_str(), buf, sz - 1);
            if ( len > 0 ) {
                ((char*)buf)[len] = '\0';
                tname = (char*)buf;
                pfeopt("found %s is a symlink to %s\n",
                    inname.c_str(), tname.c_str());
            }
        }
        if ( get_mount_dev(string(tname).c_str(), tname) == false ) {
            pfeall("if %s is the mount point"
                " of a DVD device, give device name"
                " instead\n", inname.c_str());
            return EXIT_FAILURE;
        }
        // accept name change and recheck
        inname = tname;
        if ( stat(inname.c_str(), &sb) ) {
            perror(inname.c_str());
            return EXIT_FAILURE;
        }
    }

    // allowing character dev or block; e.g. on OBSD if
    // fs is mounted, opening block gets EBUSY, but opening
    // char succeeds -- either will do for this code
    if ( S_ISCHR(sb.st_mode) || S_ISBLK(sb.st_mode) ) {
        string tname = check_node(inname);
        if ( tname != inname ) {
            struct stat t;
            if ( ! stat(tname.c_str(), &t) &&
                (S_ISCHR(t.st_mode) || S_ISBLK(t.st_mode)) ) {
                pfeopt("using %s rather than %s\n",
                    tname.c_str(), inname.c_str());
                inname = tname;
                sb = t; // compiler copy
            }
        }
    } else if ( ! S_ISREG(sb.st_mode) ) {
        pfeall("unsupported file type %s\n", inname.c_str());
        return EXIT_FAILURE;
    }

    int out, inp = open(inname.c_str(), O_RDONLY);
    if ( inp < 0 ) {
        perror(inname.c_str());
        return EXIT_FAILURE;
    }

    if ( dryrun || outname == "" ) {
        out = STDOUT_FILENO;
        if ( outname == "" ) {
            outname = "<standard output>";
        }
    } else {
        out = open(outname.c_str(), O_TRUNC|O_CREAT|O_WRONLY, 0666);
    }
    if ( out < 0 ) {
        perror(outname.c_str());
        close(inp);
        return EXIT_FAILURE;
    }
    if ( verbose && dryrun && argc > 2 ) {
        pfeall("in dry run: output %s not used\n",
            outname.c_str());
    }

    auto_array<unsigned char> buffalloc(
        block_read_count * blk_sz + page_size()
        );
    iobuffer = mk_aligned_ptr(buffalloc, page_size());

    // cannot get size from struct stat: get it from ISO 9660 field
    size_t volblks = get_vol_blocks(inp);

    dvd_reader_p drd = DVDOpen(inname.c_str());
    if ( drd == 0 ) {
        pfeall("failed opening %s\n", inname.c_str());
        return EXIT_FAILURE;
    }

    file_list filelist;
    list_build(filelist, drd);
    if ( dryrun || verbose >= 2 ) {
        list_print(filelist);
    }

    setnum_list setlist;
    vt_set_map setmap;
    setmap_build(filelist, setlist, setmap);
    if ( dryrun || verbose >= 3 ) {
        setmap_print(setlist, setmap);
    }

    off_t wrbl;
    if ( dryrun || verbose >= 3 ) {
        wrbl = dd_ops_print(setlist, setmap, volblks);
        if ( size_t(wrbl) != volblks ) {
            pfeall("FAIL: %llu written; expected %llu\n",
                CAST_ULL(wrbl) * blk_sz, CAST_ULL(volblks) * blk_sz);
            return EXIT_FAILURE;
        }
    }

    if ( !dryrun ) {
        wrbl =
          dd_ops_exec(setlist, setmap, volblks, drd, inp, out);
        if ( size_t(wrbl) != volblks ) {
            pfeall("FAIL: %llu written; expected %llu\n",
                CAST_ULL(wrbl) * blk_sz, CAST_ULL(volblks) * blk_sz);
            return EXIT_FAILURE;
        }
    }

    if ( numbadblk || verbose > 1 ) {
        pfeall(
            "found %llu total bad blocks in %s%s\n",
            CAST_ULL(numbadblk), inname.c_str(),
            numbadblk ? "; bad blocks are zeroed in output" : "");
    }

    DVDClose(drd);
    close(inp);
    if ( dryrun == false && close(out) ) {
        perror("closing output");
        return EXIT_FAILURE;
    }

    return EXIT_SUCCESS;
}

