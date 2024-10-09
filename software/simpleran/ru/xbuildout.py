# Copyright (C) 2023-2024  Nexedi SA and Contributors.
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
# Such encoding is needed because buildout forbids to use spaces and many other
# characters in section names, which, in turn, leads to inability to directly
# use arbitrary strings for sections generated based on e.g. instance
# references retrieved from SlapOS Master.
#
# With encoding it becomes possible to use arbitrary names for references
# without leading to instantiation failures like
#
#   zc.buildout.configparser.ParsingError: File contains parsing errors: .../instance-enb.cfg
#       [line 45]: '[promise-testing partition 0.RU-sdr-busy]\n'
#
# and without being vulnerable to buildout code injection.
#
# The encoding never fails, does not loose information and can be reversed back via decode.
#
# It also leaves all characters allowed by buildout except "_" as is, which
# makes encoding to be identity for 99% of the practical cases in existing
# SlapOS profiles. In other words it is safe to use encode for both generated
# and static buildout sections, without the need to also use encode when
# referring to those static sections.
#
# Recommended usage of encode in buildout profiles is via B as illustrated below:
#
#   {#-   B(name) escapes name to be safe to use in buildout code. #}
#   {%-   set B = xbuildout.encode  %}
#
#   ...
#
#   [{{ B('%s-stats' % ru_ref) }}]
#   # code for <ru_ref>-stats section
#
#   ...
#
#   # referring to <ru_ref>-stats
#   ${ {{-B('%s-stats' % ru_ref)}}:output}
#
#
# See also `dumps` in buildout for a way to serialize option values with
# protection against code injection:
#
#   https://lab.nexedi.com/nexedi/slapos.buildout/commit/4e13dcb9
#   https://lab.nexedi.com/nexedi/slapos.recipe.template/commit/84dc7957
def encode(s: str) -> str:
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
def decode(s: str): # -> str | ValueError
    try:
        return _decode(s)
    except Exception as e:
        raise ValueError("invalid encoding: %r" % s) from e

def _decode(s):
    s = s.encode('utf-8')
    outv = []
    emit = outv.append
    while len(s) > 0:
        c = s[:1]
        s = s[1:]

        if c != b'_':
            emit(c)
            continue

        if len(s) < 1:
            raise ValueError("truncated escape sequence")
        x = s[:1]
        s = s[1:]

        if x == b'_':
            emit(b'_')
            continue

        if len(s) < 1:
            raise ValueError("truncated escape sequence")
        x += s[:1]
        s = s[1:]

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
        ('',            ''),
        ('a',           'a'),
        ('ayzAYZ09.-',  'ayzAYZ09.-'),
        ('_',           '__'),
        (' ',           '_20'),
        ('αβγ',         '_ce_b1_ce_b2_ce_b3'),
        ('a b+c_d',     'a_20b_2bc__d'),
    ]
    for (s, encok) in testv:
        assert encode(s) == encok
        assert decode(encok) == s

    # decode errors
    from pytest import raises
    def checkbad(x, f):
        with raises(ValueError, match="invalid encoding") as exci:
            decode(x)
        cause = exci.value.__cause__
        f(cause)

    for x in ('_', '_1', 'a_2'):
        def _(cause):
            assert isinstance(cause, ValueError)
            assert cause.args == ("truncated escape sequence",)
        checkbad(x, _)

    for x in ('_1r', '_r1', 'a_xy'):
        def _(cause):
            assert isinstance(cause, ValueError)
            assert len(cause.args) == 1
            assert cause.args[0] .startswith("invalid literal for int() with base 16:")
        checkbad(x, _)

    for x in ('_c3_28', '_e2_28_a1'):
        def _(cause):
            assert isinstance(cause, UnicodeDecodeError)
        checkbad(x, _)
