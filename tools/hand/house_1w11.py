"""house_1w11: a wooden house with a pitched roof, chimney and antenna.

(Opus, 6 Oct, c37) a dark seam split the snow along the ridge at v1-v4: the ridge board (under 1 dm2 of top) was
left out by the building default. Every part with at least 0.1 dm2 of top holds snow, thin strips ridges."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, fn=lambda m_, v_: H.big_tops(m_, v_, 0.001), A7_THIN=0.07)
