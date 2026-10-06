"""garbage_pile2: a heap of rubbish bags and boxes on broken pallets.

(Opus, 6 Oct, c37, c39) the v7 pillow on the bags hung thick fingers down between the pallet slats at its foot and a
ball formed on the front bag; only big tops and a short lip did not help. The pallets lie within 25 cm of the ground,
which tops() leaves to the terrain's cover: the heap is treated as the dirt piles are (rough, its foot included), so
the pillow runs out over the snowed-in pallets instead of hanging into their gaps."""
import snow_hand as H


def build(m, v):
    m.rough = True
    if not getattr(m, '_sz_low', False):
        m.ground -= 0.22
        m._sz_low = True
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05, A7_CREVICE=0.15)
