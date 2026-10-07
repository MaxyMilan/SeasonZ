"""office_municipal1: a municipal building with a parapet roof, raised tower and slender spire.

(Astra Euler, 7 Oct 2026, b1) huge volumetric fans and floating sheets left the broad roof open.
Surface blankets follow exposed roof planes and masonry ledges, keeping distinct height steps separate.
Thin ornamental rods and the summit emblem let snow through. Steep spire and wall faces stay bare;
short rounded lips retain the parapet openings and do not bury down the facade.
"""
import snow_hand as H


def build(m, v):
    if not hasattr(m, '_sz_euler_parts'):
        m._sz_euler_parts = tuple(p for p in range(int(m.part_t.max()) + 1)
                                 if p != 265 and H.part_top_area(m, p, 0.55) >= 0.03)
        H.through(m, [p for p in range(int(m.part_t.max()) + 1) if p not in m._sz_euler_parts])
    tops = m.tops(v, ny_min=0.55, slope=False) & (m.NYF >= 0.55)
    return m.cover(v, tops, over=0.008, smooth=0.05, bury=False)
