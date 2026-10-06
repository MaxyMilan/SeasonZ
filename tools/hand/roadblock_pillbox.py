"""roadblock_pillbox: a pillbox of stacked concrete blocks with broken, tilted stacks of blocks at both ends.

(Opus, 6 Oct, c35) at v7 the snow of the tilted blocks at the ends merged into one sheet draped down the whole stack
(a vertical curtain) and tongues ran down the broken wall heads. Only parts with at least 10 dm2 of top hold snow (the
wall caps, the big blocks), with a short lip (30% of the depth + 1 cm, sinking 1.6 cm at most)."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, fn=lambda m_, v_: H.big_tops(m_, v_, 0.10), A7_OVL=0.3, A7_LIPDROP=0.05)
