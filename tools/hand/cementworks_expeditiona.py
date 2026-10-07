"""cementworks_expeditiona: an industrial dispatch platform with hoppers, walkways and pole lamps.

(Astra Laplace, 7 Oct 2026, b1) small lamp heads grew tall angular snow mounds. Broad roofs
and platforms receive supported surface blankets; a finer volume trial was too expensive. Thin rails
and lamp poles let snow through. Source renders show raised central lamp housings: each half stays separate across that height step and receives shallow
supported blankets with dense sampling and no surface smoothing to keep the thin layer above the curved source; the narrow lamp poles stay bare.
"""
import numpy as np
import snow_hand as H

LAMPS = (640, 641, 642, 643, 646, 647)
POLES = (351, 353, 394)


def build(m, v):
    if not getattr(m, '_sz_huygens_poles', False):
        rods = list(POLES)
        for p in range(int(m.part_t.max()) + 1):
            if p in LAMPS:
                continue
            pts = m.V[np.unique(m.T[m.part_t == p])]
            ex = np.ptp(pts, axis=0)
            if ex[1] < 0.4 and max(ex[0], ex[2]) > 0.7:
                if min(ex[0], ex[2]) < 0.12 or H.part_top_area(m, p, 0.8) < 0.12*ex[0]*ex[2]:
                    rods.append(p)
        H.through(m, rods)
        m._sz_huygens_poles = True
    out = []
    # Adjacent hopper panels share a cap; tall silo steps remain separate.
    hopper = (24, 64) + tuple(range(600, 608))
    groups = [hopper] + [(p,) for p in range(int(m.part_t.max()) + 1)
                         if p not in hopper and p not in LAMPS
                         and H.part_top_area(m, p, 0.65) >= 0.15]
    for group in groups:
        tops = m.tops(v, parts=group, ny_min=0.65) & (m.NYF >= 0.65)
        for region, heights in m.regions(tops, v, close=0.06 if group == hopper else 0.0, tau=0.1, min_area=0.015):
            out.append(m.blanket(region, heights, v, over=0.01, smooth=0.04,
                                 fill=0.02, bury=False))
    for p in LAMPS:
        tops = m.tops(v, parts=(p,), ny_min=0.65, slope=False) & (m.NYF >= 0.65)
        for region, heights in m.regions(tops, v, close=0.0, min_area=0.001):
            out.append(m.blanket(region, heights, v, depth=1.0, over=0.003,
                                 smooth=0.0, spacing=0.025, shoulder=0.2,
                                 holes=0.0, fill=0.0, bury=False))
    return H.join(out)
