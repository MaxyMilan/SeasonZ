"""tower_tc3_grey: a steel lattice communications tower with platforms and antennas (Expansion mapping).

(Astra Socrates, 7 Oct 2026, e2) thin antenna crossbars grew domes and vertical rods grew long slivers. Keep
the broad platforms, concrete feet and wide horizontal structural members. Antennas, railings, ladders and
diagonal braces let snow through. Separate supported blankets leave short lips and no burial down upright rods."""
import numpy as np
import snow_hand as H


def build(m, v):
    if not hasattr(m, '_sz_tower_platforms'):
        keep = {97, 98, 99, 100, 326, 420, 514, 668, 670}
        for p in range(int(m.part_t.max()) + 1):
            pts = m.V[np.unique(m.T[m.part_t == p])]
            ex = np.ptp(pts, axis=0)
            if ex[1] <= 0.25 and min(ex[0], ex[2]) >= 0.12 and H.part_top_area(m, p, 0.9) >= 0.1:
                keep.add(p)
        m._sz_tower_platforms = tuple(sorted(keep))
        H.through(m, [p for p in range(int(m.part_t.max()) + 1) if p not in keep])
    tops = m.tops(v, parts=m._sz_tower_platforms, ny_min=0.9) & (m.NYF >= 0.9)
    return m.cover(v, tops, over=0.015, smooth=0.025, bury=False)
