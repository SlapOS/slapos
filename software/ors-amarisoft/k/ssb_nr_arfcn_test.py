#!/usr/bin/env python
# test dl_nr_arfcn -> ssb_nr_arfcn calculation

import nrarfcn as nr

khz = 1e-3  # we work in MHz

def default_ssb_nr_arfcn(dl_nr_arfcn, scs_khz):
    f = nr.get_frequency(nrarfcn=dl_nr_arfcn)
    gscn = nr.get_gscn_by_frequency(f)
    if nr.get_frequency_by_gscn(gscn) > f:
        gscn -= 1
    # align fg to be multiple of scs
    scs = scs_khz * khz
    while 1:
        fg = nr.get_frequency_by_gscn(gscn)
        # check `fg % scs == 0` with tolerating fp rounding
        r = (fg % scs) / scs
        #print('gscn %d\tfg %.16g  %%scs  %.16g·scs' % (gscn, fg, r))
        if abs(r - round(r)) < 1e-5:
            break
        gscn -= 1
    fg_arfcn = nr.get_nrarfcn(fg)
    return fg_arfcn

def _(dl_nr_arfcn, scs_khz):
    ssb_nr_arfcn = default_ssb_nr_arfcn(dl_nr_arfcn, scs_khz)
    f = nr.get_frequency(dl_nr_arfcn)
    fssb = nr.get_frequency(ssb_nr_arfcn)
    gssb = nr.get_gscn_by_frequency(fssb)

    scs = scs_khz * khz  # subcarrier spacing
    fssb_div_scs = fssb / scs
    fssb_mod_scs = fssb % scs
    print("%d %d  ->  %d\t;  %.16g MHz\t->  %.16g Mhz\t gscn %d\t/scs %.16g  %%scs %.16g·scs" %
        (dl_nr_arfcn, scs_khz, ssb_nr_arfcn, f, fssb, gssb, fssb_div_scs, fssb_mod_scs/scs))

print('# dl_nr_arfcn scs ->  ssb_nr_arfcn')
_(633300, 30)
_(632628, 30)
_(630336, 30)
_(627300, 30)
_(624288, 30)
_(532000, 30)
_(530890, 30)
_(526000, 30)
_(524650, 30)
_(523020, 30)
_(437000, 30)
_(176300, 30)