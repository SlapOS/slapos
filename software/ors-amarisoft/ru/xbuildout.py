# Copyright (C) 2023  Nexedi SA and Contributors.
#
# This program is free software: you can Use, Study, Modify and Redistribute
# it under the terms of the GNU General Public License version 3, or (at your
# option) any later version, as published by the Free Software Foundation.
#
# You can also Link and Combine this program with other software covered by
# the terms of any of the Free Software licenses or any of the Open Source
# Initiative approved licenses and Convey the resulting work. Corresponding
# source of such a combination shall include the source code for all other
# software used.
#
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See COPYING file for full licensing terms.
# See https://www.nexedi.com/licensing for rationale and options.
"""Package xbuildout provides additional buildout-related utilities.

- encode/decode convert string to/from form, that is suitable to be used in
  names of buildout sections.
"""


# encode converts string s into form suitable to be used in names of buildout sections.
#
# The encoding never fails, does not loose information and can be reversed back via decode.
def encode(s: str): # -> str
    s = s.encode('utf-8')
    outv = []
    emit = outv.append
    for c in s:
        c = bytes([c])  # int -> bytechar
        # _ serves as escape character
        if c == b'_':
            emit(b'__')

        # other characters allowed by buildout go as is
        elif (b'a' <= c <= b'z')    or  \
             (b'A' <= c <= b'Z')    or  \
             (b'0' <= c <= b'9')    or  \
             (c in b'.-'):
            emit(c)

        # all other bytes go as escaped hex
        else:
            emit(b'_%02x' % ord(c))

    out = b''.join(outv)
    out = out.decode('utf-8')   # should not fail
    return out


# decode provides reverse operation for encode.
def decode(s: str): # -> str | ValueError | UnicodeDecodeError
    s = s.encode('utf-8')
    outv = []
    emit = outv.append
    def bad(reason):
        raise ValueError(reason)
    while len(s) > 0:
        c = s[0:1]
        s = s[1:]

        if c != b'_':
            emit(c)
            continue

        if len(s) < 2:
            bad("truncated escape sequence")
        x = s[:2]
        s = s[2:]
        i = int(x, 16)  # raises ValueError if not ok
        c = bytes([i])
        emit(c)

    out = b''.join(outv)
    out = out.decode('utf-8')   # raises UnicodeDecodeError if it was invalid UTF-8
    return out


# ----------------------------------------

import re

def test_encode():
    # verify all ascii characters one by one
    bok = re.compile(r'[a-zA-Z0-9.-]')  # characters that are ok to use in buildout except '_'
    for i in range(0x80):
        c = chr(i)
        e = encode(c)
        if bok.match(c):
            assert e == c
        elif c == '_':
            assert e == '__'
        else:
            assert e == '_%02x' % i
        assert decode(e) == c

    # also explicitly test several example cases, including unicode
    testv = [
        #  s    encoded
        ('',     ''),
        ('a',      'a'),
        ('ayzAYZ09.-',  'ayzAYZ09.-'),
        ('_',       '__'),
        (' ',       '_20'),
        ('αβγ',     '_ce_b1_ce_b2_ce_b3'),
        ('a b+c_d'  'a_20b_43c__d'),
    ]

    for (s, encok) in testv:
        assert encode(s) == encok
        assert decode(encok) == s


    # XXX decode error

    # XXX UTF-8 error
