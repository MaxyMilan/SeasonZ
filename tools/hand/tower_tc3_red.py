"""tower_tc3_red: a lattice communications tower with broad platforms, concrete feet and thin antennas.

(Astra Euclid, 7 Oct 2026, b1) review found antenna domes and upright snow shards. The grey tower's repair
passed, but the red model's vertex/triangle/part ordering differs, so fixed grey part IDs are not reused.
Select shallow broad horizontal members by geometry and the wide foundation feet at the source base. The
remaining antennas, ladders and thin braces let snow through. Supported platform blankets keep short edges.
"""
import numpy as np
import snow_hand as H


def build(m, v):
    if not hasattr(m, '_sz_red_platforms'):
        keep = []
        base = float(m.V[:, 1].min())
        for p in range(int(m.part_t.max()) + 1):
            pts = m.V[np.unique(m.T[m.part_t == p])]
            ex = np.ptp(pts, axis=0)
            top = H.part_top_area(m, p, 0.9)
            horizontal = ex[1] <= 0.25 and min(ex[0], ex[2]) >= 0.12 and top >= 0.1
            foot = pts[:, 1].min() <= base + 0.05 and min(ex[0], ex[2]) >= 1.0 and max(ex[0], ex[2]) <= 2.5 and top >= 1.0
            if horizontal or foot:
                keep.append(p)
        m._sz_red_platforms = tuple(keep)
        H.through(m, [p for p in range(int(m.part_t.max()) + 1) if p not in keep])
    tops = m.tops(v, parts=m._sz_red_platforms, ny_min=0.9) & (m.NYF >= 0.9)
    return m.cover(v, tops, over=0.015, smooth=0.025, bury=False)
