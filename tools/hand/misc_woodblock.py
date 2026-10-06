"""misc_woodblock: a short thick log standing on end (a chopping block).

(Opus, 6 Oct) its deep pillow rolled out far over the sawn edge as a mushroom by v5-v7 (r10). The lip may hang over
the edge by at most 30% of the depth (+1 cm; 8 cm at v7)."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, A7_OVL=0.3)
