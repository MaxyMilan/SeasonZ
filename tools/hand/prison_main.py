"""prison_main: the large prison block with a pitched roof, tower and dormers.

(Astra Curie, 7 Oct 2026, b1) the volume took 48 minutes and left broad thin-layer
tears, radial fans and hanging sheets at roof junctions. Supported surface blankets
follow the measured main roof (105), tower roof (104) and separate dormer roofs.
Real height steps stay separated; thin fittings let snow through. Dense sampling
and short lips preserve roof detail without burying snow down the facade.

(Astra Euler II, 7 Oct 2026, b1) independent review accepted the roof coverage
but found peeling round skirts beside the tower. Tapered edges finish on the
roof support without a rolled skirt or overhang. The depth-independent roof
regions are cached; each of the seven depths still gets its own blanket.
"""
import numpy as np
import snow_hand as H


def build(m, v):
    if not hasattr(m, '_sz_euler2_prison_regions'):
        thin = [p for p in range(int(m.part_t.max()) + 1)
                if H.part_top_area(m, p, ny_min=0.5) < 0.025]
        H.through(m, thin)
        tops = m.tops(1, slope=False) & (m.NYF >= 0.55)
        groups = [tops & (m.PART == p) for p in (104, 105)]
        groups.append(tops & ~np.isin(m.PART, (104, 105)))
        m._sz_euler2_prison_regions = [r for group in groups
            for r in m.regions(group, 1, close=0.0, tau=0.06, min_area=0.015)]
    out = []
    for region, heights in m._sz_euler2_prison_regions:
        out.append(m.blanket(region, heights, v, rim='taper', over=0.0,
                             smooth=0.0, spacing=0.15, fill=0.0,
                             holes=0.002, bury=False))
    return H.join(out)
