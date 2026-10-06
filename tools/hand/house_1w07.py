"""house_1w07: a wooden house with a cross gable.

(Opus, 6 Oct, b1) at v1-v2 long open seams and triangular flaps over the main roof. Rebuilt with the short lip and
thin strips as ridges."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, fn=lambda m_, v_: H.big_tops(m_, v_, 0.01), A7_OVL=0.3, A7_LIPDROP=0.05, A7_THIN=0.07)
