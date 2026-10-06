"""misc_range_roof: a shooting range shelter, a corrugated roof (part 33) on posts over a shooting bench (7, 15).

(Opus, 6 Oct, c35) the bench and the rails under the roof's edge carried beads of snow at v7, and the edge beam (16)
hung a lump below the lip. Only the roof holds snow, with a short lip."""
import snow_hand as H


def build(m, v):
    m._sz_parts = (33,)
    return H.consts(m, v, A7_OVL=0.4, A7_LIPDROP=0.05)
