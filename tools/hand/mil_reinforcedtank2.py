"""mil_reinforcedtank2: a broad reinforced storage dome with rooftop vents and fittings.

(Astra Noether, 7 Oct 2026, b1) the coarse volume made torn fans and large bare
islands at every depth. As on the approved reinforcedtank1, the measured dome
(part 541) receives a continuous supported surface blanket, with separate caps
on the substantial rooftop surfaces. Thin rods and narrow fittings let snow
through; short lips stop the cap from hanging down the dome or vent sides.
"""
import numpy as np
import snow_hand as H


def build(m, v):
    if not hasattr(m, '_sz_noether_panels'):
        panels = []
        for p in range(int(m.part_t.max()) + 1):
            area = H.part_top_area(m, p, ny_min=0.8)
            pts = m.V[np.unique(m.T[m.part_t == p])]
            extent = np.ptp(pts, axis=0)
            if area >= 0.1 and area / max(float(np.hypot(extent[0], extent[2])), 0.01) >= 0.07:
                panels.append(p)
        m._sz_noether_panels = tuple(panels)
        H.through(m, [p for p in range(int(m.part_t.max()) + 1) if p not in panels])
    out = []
    for p in m._sz_noether_panels:
        limit = 0.55 if p == 541 else 0.8
        tops = m.tops(v, parts=(p,), ny_min=limit) & (m.NYF >= limit)
        for region, heights in m.regions(tops, v, close=0.0, min_area=0.01):
            out.append(m.blanket(region, heights, v, over=0.01, shoulder=0.25,
                                 smooth=0.06 if p == 541 else 0.025, fill=0.01, bury=False))
    return H.join(out)
