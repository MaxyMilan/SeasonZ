"""dam_concrete_20_floodgate: a concrete dam gate with an upper walkway, raised coping and railing.

(Astra Kepler, 7 Oct 2026, b1) the volumetric thin layer left long triangular gaps in the broad coping near
railing brackets. Blanket each substantial concrete panel separately at its actual height, without closing
gaps across raised members. The railing keeps narrow log/beam ridges and post tops keep small cushions.
Short supported lips grow through all seven depths without filling the gate opening.
"""
import snow_hand as H

PANELS = (2, 3, 14, 15, 16, 17)
POSTS = tuple(range(4, 14))
RAILS = (23, 24, 25, 36)


def build(m, v):
    out = []
    for p in RAILS:
        if m.is_log(p):
            out.append(m.log(p, v))
        elif m.is_beam(p):
            out.append(m.beam(p, v))
        else:
            out.append(m.cover(v, m.tops(v, parts=(p,), ny_min=0.8),
                               over=0.005, smooth=0.025, bury=False))
    for p in PANELS + POSTS:
        tops = m.tops(v, parts=(p,), ny_min=0.8) & (m.NYF >= 0.8)
        for region, heights in m.regions(tops, v, close=0.0, min_area=0.015):
            out.append(m.blanket(region, heights, v, over=0.015, shoulder=0.25,
                                 smooth=0.04, fill=0.01, bury=False))
    return H.join(out)
