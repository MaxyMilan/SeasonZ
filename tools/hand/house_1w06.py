"""house_1w06: a one-and-a-half-storey wooden house with a lean-to on posts.

(Opus, 6 Oct, b1) at v7 angular lobes hung under the eaves and a fringe under the lean-to's low edge. A short lip
(30% of the depth + 1 cm, sinking 1.6 cm), thin strips ridges."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, fn=lambda m_, v_: H.big_tops(m_, v_, 0.01), A7_OVL=0.3, A7_LIPDROP=0.05, A7_THIN=0.07)
