"""cemetery_grave4: a grave mound of earth, about 40 cm high, with a flat crown.

(Opus, 6 Oct, c37) only the crown held snow: the shoulders lie within 25 cm of the ground, which tops() leaves to the
terrain's cover, and are rough facets. Earth holds snow like rock: the rough treatment of the dirt piles, the foot
included (no bare brown ring between the cap and the white ground)."""
import snow_hand as H


def build(m, v):
    m.rough = True
    if not getattr(m, '_sz_low', False):
        m.ground -= 0.22
        m._sz_low = True
    return H.consts(m, v, A7_CREVICE=0.15)
