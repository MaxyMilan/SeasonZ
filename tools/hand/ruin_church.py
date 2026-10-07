"""ruin_church: a ruined church with broken masonry crowns and exposed roof timbers.

(Astra Euler, 7 Oct 2026, b1) the volumetric cap bridged the empty roof as upright sails and draped long
sheets down broken wall faces. Each substantial upward-facing part receives its own supported blanket,
with no gap closing between broken beams. Steep faces and tiny fittings remain bare, and short lips
retain the open structure without burying down the masonry.
"""
import snow_hand as H


def build(m, v):
    if not hasattr(m, '_sz_euler_parts'):
        m._sz_euler_parts = tuple(p for p in range(int(m.part_t.max()) + 1)
                                 if H.part_top_area(m, p, 0.65) >= 0.03)
        H.through(m, [p for p in range(int(m.part_t.max()) + 1) if p not in m._sz_euler_parts])
    out = []
    for p in m._sz_euler_parts:
        tops = m.tops(v, parts=(p,), ny_min=0.65, slope=False) & (m.NYF >= 0.65)
        for region, heights in m.regions(tops, v, close=0.0, min_area=0.006):
            out.append(m.blanket(region, heights, v, over=0.005, smooth=0.03,
                                 fill=0.01, spacing=0.15, shoulder=0.25, bury=False))
    return H.join(out)
