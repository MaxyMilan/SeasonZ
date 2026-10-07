"""mil_reinforcedtank1: a large reinforced storage dome with a door, vents and a ladder.

(Astra Faraday, 7 Oct 2026, b1) the volumetric roof formed triangular fans and broad bare patches at light depth,
then hanging flaps above the door and vents. The dome receives a continuous surface blanket on its exposed
slopes; substantial vent and door tops receive separate short blankets. Thin ladder/fittings let snow through,
and no blanket bridges from the dome down to the separate vent pieces or buries into steep wall faces.
"""
import snow_hand as H


def build(m, v):
    if not hasattr(m, '_sz_faraday_panels'):
        m._sz_faraday_panels = tuple(p for p in range(int(m.part_t.max()) + 1)
                                    if H.part_top_area(m, p, ny_min=0.8) >= 0.1)
        H.through(m, [p for p in range(int(m.part_t.max()) + 1) if p not in m._sz_faraday_panels])
    out = []
    for p in m._sz_faraday_panels:
        limit = 0.55 if p == 2 else 0.8
        tops = m.tops(v, parts=(p,), ny_min=limit) & (m.NYF >= limit)
        for region, heights in m.regions(tops, v, close=0.0, min_area=0.01):
            out.append(m.blanket(region, heights, v, over=0.01, shoulder=0.25,
                                 smooth=0.06 if p == 2 else 0.025, fill=0.01, bury=False))
    return H.join(out)
