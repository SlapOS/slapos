# Copyright (C) 2023  Nexedi SA and Contributors.
#                     Kirill Smelkov <kirr@nexedi.com>
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

"""Package earfcn helps to do computations with LTE bands, frequencies and EARFCN numbers.

- frequency converts EARFCN to frequency.
- dl2ul converts DL EARFCN to corresponding UL EARFCN.
- band returns information about band to which EARFCN belongs.
"""


import collections

# TS 36.101 v16.18.0  Table 5.7.3-1
#  band          fdl_lo        Noffs_dl         NDL range       ful_lo       Noffs_ul       NUL range
_tab573_1 = """\
     1           2110              0            0 - 599          1920          18000        18000 - 18599
     2           1930            600          600 - 1199         1850          18600        18600 - 19199
     3           1805           1200         1200 - 1949         1710          19200        19200 - 19949
     4           2110           1950         1950 - 2399         1710          19950        19950 - 20399
     5            869           2400         2400 - 2649          824          20400        20400 - 20649
     6            875           2650         2650 - 2749          830          20650        20650 - 20749
     7           2620           2750         2750 - 3449         2500          20750        20750 - 21449
     8            925           3450         3450 - 3799          880          21450        21450 - 21799
     9           1844.9         3800         3800 - 4149         1749.9        21800        21800 - 22149
    10           2110           4150         4150 - 4749         1710          22150        22150 - 22749
    11           1475.9         4750         4750 - 4949         1427.9        22750        22750 - 22949
    12            729           5010         5010 - 5179          699          23010        23010 - 23179
    13            746           5180         5180 - 5279          777          23180        23180 - 23279
    14            758           5280         5280 - 5379          788          23280        23280 - 23379
    …
    17            734           5730         5730 - 5849          704          23730        23730 - 23849
    18            860           5850         5850 - 5999          815          23850        23850 - 23999
    19            875           6000         6000 - 6149          830          24000        24000 - 24149
    20            791           6150         6150 - 6449          832          24150        24150 - 24449
    21           1495.9         6450         6450 - 6599         1447.9        24450        24450 - 24599
    22           3510           6600         6600 - 7399         3410          24600        24600 - 25399
    23           2180           7500         7500 - 7699         2000          25500        25500 - 25699
    24           1525           7700         7700 - 8039         1626.5        25700        25700 - 26039
    25           1930           8040         8040 - 8689         1850          26040        26040 - 26689
    26            859           8690         8690 - 9039          814          26690        26690 - 27039
    27            852           9040         9040 - 9209          807          27040        27040 - 27209
    28            758           9210         9210 - 9659          703          27210        27210 - 27659
    29            717           9660         9660 - 9769                          N/A
    30           2350           9770         9770 - 9869         2305          27660        27660 - 27759
    31            462.5         9870         9870 - 9919          452.5        27760        27760 - 27809
    32           1452           9920         9920 - 10359                         N/A
    33           1900          36000        36000 - 36199        1900          36000        36000 - 36199
    34           2010          36200        36200 - 36349        2010          36200        36200 - 36349
    35           1850          36350        36350 - 36949        1850          36350        36350 - 36949
    36           1930          36950        36950 - 37549        1930          36950        36950 - 37549
    37           1910          37550        37550 - 37749        1910          37550        37550 - 37749
    38           2570          37750        37750 - 38249        2570          37750        37750 - 38249
    39           1880          38250        38250 - 38649        1880          38250        38250 - 38649
    40           2300          38650        38650 - 39649        2300          38650        38650 - 39649
    41           2496          39650        39650 - 41589        2496          39650        39650 - 41589
    42           3400          41590        41590 - 43589        3400          41590        41590 - 43589
    43           3600          43590        43590 - 45589        3600          43590        43590 - 45589
    44            703          45590        45590 - 46589         703          45590        45590 - 46589
    45           1447          46590        46590 - 46789        1447          46590        46590 - 46789
    46           5150          46790        46790 - 54539        5150          46790        46790 - 54539
    47           5855          54540        54540 - 55239        5855          54540        54540 - 55239
    48           3550          55240        55240 - 56739        3550          55240        55240 - 56739
    49           3550          56740        56740 - 58239        3550          56740        56740 - 58239
    50           1432          58240        58240 - 59089        1432          58240        58240 - 59089
    51           1427          59090        59090 - 59139        1427          59090        59090 - 59139
    52           3300          59140        59140 - 60139        3300          59140        59140 - 60139
    53           2483.5        60140        60140 - 60254        2483.5        60140        60140 - 60254
    …
    64                                                 Reserved
    65           2110          65536        65536 - 66435        1920         131072       131072 - 131971
    66           2110          66436        66436 - 67335        1710         131972       131972 - 132671
    67            738          67336        67336 - 67535                          N/A
    68            753          67536        67536 - 67835         698         132672       132672 - 132971
    69           2570          67836        67836 - 68335                          N/A
    70           1995          68336        68336 - 68585        1695         132972       132972 - 133121
    71            617          68586        68586 - 68935         663         133122       133122 - 133471
    72            461          68936        68936 - 68985         451         133472       133472 - 133521
    73            460          68986        68986 - 69035         450         133522       133522 - 133571
    74           1475          69036        69036 - 69465        1427         133572       133572 - 134001
    75           1432          69466        69466 - 70315                          N/A
    76           1427          70316        70316 - 70365                          N/A
    85            728          70366        70366 - 70545         698         134002       134002 - 134181
    87            420          70546        70546 - 70595         410         134182       134182 - 134231
    88            422          70596        70596 - 70645         412         134232       134232 - 134281
"""

# EBand represents information about one LTE band.
EBand = collections.namedtuple('EBand',
            ['band', 'fdl_lo', 'ndl_lo', 'ndl_hi', 'ful_lo', 'nul_lo', 'nul_hi'])

# _eband_tab is table with all LTE bands.
_eband_tab = []  # of EBand
def _():
    eprev = None
    for l in _tab573_1.splitlines():
        v = l.split()
        assert len(v) > 0, v

        if len(v) == 1:
            assert v[0] == '…', v
            continue
        band = int(v[0])

        if len(v) == 2:
            assert v[1] == 'Reserved', v
            continue

        assert len(v) >= 6, v
        fdl_lo  = float(v[1])
        noff_dl = int  (v[2])
        ndl_lo  = int  (v[3])
        assert v[4] == '-', v
        ndl_hi  = int  (v[5])
        assert noff_dl == ndl_lo, v
        assert ndl_lo < ndl_hi, v

        if len(v) == 7:
            assert v[6] == 'N/A'
            ful_lo = None
            nul_lo = None
            nul_hi = None
        else:
            assert len(v) == 11, v
            ful_lo  = float(v[6])
            noff_ul = int  (v[7])
            nul_lo  = int  (v[8])
            assert v[9] == '-', v
            nul_hi  = int  (v[10])
            assert noff_ul == nul_lo, v
            assert nul_lo < nul_hi, v

        eband = EBand(band, fdl_lo, ndl_lo, ndl_hi, ful_lo, nul_lo, nul_hi)
        if eprev is not None:
            n = eband
            p = eprev
            assert p.band   < n.band
            assert p.ndl_hi < n.ndl_lo
            if p.ful_lo is not None  and  n.ful_lo is not None:
                assert p.nul_hi < n.nul_hi
        _eband_tab.append(eband)
        eprev = eband
_()


# band returns information about band covering earfcn.
def band(earfcn): # -> (EBand, is_dl) | KeyError
    try:
        b = _eband_lookup_dl(earfcn)
    except KeyError:
        pass
    else:
        return b, True

    try:
        b = _eband_lookup_ul(earfcn)
    except KeyError:
        pass
    else:
        return b, False

    raise KeyError('no band that corresponds to EARFCN=%r' % earfcn)

# _eband_lookup_{dl,ul} look up EBand by DL/UL EARFCN.
def _eband_lookup_dl(dl_earfcn): # -> EBand | KeyError
    # TODO linear search -> bsearch
    for eband in _eband_tab:
        if eband.ndl_lo <= dl_earfcn <= eband.ndl_hi:
            return eband
    raise KeyError('no band that corresponds to DL EARFCN=%r' % dl_earfcn)

def _eband_lookup_ul(ul_earfcn): # -> EBand | KeyError
    # TODO linear search -> bsearch
    for eband in _eband_tab:
        if eband.nul_lo <= ul_earfcn <= eband.nul_hi:
            return eband
    raise KeyError('no band that corresponds to UL EARFCN=%r' % ul_earfcn)


# dl2ul returns UL EARFCN that corresponds to DL EARFCN.
def dl2ul(dl_earfcn): # -> ul_earfcn
    b = _eband_lookup_dl(dl_earfcn)
    assert b.ndl_lo <= dl_earfcn <= b.ndl_hi
    ul_earfcn = b.nul_lo + (dl_earfcn - b.ndl_lo)
    assert b.nul_lo <= ul_earfcn <= b.nul_hi
    return ul_earfcn


# frequency returns frequency corresponding to DL or UL EARFCN.
def frequency(earfcn): # -> freq (MHz)
    b, dl = band(earfcn)
    if dl:
        assert b.ndl_lo <= earfcn <= b.ndl_hi
        fdl = b.fdl_lo + 0.1*(earfcn - b.ndl_lo)       # TS 36.101 5.7.3
        return fdl
    else:
        assert b.nul_lo <= earfcn <= b.nul_hi
        ful = b.ful_lo + 0.1*(earfcn - b.nul_lo)       # TS 36.101 5.7.3
        return ful


# XXX _testme
def _testme():
    assert dl2ul(300) == 18300
    assert frequency(300) == 2140
    # XXX ...
