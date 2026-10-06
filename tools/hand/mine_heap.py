"""mine_heap: a big conical spoil heap (loose earth and rock) by a mine.

(Opus, 6 Oct, b1) the cap left dark bare patches on the steep flanks and a row of teeth along the foot. A heap of
earth holds snow like rock and the ground: the rough treatment (the layer thins out before the slope limit, cracks
bridged), the foot included (no bare ring between the cap and the white ground), a coarse lattice (the heap is
big: 11.8 GB on the fine one)."""
import snow_hand as H


def build(m, v):
    m.rough = True
    if not getattr(m, '_sz_low', False):
        m.ground -= 0.22
        m._sz_low = True
    return H.consts(m, v, A7_CREVICE=0.15, A7_GRIDMAX=0.05, A7_GYMIN=0.025)
