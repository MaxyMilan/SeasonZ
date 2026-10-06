"""rock_wallh3: a horizontal rock wall with stepped ledges.

(Opus, 6 Oct, b1) the caps on the ledges tore open (a dark rift in a cap) and showed flat facets at v4-v7. A short
lip (30% of the depth + 1 cm, sinking 1.6 cm at most)."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05)
