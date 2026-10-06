"""tank_small_gas: a horizontal propane tank (part 6, a faceted cylinder 1.5 m across with domed ends) on two feet,
a valve box (4) on top, label plates (10, 11) on the flank, a pipe (2, 7) at one end.

(Opus, 6 Oct) r10/c37: the v7 pillow hung down the curved flanks and over the domed ends in deep lobes. c39-c46: a
cut at 44 degrees left the cap's floor inside the faceted cylinder (white patches through the flank's facets at
v5-v7), no lip at all left a hole by the valve box and lobes still. The c44 cap (the tank's snow where it is at most
44 degrees steep, a lip of 15% of the depth + 1 cm) was clean up to v4: a round tank sheds what falls after that, so
the fourth depth is the deepest (as the trail signs' steep little roofs)."""
import numpy as np
import snow_hand as H


def build(m, v):
    if not getattr(m, '_sz_cyl', False):
        orig = m.tops
        keep = ((m.PART != 6) | (m.NYE >= 0.72)) & ~np.isin(m.PART, [2, 7, 10, 11])
        m.tops = lambda *a, **kw: orig(*a, **kw) & keep
        m._sz_cyl = True
    return H.consts(m, min(v, 4), A7_OVL=0.15, A7_LIPDROP=0.03)
