"""misc_bench4: a park bench of curved slats (seat 10, 15-19; back 11-14, 11 the top) on two cast iron frames (0-9).

Snow on the seat and on the two top slats of the back (11, 12); the lower back slats (13, 14) stand right at the slope
limit and held lumpy patches, so they stay bare; the slat chamfers hold none. The frames hold none (crumbs)."""
import snow_hand as H

SLATS = [10, 11, 12, 15, 16, 17, 18, 19]


def build(m, v):
    out = []
    for R, Zc in m.regions(m.tops(v, parts=SLATS, steep=0.6), v):
        out.append(m.blanket(R, Zc, v))
    return H.join(out)

