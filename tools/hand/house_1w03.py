"""house_1w03: a long one-storey wooden house with an annex.

(Opus, 6 Oct, b1) at v1-v2 the snow tore open along the eave by the downpipe (a long dark slit and a loose
flap). Rebuilt with the short lip and thin strips as ridges."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, fn=lambda m_, v_: H.big_tops(m_, v_, 0.01), A7_OVL=0.3, A7_LIPDROP=0.05, A7_THIN=0.07)
