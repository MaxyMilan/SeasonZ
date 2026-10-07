"""barn_metal_big: a large metal barn with two roof slopes and a separate narrow ridge member.

(Astra Euler, 7 Oct 2026, b1) review could not distinguish the dark ridge seam from a cap split.
Source roof parts 863/864 stop at x=0.8630/0.2659; ridge part 848 spans x=0.4956..0.6456,
leaving genuine 21.7/23.0 cm openings. Separate surface blankets retain these openings while smoothing
the former serrated deep edges. Thin ladder/fitting parts let snow through and steep faces stay bare.
"""
import snow_hand as H


def build(m, v):
    if not hasattr(m, '_sz_euler_parts'):
        m._sz_euler_parts = tuple(p for p in range(int(m.part_t.max()) + 1)
                                 if H.part_top_area(m, p, 0.7) >= 0.1)
        H.through(m, [p for p in range(int(m.part_t.max()) + 1) if p not in m._sz_euler_parts])
    tops = m.tops(v, ny_min=0.7, slope=False) & (m.NYF >= 0.7)
    return m.cover(v, tops, over=0.005, smooth=0.04, bury=False)
