#!/usr/bin/env python
# test dl_nr_arfcn -> ssb_nr_arfcn calculation

import nrarfcn as nr

def default_ssb_nr_arfcn(dl_nr_arfcn):
    f = nr.get_frequency(nrarfcn=dl_nr_arfcn)
    gscn = nr.get_gscn_by_frequency(f)
    if nr.get_frequency_by_gscn(gscn) > f:
        gscn -= 1
    fg = nr.get_frequency_by_gscn(gscn)
    fg_arfcn = nr.get_nrarfcn(fg)
    return fg_arfcn

def _(dl_nr_arfcn):
    ssb_nr_arfcn = default_ssb_nr_arfcn(dl_nr_arfcn)
    f = nr.get_frequency(dl_nr_arfcn)
    fssb = nr.get_frequency(ssb_nr_arfcn)
    print('%d  ->  %d\t;  %g MHz\t->  %g Mhz' % (dl_nr_arfcn, ssb_nr_arfcn, f, fssb))

print('# dl_nr_arfcn  ->  ssb_nr_arfcn')
_(633300)
_(632628)
_(630336)
_(627300)
_(624288)
_(532000)
_(530890)
_(526000)
_(524650)
_(523020)
_(437000)
_(176300)
