"""ruin_shed_closed2: a collapsed shed roof over broken side walls and exposed timber braces.

(Astra Laplace, 7 Oct 2026, e2) extra side views revealed thin-layer triangular fans
rising beside wall stumps and torn patches across supported roof debris. Separate exposed
upward regions hold shallow blankets; slender braces and steep walls let snow through,
without bridging open rubble bays or rounding down the upright sides.
"""
import numpy as np
import snow_hand as H


def build(m, v):
    if not getattr(m, '_sz_laplace_parts', False):
        thin = []
        for p in range(int(m.part_t.max()) + 1):
            pts = m.V[np.unique(m.T[m.part_t == p])]
            ex = np.ptp(pts, axis=0)
            if H.part_top_area(m, p, 0.65) < 0.08:
                thin.append(p)
        H.through(m, thin)
        m._sz_laplace_parts = True
    tops = m.tops(v, ny_min=0.65, slope=False) & (m.NYF >= 0.65)
    out = []
    for region, heights in m.regions(tops, v, close=0.0, tau=0.02, min_area=0.015):
        out.append(m.blanket(region, heights, v, over=0.005, smooth=0.025,
                             spacing=0.15, fill=0.0, holes=0.002, bury=False))
    return H.join(out)
