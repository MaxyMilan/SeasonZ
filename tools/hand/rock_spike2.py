"""rock_spike2: a rock spike, a cluster of steep blocks.

(Opus, 6 Oct, b1) at v7 broad tongues of snow hung over the steep flanks with angular folds. A short lip (30% of
the depth + 1 cm, sinking 1.6 cm at most), as the other rocks rebuilt on 6 Oct."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05)
