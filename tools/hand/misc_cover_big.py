"""misc_cover_big: a row of large rocks as cover, low rock shelves at both ends.

(Opus, 6 Oct, m1, c37) the low shelves at both ends (within 25 cm of the ground) stayed bare while the rocks above
carried full pillows. Rock: the rough treatment, the low shelves included, with a short lip."""
import snow_hand as H


def build(m, v):
    m.rough = True
    if not getattr(m, '_sz_low', False):
        # its lowest broad tops lie within 25 cm of the ground, which tops() leaves to the terrain's cover
        m.ground -= 0.22
        m._sz_low = True
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05, A7_CREVICE=0.15)
