"""hotel_damaged: a tall ruined hotel with broken floor frames, roof terraces and a broad low canopy.

(Astra Euler, 7 Oct 2026, b1) the volume route draped long snow plates down steep broken facade members.
Only upward faces within about 41 degrees receive surface blankets. Per-part regions keep the broken
frames separate from roof and canopy caps, without bridging open rubble gaps or burying into walls.
"""
import snow_hand as H


def build(m, v):
    if not hasattr(m, '_sz_euler_parts'):
        m._sz_euler_parts = tuple(p for p in range(int(m.part_t.max()) + 1)
                                 if H.part_top_area(m, p, 0.75) >= 0.05)
        H.through(m, [p for p in range(int(m.part_t.max()) + 1) if p not in m._sz_euler_parts])
    out = []
    for p in m._sz_euler_parts:
        tops = m.tops(v, parts=(p,), ny_min=0.75, slope=False) & (m.NYF >= 0.75)
        for region, heights in m.regions(tops, v, close=0.0, min_area=0.01):
            out.append(m.blanket(region, heights, v, over=0.005, smooth=0.04,
                                 fill=0.01, shoulder=0.25, bury=False))
    return H.join(out)
