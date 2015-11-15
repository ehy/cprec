/*
 * vd_cpf.[hc] - video data copy functions
 *
 * Copyright (C) 2015 Ed Hynan
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
 * MA 02110-1301, USA.
 */


#include "hdr_cfg.h"
#include "lib_misc.h"
#include "vd_cpf.h"

/*
static procedures to wrap the read procedures used herein

procedures operate in bytes for uniformity; DVDReadBlocks()
will divide by block size
*/

/* struct for arguments to static procedures */
struct vdstatic_data {
    vd_rw_proc_args*    pargs; /* data described in header */
    unsigned char*      buf;   /* buffer for cnt bytes */
    size_t              cnt;   /* read count */
};

/*
 * name: reader_fdread -- reader for 'low level' read(2)
 *
 * name: reader_dvdbytes -- reader for libdvdread DVDReadBytes()
 *
 * name: reader_dvdblocks -- reader for libdvdread DVDReadBlocks()
 *
 * @param pargs -- structure with with general parameters
 * @param cnt -- number of bytes to read in this call
 * @return number of blocks read
 */
/* reader for 'low level' read(2) syscall on file descriptor */
static ssize_t
reader_fdread(struct vdstatic_data* data);
/* reader for libdvdread DVDReadBytes() */
static ssize_t
reader_dvdbytes(struct vdstatic_data* data);
/* reader for libdvdread DVDReadBlocks() */
static ssize_t
reader_dvdblocks(struct vdstatic_data* data);

/* a type for reader procedures: */
typedef ssize_t (*dv_read_proc)(struct vdstatic_data*);

/* internal loop receives pointer to read proc. */
static ssize_t
vd_rw_in_out(vd_rw_proc_args* pargs, dv_read_proc rproc);
/* internal loop receives pointer to read proc.; for error retries */
static ssize_t
vd_rw_in_out_retry(vd_rw_proc_args* pargs, dv_read_proc rproc);

/*
implementations of procedures with external linkage
*/

/* copy IFO of BUP with DVDReadBytes() */
ssize_t
vd_rw_ifo_blks(vd_rw_proc_args* pargs)
{
    return vd_rw_in_out(pargs, reader_dvdbytes);
}

ssize_t
vd_rw_vob_blks(vd_rw_proc_args* pargs)
{
    return vd_rw_in_out(pargs, pargs->vd_poff == NULL
        ? reader_fdread : reader_dvdblocks);
}

/*
 *  call when read fails with io error; assume optical medium fault.
 *  zero the destination buffer and try reading one block at a time.
 *  if read fails w/ EIO advanvce one block (writing zeroes).
 *  return -1 for errors other than EIO.
 */
ssize_t
vd_rw_vob_badblks(vd_rw_proc_args* pargs)
{
    return vd_rw_in_out_retry(pargs, pargs->vd_poff == NULL
        ? reader_fdread : reader_dvdblocks);
}


/*
implementations of procedures with static linkage
*/

/* internal loop receives pointer to read proc. */
static ssize_t
vd_rw_in_out(vd_rw_proc_args* pargs, dv_read_proc rproc)
{
    /* break out all struct members: optimizing compiler should
     * dispose of unused automatics
     */
    drd_file_t*     dvdfile     = pargs->vd_dvdfile;
    int             inp         = pargs->vd_inp;
    int             out         = pargs->vd_out;
    const char*     progname    = pargs->vd_program_name;
    const char*     inp_fname   = pargs->vd_inp_fname;
    const char*     out_fname   = pargs->vd_out_fname;
    size_t          blkcnt      = pargs->vd_blkcnt;
    size_t          blknrd      = pargs->vd_blknrd;
    size_t          blk_sz      = pargs->vd_blk_sz;
    size_t          blknretry   = pargs->vd_retrybadblk;
    size_t*         numbadblk   = pargs->vd_numbadblk;
    int*            poff        = pargs->vd_poff;
    unsigned char*  buf         = pargs->vd_buf;

    struct vdstatic_data data;


    size_t cnt = blkcnt * blk_sz;
    size_t nrd = blknrd * blk_sz;

    data.pargs = pargs;

    if ( inp_fname == NULL || *inp_fname == '\0' ) {
        inp_fname = _("input data");
    }

    if ( out_fname == NULL || *out_fname == '\0' ) {
        out_fname = _("output data");
    }

    while ( cnt ) {
        size_t  nbr;
        ssize_t nb;

        nbr = MIN(cnt, nrd);
        data.buf = buf;
        data.cnt = nbr;

        errno = 0;

        nb  = rproc(&data);

        if ( nb < 0 || (nb == 0 && errno != 0) ) {
            /* retry is disable when blknretry == 0 */
            if ( blknretry < 1 ) {
                pfeopt(_("%s: retry bad block == %zu, failing\n"),
                    progname, blknretry);
                return -1;
            }

            pfeopt(_("%s: retry bad block == %zu, retrying\n"),
                progname, blknretry);

            errno = 0;
            /* call desperation procedure:
             * will write NUL data for failed
             * reads on the premise that still
             * a video dvd _might_ remain usable
             */
            pargs->vd_blkcnt = nbr / blk_sz;
            nb = vd_rw_in_out_retry(pargs, rproc);
            pargs->vd_blkcnt = blkcnt;

            if ( nb >= 0 ) {
                cnt -= nb;
                continue;
            }

            pfeall(_("%s: %s has bad blocks, read retry failed '%s'\n"),
                progname, inp_fname, strerror(errno));

            return -1;
        }

        if ( nb > 0 ) {
            if ( poff ) {
                *poff += (int)(nb / blk_sz);
            }

            cnt -= nb;

            if ( write_all(out, buf, nb) != nb ) {
                perror("write DVD data");

            pfeall(_("%s: failed writing to %s -- '%s'\n"),
                progname, out_fname, strerror(errno));

                return -1;
            }
        }
    }

    return blkcnt - cnt / blk_sz;
}

/* internal loop receives pointer to read proc. */
static ssize_t
vd_rw_in_out_retry(vd_rw_proc_args* pargs, dv_read_proc rproc)
{
    drd_file_t*     dvdfile     = pargs->vd_dvdfile;
    int             inp         = pargs->vd_inp;
    int             out         = pargs->vd_out;
    const char*     progname    = pargs->vd_program_name;
    const char*     inp_fname   = pargs->vd_inp_fname;
    const char*     out_fname   = pargs->vd_out_fname;
    size_t          blkcnt      = pargs->vd_blkcnt;
    size_t          blknrd      = pargs->vd_blknrd;
    size_t          blk_sz      = pargs->vd_blk_sz;
    size_t          blknretry   = pargs->vd_retrybadblk;
    size_t*         numbadblk   = pargs->vd_numbadblk;
    int*            poff        = pargs->vd_poff;
    unsigned char*  buf         = pargs->vd_buf;

    time_t tm1, tm2;
    size_t nbr;
    off_t rdp;
    unsigned long good = 0, bad = 0;
    size_t cnt = blkcnt * blk_sz;
    unsigned char* prd = buf;

    struct vdstatic_data data;

    data.pargs = pargs;

    tm1 = time(0);

    if ( inp >= 0 && (rdp = lseek(inp, 0, SEEK_CUR)) < 0 ) {
        int t = errno;
        perror("lseek cur in reading input");
        errno = t;
        return -1;
    }

    nbr = blknretry * blk_sz;

    if ( inp_fname == NULL || *inp_fname == '\0' ) {
        inp_fname = _("input data");
    }

    if ( out_fname == NULL || *out_fname == '\0' ) {
        out_fname = _("output data");
    }

    while ( cnt ) {
        size_t  nbr;
        ssize_t nb;

        nbr = MIN(cnt, nbr);
        data.buf = prd;
        data.cnt = nbr;

        errno = 0;

        nb  = rproc(&data);

        if ( nb == 0 ) {
            break;
        } else if ( nb < 0 ) {
            if ( errno != EIO ) {
                perror(inp_fname);
                return -1;
            }

            memset(prd, 0, nbr);

            nb = nbr;
            bad += nb / blk_sz;
        } else {
            good += nb / blk_sz;
        }

        if ( poff ) {
            *poff += (int)(nb / blk_sz);
        }

        cnt -= nb;
        prd += nb;
        rdp += nb;

        if ( inp >= 0 && lseek(inp, rdp, SEEK_SET) != rdp ) {
            int t = errno;
            perror("lseek set in reading input");
            errno = t;
            return -1;
        }
    }

    cnt = blkcnt * blk_sz - cnt;
    nbr = cnt;

    if ( write_all(out, buf, nbr) != nbr ) {
        perror(out_fname);
        return -1;
    }

    *numbadblk += bad;

    tm2 = time(0);

    pfeall(
    _("%s: %lu bad blocks zeroed in read of %lu in %llu seconds\n"),
        inp_fname, bad, (unsigned long)blkcnt,
        (unsigned long long)tm2 - tm1);


    return cnt / blk_sz;
}

/* reader for 'low level' read(2) syscall on file descriptor */
static ssize_t
reader_fdread(struct vdstatic_data* data)
{
    vd_rw_proc_args* pargs = data->pargs;
    ssize_t ret = read_all(pargs->vd_inp, data->buf, data->cnt);

    if ( ret < 0 ) {
        int e = errno;

        if ( pargs->vd_inp_fname != NULL && *(pargs->vd_inp_fname) ) {
            pfeall(_("%s: error reading '%s' \"%s\"\n"),
                pargs->vd_program_name, pargs->vd_inp_fname,
                strerror(e));
        } else {
            pfeall(_("%s: error reading from input \"%s\"\n"),
                pargs->vd_program_name, strerror(e));
        }

        errno = e;
    }

    return ret;
}

/* reader for libdvdread DVDReadBytes() */
static ssize_t reader_dvdbytes(struct vdstatic_data* data)
{
    vd_rw_proc_args* pargs = data->pargs;
    ssize_t ret = DVDReadBytes(pargs->vd_dvdfile, data->buf, data->cnt);

    if ( ret < 0 ) {
        int e = errno;

        if ( pargs->vd_inp_fname != NULL && *(pargs->vd_inp_fname) ) {
            pfeall(_("%s: DVDReadBytes() error reading '%s' \"%s\"\n"),
                pargs->vd_program_name, pargs->vd_inp_fname,
                strerror(e));
        } else {
            pfeall(_("%s: DVDReadBytes() error reading \"%s\"\n"),
                pargs->vd_program_name, strerror(e));
        }

        errno = e;
    }

    return ret;
}

/* reader for libdvdread DVDReadBlocks() */
static ssize_t reader_dvdblocks(struct vdstatic_data* data)
{
    vd_rw_proc_args* pargs = data->pargs;
    ssize_t ret = DVDReadBlocks(pargs->vd_dvdfile, *(pargs->vd_poff),
        data->cnt / pargs->vd_blk_sz, data->buf);

    if ( ret < 0 ) {
        int e = errno;

        if ( pargs->vd_inp_fname != NULL && *(pargs->vd_inp_fname) ) {
            pfeall(_("%s: DVDReadBlocks() error reading '%s' \"%s\"\n"),
                pargs->vd_program_name, pargs->vd_inp_fname,
                strerror(e));
        } else {
            pfeall(_("%s: DVDReadBlocks() error reading \"%s\"\n"),
                pargs->vd_program_name, strerror(e));
        }

        errno = e;
        return ret;
    }

    return ret * pargs->vd_blk_sz;
}
