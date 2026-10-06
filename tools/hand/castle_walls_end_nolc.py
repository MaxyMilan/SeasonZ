"""castle_walls_end_nolc: the broken end of the castle's curtain wall (a stepped break, stones sticking out).

(Opus, 6 Oct, c37) the top pillow ran down the broken side and joined the lower protruding stones (v7). The
castle family's crown rule: only cells within 50 cm of the highest top within a metre in plan, a short lip."""
import snow_hand as H


def build(m, v):
    H.crown(m, 0.5, 1.0)
    return H.consts(m, v, fn=lambda m_, v_: H.big_tops(m_, v_, 0.01), A7_OVL=0.3, A7_LIPDROP=0.05)

