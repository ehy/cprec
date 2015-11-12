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

// copy IFO of BUP with DVDReadBytes()
ssize_t
/* copy_ifo(
    drd_file_t* dvdfile,
    int inp, int out,
    unsigned char* buf,
    size_t blkcnt,
    int* poff
*/
vd_rw_ifo_blks(vd_rw_proc_args* pargs)
{
    drd_file_t*     dvdfile     = pargs->vd_dvdfile;
    int             inp         = pargs->vd_inp;
    int             out         = pargs->vd_out;
    const char*     program_name= pargs->vd_program_name;
    const char*     inp_fname   = pargs->vd_inp_fname;
    const char*     out_fname   = pargs->vd_out_fname;
    size_t          blkcnt      = pargs->vd_blkcnt;
    size_t          blknrd      = pargs->vd_blknrd;
    size_t          blk_sz      = pargs->vd_blk_sz;
    size_t          retrybadblk = pargs->vd_retrybadblk;
    size_t*         numbadblk   = pargs->vd_numbadblk;
    int*            poff        = pargs->vd_poff;
    unsigned char*  buf         = pargs->vd_buf;

    unsigned nxrd = 0;
    const unsigned lxrd = 512;
    size_t cnt = blkcnt;

    errno = 0;
    DVDFileSeek(dvdfile, 0);

    while ( cnt ) {
        //ssize_t nb;
        size_t  nbr = MIN(cnt, blknrd);
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
/* copy_vob( */
vd_rw_vob_blks(vd_rw_proc_args* pargs)
{
    drd_file_t*     dvdfile     = pargs->vd_dvdfile;
    int             inp         = pargs->vd_inp;
    int             out         = pargs->vd_out;
    const char*     program_name= pargs->vd_program_name;
    const char*     inp_fname   = pargs->vd_inp_fname;
    const char*     out_fname   = pargs->vd_out_fname;
    size_t          blkcnt      = pargs->vd_blkcnt;
    size_t          blknrd      = pargs->vd_blknrd;
    size_t          blk_sz      = pargs->vd_blk_sz;
    size_t          retrybadblk = pargs->vd_retrybadblk;
    size_t*         numbadblk   = pargs->vd_numbadblk;
    int*            poff        = pargs->vd_poff;
    unsigned char*  buf         = pargs->vd_buf;

    size_t cnt = blkcnt;

    errno = 0;

    while ( cnt ) {
        ssize_t nb;
        size_t  nbr = MIN(cnt, blknrd);

        if ( poff ) {
            nb = DVDReadBlocks(dvdfile, *poff, nbr, buf);
        } else {
            ssize_t ssz = read_all(inp, buf, nbr * blk_sz);
            if ( ssz <= 0 ) {
                nb = ssz;
            } else {
                /* it shouldn't happen: e.g. medium/fs won't
                 * have a size that is not a blocksize multiple,
                 * but have this little code in place anyway:
                 */
                ssize_t rmd = ssz % blk_sz;
                if ( rmd ) {
                    pfeopt(
                        _("%s: WARN: fractional read remainder %zd\n"),
                        program_name, rmd);
                    lseek(inp, 0 - rmd, SEEK_CUR);
                }
                nb = ssz / blk_sz;
            }
        }

        if ( nb <= 0 ) {
            perror("DVD read");

            /* retry is disable when retrybadblk == 0 */
            if ( retrybadblk < 1 ) {
                pfeopt(_("%s: retry bad block == %zu, failing\n"),
                    program_name, retrybadblk);
                return -1;
            }

            pfeopt(_("%s: retry bad block == %zu, retrying\n"),
                program_name, retrybadblk);

            errno = 0;
            /* call desperation procedure:
             * will write NUL data for failed
             * reads on the premise that still
             * a video dvd _might_ remain usable
             */
            pargs->vd_blkcnt = nbr;
            nb = vd_rw_vob_badblks(pargs);

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


/* if poff==0 do fd copy else do vob copy */
/*
 *  call when read fails with io error; assume optical medium fault.
 *  zero the destination buffer and try reading one block at a time.
 *  if read fails w/ EIO advanvce one block (writing zeroes).
 *  return -1 for errors other than EIO.
 */
ssize_t
vd_rw_vob_badblks(vd_rw_proc_args* pargs)
{
    drd_file_t*     dvdfile     = pargs->vd_dvdfile;
    int             inp         = pargs->vd_inp;
    int             out         = pargs->vd_out;
    const char*     program_name= pargs->vd_program_name;
    const char*     inp_fname   = pargs->vd_inp_fname;
    const char*     out_fname   = pargs->vd_out_fname;
    size_t          blkcnt      = pargs->vd_blkcnt;
    size_t          blknrd      = pargs->vd_blknrd;
    size_t          blk_sz      = pargs->vd_blk_sz;
    size_t          retrybadblk = pargs->vd_retrybadblk;
    size_t*         numbadblk   = pargs->vd_numbadblk;
    int*            poff        = pargs->vd_poff;
    unsigned char*  buf         = pargs->vd_buf;

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
            pfeall("FATAL internal error: inp == %d\n",
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

    *numbadblk += bad;
    tm2 = time(0);
    pfeall(
        "%lu bad blocks zeroed in read of %lu in %llu seconds\n",
        bad, (unsigned long)blkcnt,
        (unsigned long long)tm2 - tm1);

    return cnt;
}
