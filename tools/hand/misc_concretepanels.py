"""misc_concretepanels: a stack of concrete wall panels on timber spacers.

(Opus, 6 Oct, c37) the v7 pillow sagged over the corners of the stack and down the slab faces. A short lip: 30% of
the depth (+1 cm), sinking 1.6 cm at most below the edge."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05)
