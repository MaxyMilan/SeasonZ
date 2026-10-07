"""church3: an ornate church with intersecting pitched roofs, a broad dome and three steep cupolas.

(Astra Huygens, 7 Oct 2026, b1) the coarse volumetric thin layer split into broad bare fans and shards.
Supported surface blankets follow the roof slopes and domes. Thin summit crosses let snow through.
The steep cupolas use the permitted v3 minimum at light depths; short rounded lips keep walls clear.
"""
import snow_hand as H

CROSSES = tuple(p for p in range(118, 134) if p not in (121, 123, 128, 133))


def build(m, v):
    H.through(m, CROSSES)
    vv = max(v, 3)
    tops = m.tops(vv, ny_min=0.35, slope=False) & (m.NYF >= 0.35)
    return m.cover(vv, tops, over=0.015, smooth=0.05, fill=0.02,
                   shoulder=0.3, bury=False)
