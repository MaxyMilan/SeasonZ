"""pipe_small_20m: a 20 m run of small pipe on low supports, open at both ends.

(Opus, 6 Oct, b1) at v7 the pipe's ridge curled far down over both open ends as thick tongues. A short lip: 10%
of the depth (+1 cm), sinking 1 cm at most."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, A7_OVL=0.1, A7_LIPDROP=0.03)
