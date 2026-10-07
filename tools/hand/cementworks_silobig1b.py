"""cementworks_silobig1b: a large concrete silo with a roof deck and damaged perimeter railing.

(Astra Huygens, 7 Oct 2026, b1) the thin railing rods grew separate wedges and angular strips.
Measured perimeter rods above the roof deck let snow through, including bent rails whose wide bounding
boxes defeated a simple width filter. Supported blankets follow the main roof, silo ledges and hatch
debris, with short rounded edges and no snow on the steep concrete walls.
"""
import numpy as np
import snow_hand as H


def build(m, v):
    if not getattr(m, '_sz_huygens_rods', False):
        rods = []
        for p in range(int(m.part_t.max()) + 1):
            pts = m.V[np.unique(m.T[m.part_t == p])]
            lo, hi = pts.min(0), pts.max(0)
            # Include bent corner rods extending inward from the nominal perimeter.
            if lo[1] > 17.7 and hi[1] < 19.2 and H.part_top_area(m, p, 0.8) < 0.1:
                rods.append(p)
        H.through(m, rods)
        m._sz_huygens_rods = True
    tops = m.tops(v, ny_min=0.75) & (m.NYF >= 0.75)
    return m.cover(v, tops, over=0.01, smooth=0.04, fill=0.02, bury=False)
