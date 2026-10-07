"""ship_medium_back: the broken aft ship section, deck, mast and long hanging rigging cables.

(Astra Kepler, 7 Oct 2026, b1) thin rigging parts 1 and 2 carried chains of rectangular snow tabs. The broad
exposed deck, mast platforms and fittings receive separate supported blankets; thin rigging and upright poles
let snow through. Each surface keeps its actual slope and depth, with small round edges and no gap bridging.
The selective volumetric trial was stopped after ten minutes before v1; surface blankets avoid its large volume.
"""
import snow_hand as H

PANELS = (3, 4, 5, 6, 7, 9, 10, 13)


def build(m, v):
    H.through(m, [p for p in range(int(m.part_t.max()) + 1) if p not in PANELS])
    out = []
    for p in PANELS:
        tops = m.tops(v, parts=(p,), ny_min=0.75) & (m.NYF >= 0.75)
        for region, heights in m.regions(tops, v, close=0.0, min_area=0.025):
            out.append(m.blanket(region, heights, v, over=0.015, shoulder=0.25,
                                 smooth=0.04, fill=0.01, bury=False))
    return H.join(out)
