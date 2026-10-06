"""misc_chair_camp2: a folding camp chair (Expansion mapping).

(Opus, 6 Oct, e1; Astra Boyle) at v7 the seat cap tore into an upright flap with punctures where the backrest's bar
passes through it; (e1b, McClintock) the wreck route left two punctures and a seam. Part table: 0 the tube frame,
5 the seat (0.2 m2 of top), 6 the backrest. Only the seat holds snow (mine_rail_tram's way); the frame and the
backrest let the snow through, so their bars do not punch holes in the seat's pillow. A short lip."""
import numpy as np
import snow_hand as H

THROUGH = (0, 6)


def build(m, v):
    if getattr(m, '_sz_see', None) is None:
        sel = np.isin(m.part_t, THROUGH)
        m.occ_t = m.occ_t & ~sel
        m.good_t = m.good_t & ~sel
        m._raster()
        m._bvh()
        m._sz_see = THROUGH
    m._sz_parts = (5,)
    m._sz_rails = ([], [])
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05)
