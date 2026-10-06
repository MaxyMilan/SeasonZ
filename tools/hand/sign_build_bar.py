"""sign_build_bar: a big bar sign board on a wall bracket.

(Opus, 6 Oct, c37) the board's top cap flowed along its side onto the lower bracket arm (v6-v7). Every part with 1 dm2 of top or more its own field that spills onto no other part
(H.part_fields), a short lip (30% of the depth + 1 cm, sinking 1.6 cm)."""
import snow_hand as H


def build(m, v):
    g = H.part_fields(m, 0.01)
    return H.consts(m, v, fn=lambda m_, v_: H.separate(m_, v_, g), A7_OVL=0.3, A7_LIPDROP=0.05)

