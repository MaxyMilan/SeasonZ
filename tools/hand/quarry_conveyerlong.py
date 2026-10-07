"""quarry_conveyerlong: a long inclined quarry conveyor on a slender wheeled support frame.

(Astra Kepler, 7 Oct 2026, b1) the slender struts and wheel-frame junctions grew isolated mushroom-shaped snow
lobes. The belt, end housing and two raised side edges (parts 0, 3, 6, 7) receive separate short blankets. Thin
braces and the low wheel gear let snow through; nearly level exposed panel cells alone carry the cap, without
bridging the side edges down to the supports.
"""
import snow_hand as H

PANELS = (0, 3, 6, 7)


def build(m, v):
    H.through(m, [p for p in range(int(m.part_t.max()) + 1) if p not in PANELS])
    out = []
    for p in PANELS:
        tops = m.tops(v, parts=(p,), ny_min=0.75) & (m.NYF >= 0.75)
        for region, heights in m.regions(tops, v, close=0.0, min_area=0.01):
            out.append(m.blanket(region, heights, v, over=0.005, shoulder=0.25,
                                 smooth=0.03, fill=0.005, bury=False))
    return H.join(out)
