"""Cable reel: c37 showed spoke fins and triangular tears at the top rim.
ast3 keeps the upper disc, rims and crosspieces in one snow field.
The narrow ribs must contribute instead of cutting holes through the cap;
disabling height bands lets their snow merge, with only a short rounded lip.
ast3 attempt 2's stronger unfolding/beautify made facets worse. Attempt 3
restores normal cleanup and filters only the thinnest rib tops (3.5 cm).
"""
import snow_hand as H


def build(m, v):
    m._sz_parts = (0, 1, 2, 3, 4, 5)
    m._sz_rails = ([], [])
    return H.consts(m, v, A7_THIN=.035, A7_LEDGE=False,
                    A7_BANDH=0., A7_OVL=.15, A7_LIPDROP=.03)
