"""rubble_concrete2: a heap of concrete rubble and slabs.

(Opus, 6 Oct, m1, c37) the broad shallow parts round the heap (within 25 cm of the ground) stayed bare round the
central pillows. Rubble holds snow as the dirt piles: rough, its foot included, crevices bridged up to 15 cm."""
import snow_hand as H


def build(m, v):
    m.rough = True
    if not getattr(m, '_sz_low', False):
        # its lowest broad tops lie within 25 cm of the ground, which tops() leaves to the terrain's cover
        m.ground -= 0.22
        m._sz_low = True
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05, A7_CREVICE=0.15)
