"""rock_monolith1: a large flat-topped rock monolith with cliff sides and ledges.

(Opus, 6 Oct, b1) at v7 the cornice over the cliff tops hung pointed drips and a long tongue down the rock face,
sharp fins on the side ledges at v1. A short lip (30% of the depth + 1 cm, sinking 1.6 cm at most)."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05)
