"""barn_brick2: a brick barn with stepped gable walls rising above the roof.

(Opus, 6 Oct, b1) at the roof's corners the gable parapet's cap and the roof's lip met in pointed flaps hanging
down the gable. A short lip (30% of the depth + 1 cm, sinking 1.6 cm), thin strips ridges.
(c43) with thin strips as ridges the v1 cap of the tiled roof broke up into a bare roof with a twisted sheet: no
thin-strip handling on this roof."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, fn=lambda m_, v_: H.big_tops(m_, v_, 0.01), A7_OVL=0.3, A7_LIPDROP=0.05, A7_THIN=0.0)
