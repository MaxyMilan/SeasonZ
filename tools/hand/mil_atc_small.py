"""mil_atc_small: a control tower with a flat cabin roof, an exposed balcony and a lower annex roof.

(Astra Euclid, 7 Oct 2026, e2) the volumetric cap ran down sloping window frames as thick fingers and left a
detached strip on the balcony fascia. Keep the broad roof, balcony, landings and visible substantial trim from
the part table; antenna fittings and slender window/railing members let snow through. Each panel's nearly level
tops get their own short blanket, without downward burial or bridges between the roof and glazing.
"""
import snow_hand as H

PANELS = (1, 3, 4, 5, 6, 31, 49, 50, 124, 129, 132, 136, 137, 173, 208)


def build(m, v):
    H.through(m, [p for p in range(int(m.part_t.max()) + 1) if p not in PANELS])
    out = []
    for p in PANELS:
        tops = m.tops(v, parts=(p,), ny_min=0.85) & (m.NYF >= 0.85)
        for region, heights in m.regions(tops, v, close=0.0, min_area=0.02):
            out.append(m.blanket(region, heights, v, over=0.015, shoulder=0.25,
                                 smooth=0.04, fill=0.01, bury=False))
    return H.join(out)
