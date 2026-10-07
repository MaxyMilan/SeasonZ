"""houseblock_3f_corner2: a three-storey corner block of flats, an L of steep gabled roofs with chimneys.

(Opus, 6 Oct, b1) v4-v7 clean; at v1 and v2 the thin layer broke into torn patches and dark holes along the gable and
the valley (v3 closed, a small crease at the gable end). v1 and v2 show the v3 cap.

(Astra Laplace, 7 Oct 2026, b1) measured thin rooftop rods and their tip discs
grew isolated polygonal knobs. Those fittings now let snow through; surface blankets preserve the broad roof coverage after the fine volume exceeded eight minutes without a single completed depth."""
import snow_hand as H


def build(m, v):
    H.through(m, (7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24))
    return H.auto(m, max(v, 3), over=0.01, smooth=0.04, bury=False)
