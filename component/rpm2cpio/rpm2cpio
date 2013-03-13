#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Standalone RPM to CPIO converter
# Copyright (c) 2012 Rudá Moura
#

'''Extract cpio archive from RPM package.

rpm2cpio converts the RPM on standard input or first parameter to a CPIO archive on standard output.

Usage:
rpm2cpio < adjtimex-1.20-2.1.i386.rpm  | cpio -it
./sbin/adjtimex
./usr/share/doc/adjtimex-1.20
./usr/share/doc/adjtimex-1.20/COPYING
./usr/share/doc/adjtimex-1.20/COPYRIGHT
./usr/share/doc/adjtimex-1.20/README
./usr/share/man/man8/adjtimex.8.gz
133 blocks
'''

import sys
import StringIO
import gzip

RPM_MAGIC = '\xed\xab\xee\xdb'
GZIP_MAGIC = '\x1f\x8b'

def rpm2cpio(stream_in=sys.stdin, stream_out=sys.stdout):
    lead = stream_in.read(96)
    if lead[0:4] != RPM_MAGIC:
        raise IOError, 'the input is not a RPM package'
    data = stream_in.read()
    idx = data.find(GZIP_MAGIC)
    if idx == -1:
        raise IOError, 'could not find compressed cpio archive'
    gzstream = StringIO.StringIO(data[idx:])
    gzipper = gzip.GzipFile(fileobj=gzstream)
    data = gzipper.read()
    stream_out.write(data)
    
if __name__ == '__main__':
    if sys.argv[1:]:
        try:
            fin = open(sys.argv[1])
            rpm2cpio(fin)
            fin.close()
        except IOError, e:
            print 'Error:', sys.argv[1], e
    else:
        try:
            rpm2cpio()
        except IOError, e:
            print 'Error:', e
