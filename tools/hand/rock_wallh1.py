"""rock_wallh1: a long horizontal rock wall (placed over 2000 times).

(Opus, 6 Oct) built on its own: with other rocks in parallel it ran out of memory (b1). Like the other rock walls
now: a short lip (30% of the depth + 1 cm, sinking 1.6 cm at most), no cornices with pointed drips."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05)
