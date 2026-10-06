"""mil_guardhouse2: a checkpoint hut with a flat roof (164, 165) and a two-leaf barrier gate (18, 42 with their rails
and braces 29, 30, 61, 62 and fittings) beside it.

(Opus, 6 Oct, m1, c39) the gate's thin top rail grew a lumpy roll and a brace a thin vertical sheet. The gate holds
no snow; every other part with at least 1 dm2 of top (roofs, parapets, posts) does."""
import snow_hand as H

GATE = {18, 42, 23, 24, 26, 29, 30, 31, 37, 55, 56, 57, 58, 61, 62, 63}


def build(m, v):
    if not hasattr(m, '_sz_rails'):
        n = int(m.part_t.max()) + 1
        m._sz_parts = tuple(p for p in range(n) if p not in GATE and H.part_top_area(m, p) >= 0.01)
        m._sz_rails = ([], [])
    return H.hybrid(m, v)
