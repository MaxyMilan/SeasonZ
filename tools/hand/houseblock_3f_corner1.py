"""houseblock_3f_corner1: a three-storey corner block of flats, an L of steep gabled roofs with chimneys.

(Opus, 6 Oct, b1) v4-v7 clean; at v1 and v2 the thin layer broke into torn patches and dark holes along the gable and
the valley (v3 closed, a small crease at the gable end). v1 and v2 show the v3 cap."""
import snow_hand as H


def build(m, v):
    return H.big_tops(m, max(v, 3), 0.01)
