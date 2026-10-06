"""Shower tent: c37 had right roof holes and snow on sheltered inner walls.
ast3 selects outer fabric and ridge, excluding frame and interior fittings.
Attempt 1's crown filter left broad bare strips; attempt 2 retained wall spots.
ast3 attempt 3 removes minor lower ledges and admits narrow roof cells, with
a stronger minimum layer to reduce roof tears around the crossing framework.
"""
import snow_hand as H


def build(m, v):
    m._sz_parts = (0, 11)
    m._sz_rails = ([], [])
    H.ledges(m, drop=.08, reach=.6, amin=.5, wmin=.16, jump=.08, ny=.5)
    return H.consts(m, v, A7_OVL=.1, A7_LIPDROP=.03, A7_BANDH=0.,
                    A5_STEEP_SMOOTH=50., A7_THIN=0., A7_MINLAYER=.5)
