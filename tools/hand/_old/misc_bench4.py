"""misc_bench4: a park bench of curved slats (seat 10, 16-19; the curve 15, 14; back 13-11, 11 the top) on two cast
iron frames (0-9).

Snow on the seat (10, 16-19) and on the two top slats of the back (11, 12, one ridge in deep snow). The curve into the
back (15, 14 at about 46 degrees, 13) holds none of its own: the seat's snow buries it as it deepens, its top running
on level until the back comes out of it. The slat chamfers hold none; the frames hold none (crumbs)."""
import snow_hand as H

SLATS = [10, 11, 12, 16, 17, 18, 19]


def build(m, v):
    out = []
    for R, Zc in m.regions(m.tops(v, parts=SLATS, steep=0.6), v):
        out.append(m.blanket(R, Zc, v))
    return H.join(out)

