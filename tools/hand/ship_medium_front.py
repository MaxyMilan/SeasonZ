"""ship_medium_front: a tilted ship hull with open decks, a deckhouse, masts and thin rigging.

(Astra Kepler, 7 Oct 2026, b1) the rigging carried rectangular snow tabs and the deck cap folded into sharp
triangles. Rigging assemblies 48 and 49 let snow through. Independently measured parts with at least 0.1 m2
of real top receive separate blankets on their shallow exposed faces, with short lips and no gap bridging.
The deckhouse tiers, deck and mast platforms retain actual depth growth; steep hull sides stay bare.
"""
import snow_hand as H

WIRE = (48, 49)


def build(m, v):
    H.through(m, WIRE)
    if not hasattr(m, '_sz_kepler_panels'):
        m._sz_kepler_panels = tuple(p for p in range(int(m.part_t.max()) + 1)
                                   if p not in WIRE and H.part_top_area(m, p, ny_min=0.75) >= 0.1)
    out = []
    for p in m._sz_kepler_panels:
        tops = m.tops(v, parts=(p,), ny_min=0.75) & (m.NYF >= 0.75)
        for region, heights in m.regions(tops, v, close=0.0, min_area=0.02):
            out.append(m.blanket(region, heights, v, over=0.01, shoulder=0.25,
                                 smooth=0.04, fill=0.01, bury=False))
    return H.join(out)
