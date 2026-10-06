"""boat_small2: a small boat lying on the ground under a tarpaulin, a raised stern fitting.

(Opus, 6 Oct, r10, c37) the v7 pillow hung down both sides of the stern fitting. A short lip (30% of the depth
+ 1 cm, sinking 1.6 cm at most)."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05)
