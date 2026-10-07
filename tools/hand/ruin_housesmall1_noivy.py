"""ruin_housesmall1_noivy: ruined house walls and slabs surrounded by rubble heaps.

(Astra Gauss, 7 Oct 2026, e2) Laplace surface blankets removed the outer rubble
fans, but the automatic beam and slope route retained curtains below the upper
slab. Separate upper slabs, height bands and rubble regions hold tapered blankets; thin steep fragments
let snow through. Short lips and zero gap closing preserve open framing. Low
exposed floors keep their snow from v1. The mound uses the native snow slope
selection: its fallen slab has source normal.y=.615-.637 and must not be
removed by the stricter structural .65 cutoff. This last adjustment needs a
fresh seven-depth build before another submission.
"""
import numpy as np
import snow_hand as H


def build(m, v):
    m.ground = float(m.V[:, 1].min()) - 0.25
    if not getattr(m, '_sz_gauss_parts', False):
        thin = []
        for p in range(int(m.part_t.max()) + 1):
            pts = m.V[np.unique(m.T[m.part_t == p])]
            ex = np.ptp(pts, axis=0)
            if H.part_top_area(m, p, 0.65) < 0.08:
                thin.append(p)
        H.through(m, thin)
        m._sz_gauss_parts = True
    tops = m.tops(v, ny_min=0.65, slope=False) & (m.NYF >= 0.65)
    out = []
    # The rubble mound, upper slabs and stepped masonry must not share an
    # outline: its triangulation otherwise draws a curtain across open air.
    groups = [tops & (m.PART == p) for p in (7, 65)]
    groups.append(m.tops(v, parts=(281,)))
    rest = tops & ~np.isin(m.PART, (7, 65, 281))
    for low, high in ((-100., -0.8), (-0.8, 0.6), (0.6, 2.), (2., 100.)):
        groups.append(rest & (m.Z >= low) & (m.Z < high))
    for group in groups:
        for region, heights in m.regions(group, v, close=0.0, tau=0.02, min_area=0.015):
            out.append(m.blanket(region, heights, v, rim='taper', over=0.0, smooth=0.0,
                                 spacing=0.12, fill=0.0, holes=0.002, bury=False))
    return H.join(out)
