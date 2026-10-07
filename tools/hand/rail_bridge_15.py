"""rail_bridge_15: a railway bridge with ballast, sleepers, twin rails and a side walkway.

(Astra Euler, 7 Oct 2026, b1) the thin volumetric layer made sharp tents and open gaps across the track bed.
Surface blankets follow the exposed ballast, sleepers, rail crowns and walkway independently across real
height steps. Thin fittings let snow through. A small smoothed shoulder gives continuous v1 coverage without
the old pointed wedges; rounded short edges leave vertical sides clear.
"""
import snow_hand as H

PANELS = (46,) + tuple(range(236, 246)) + tuple(range(302, 306)) + (418, 419, 459)


def build(m, v):
    H.through(m, [p for p in range(int(m.part_t.max()) + 1) if p not in PANELS])
    tops = m.tops(v, ny_min=0.8, slope=False) & (m.NYF >= 0.8)
    return m.cover(v, tops, over=0.006, smooth=0.04, bury=False)
