#!/usr/bin/python
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
        res.append(randint(l, r) * blockSize)
        l = r
    return res

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description = 'Find duplicate files')
    parser.add_argument('dirs', metavar='Dir', type=str, nargs='*', help='dirs to traverse')

    args = parser.parse_args()

    if not args.dirs:
        args.dirs=["."]
    hashsums={}
    for d in args.dirs:
        res = dupfind(d, hashsums)
        for f, base in res:
            print(f, " is a copy of " , base)
