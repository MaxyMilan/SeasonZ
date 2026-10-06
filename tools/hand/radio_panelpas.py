"""radio_panelpas: a radio panel cabinet with two lids on top.

(Opus, 6 Oct, c37) a sharp flap and a ragged seam where the two lid caps met (v7). Parts with 1 dm2 of top or more,
a short lip (30% of the depth + 1 cm, sinking 1.6 cm)."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, fn=lambda m_, v_: H.big_tops(m_, v_, 0.01), A7_OVL=0.3, A7_LIPDROP=0.05)

