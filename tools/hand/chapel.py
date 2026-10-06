"""chapel: a small Orthodox wayside chapel: octagonal drum with a ring of arched gables (kokoshniki), a tent roof and an onion dome.

(Opus, 6 Oct, c37) the arched gables' caps rolled over as thick lobes that ran down the arches and joined the
higher and lower roof edges (v4-v7). Parts with 1 dm2 of top or more, a short lip (30% of the depth + 1 cm, sinking
1.6 cm)."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, fn=lambda m_, v_: H.big_tops(m_, v_, 0.01), A7_OVL=0.3, A7_LIPDROP=0.05)

