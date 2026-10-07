"""coalplant_conveyor: a long enclosed inclined conveyor on slender lattice supports.

(Astra Euler, 7 Oct 2026, b1) v1 had repeated roof gaps and triangular shards, and deep snow folded over
the end as angular flaps. The roof panels, ridge flashing and exposed belt-end surface carry a continuous
surface blanket from the first depth. Thin support bars let snow through; short lips leave end faces clear.
"""
import snow_hand as H


def build(m, v):
    H.through(m, [p for p in range(int(m.part_t.max()) + 1) if p not in (0, 1, 32, 179, 243)])
    tops = m.tops(v, ny_min=0.65, slope=False) & (m.NYF >= 0.65)
    return m.cover(v, tops, over=0.006, smooth=0.04, bury=False)
