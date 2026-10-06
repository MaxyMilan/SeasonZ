"""stone1: a large flat boulder with a deep hollow in its top.

(Opus, 6 Oct) the hollow showed as a dark hole in the cap at v1-v4 (r10); snow fills a hollow first. Crevices up to
30 cm are bridged at their rim's height from the first depth on (A7_CREVICE)."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, A7_CREVICE=0.3)
