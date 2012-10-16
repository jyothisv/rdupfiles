#!/usr/bin/python

# Copyright 2012 Jyothis Vasudevan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


import os
import hashlib
from math import floor
from random import randint

class FileOrHash:
    def __init__(self, isHash, filename = "", hashsum = {}, rseq = [], fullhash = None):
        self.isHash   = isHash
        self.hashsum  = hashsum
        self.filename = filename
        self.fullhash = fullhash
        self.rseq = rseq

def hashfile(f, byteOffsets=range(1), blockSize=4096):
    dig    = hashlib.sha1()
    # Get access and modification times for restoring later
    atime  = os.path.getatime(f)
    mtime  = os.path.getmtime(f)
    infile = open(f, mode="rb")
    for byte in byteOffsets:
        infile.seek(byte, 0)
        buf = infile.read(blockSize)
        if not buf:
            continue
        dig.update(buf)
    infile.close()
    try:
        os.utime(f, (atime, mtime)) # Try to restore atime and mtime
    except OSError as e:            # Well I tried, didn't I? It just didn't work out.
        pass                        # Just act as if nothing has happened
    return dig.hexdigest()


def dupfind(topdir, hashsums={}, n = 20, ntrials=2, blockSize = 4096, noverify = False):
    for root, dirs, files in os.walk(topdir):
        for f in files:
            fname = os.path.join(root, f)
            if not os.path.isfile(fname): # skip over regular files
                continue
            fsize = os.path.getsize(fname)

            found = True
            if fsize not in hashsums: # the easy case
                hashsums[fsize] = FileOrHash(isHash = False, filename = fname)
                found = False
            else:
                foh = hashsums[fsize]
                basename = foh.filename
                for i in range(ntrials):
                    if not foh.isHash:
                        rseq = getNewRSeq(n, blockSize, fsize)
                        #rseq.sort()
                        hash1 = hashfile(foh.filename, byteOffsets = rseq)
                        foh.hashsum[hash1] = FileOrHash(isHash = False, filename = foh.filename)
                        foh.rseq = rseq
                        foh.isHash = True
                    rseq = foh.rseq
                    hash2 = hashfile(fname, byteOffsets = rseq)
                    if hash2 not in foh.hashsum:
                        foh.hashsum[hash2] = FileOrHash(isHash = False, filename = fname)
                        found = False
                        break
                    else:
                        foh = foh.hashsum[hash2]
                        basename = foh.filename
                if found:
                    if noverify:
                        yield fname, basename
                    else:
                        if not foh.fullhash:
                            foh.fullhash = {}
                            hash1 = hashfile(basename, byteOffsets = range(0, os.path.getsize(basename), blockSize), blockSize = blockSize)
                            foh.fullhash[hash1] = basename
                        hash2 = hashfile(fname, byteOffsets = range(0, fsize, blockSize), blockSize = blockSize)
                        if hash2 in foh.fullhash:
                            yield fname, basename
                        else:
                            foh.fullhash[hash2] = fname

def getNewRSeq(n, blockSize, fileSize):
    res = []
    maxN = floor(fileSize/blockSize)
    l = 0
    for i in range(n):
        r = floor((i+1)*maxN/n)
        res.append(randint(l, r) * blockSize) # We use l, r to make sure that the numbers are widely spread out.
        l = r
    return res

if __name__ == "__main__":
    try:
        import argparse
        parser = argparse.ArgumentParser(description = 'Find duplicate files')
        parser.add_argument('dirs', metavar='Dir', type=str, nargs='*', help='dirs to traverse')
        parser.add_argument("--noverify", help="Do not verify using a full hash for each match", action="store_true")
        parser.add_argument("--bs", help="size of a block", type=int, default=4096)
        parser.add_argument("--nblocks", help="Number of blocks to use in one trial", type=int, default=5)
        parser.add_argument("--ntrials", help="Number of trials to perform", type=int, default=2)
        parser.add_argument("--printf", help="Printf format string. {0} for the duplicate file, {1} for the base file", type=str, default=None)
        parser.add_argument("-q", "--quiet", help="print each file as it is found", action="store_true")


        args = parser.parse_args()

        if not args.dirs:
            args.dirs=["."]
            hashsums={}
            for d in args.dirs:
                res = dupfind(d, hashsums, noverify = args.noverify)
                for f, base in res:
                    if not args.printf:
                        args.printf = "{0}"
                    if not args.quiet:
                        print(args.printf.format(f, base))
    except KeyboardInterrupt as e:
        print("Interrupt received. Quitting")
