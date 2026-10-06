"""misc_woodreserve: a firewood store: a board roof (part 8) on posts over a stack of split logs.

(Opus, 6 Oct) the roof's front lip hung down in lumps in front of the logs (r10, c32). Only the roof holds snow; its
lip overhangs at most 30% of the depth (+1 cm) and sinks 1.6 cm at most below the roof's edge."""
import snow_hand as H


def build(m, v):
    m._sz_parts = (8,)
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05)
