"""pipe_small_broken: a broken run of small pipe on a support, one end open.

(Opus, 6 Oct, m1, c37) at v7 a tongue of snow hung over the open end onto the support. A short lip: 10% of the
depth (+1 cm), sinking 1 cm at most."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, A7_OVL=0.1, A7_LIPDROP=0.03)
