"""ship_big_backa: the broken stern of a cargo ship, with open decks, crane frame and rigging.

(Astra Huygens, 7 Oct 2026, b1) large snow fans bridged broken deck openings and wrapped the steep
frame and rigging as strips. Thin cables and inclined rod assemblies let snow through. Only measured
broad upward surfaces carry separate short-edged blankets: exposed deck pieces, stairs and platforms.
Nearly vertical hull and frame faces remain clear, and real openings between deck pieces stay open.
"""
import snow_hand as H

WIRE = (285, 286, 287, 454, 468, 483, 491)


def build(m, v):
    if not hasattr(m, '_sz_huygens_panels'):
        m._sz_huygens_panels = tuple(p for p in range(int(m.part_t.max()) + 1)
                                    if p not in WIRE and H.part_top_area(m, p, 0.8) >= 0.1)
        H.through(m, [p for p in range(int(m.part_t.max()) + 1) if p not in m._sz_huygens_panels])
    out = []
    for p in m._sz_huygens_panels:
        tops = m.tops(v, parts=(p,), ny_min=0.8) & (m.NYF >= 0.8)
        for region, heights in m.regions(tops, v, close=0.0, min_area=0.02):
            out.append(m.blanket(region, heights, v, over=0.008, shoulder=0.25,
                                 smooth=0.04, fill=0.01, bury=False))
    return H.join(out)
