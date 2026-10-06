"""village_healthcare: the village clinic, a long log building with a pitched roof, cross gable and porches.

(Opus, 6 Oct, b1) v3-v7 clean; at v1 and v2 the thin layer broke on the roof's panel steps into rectangular bare
notches and loose flaps. v1 and v2 show the v3 cap."""
import snow_hand as H


def build(m, v):
    return H.big_tops(m, max(v, 3), 0.01)
