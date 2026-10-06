"""misc_concreteblock1_end: the sloped end block of a concrete barrier: a ridge on a broad low foot.

(Opus, 6 Oct, r10, c37) the broad foot (within 25 cm of the ground) stayed bare at every depth under a thick
ridge cap. The foot holds snow too, with a short lip."""
import snow_hand as H


def build(m, v):
    if not getattr(m, '_sz_low', False):
        # its lowest broad tops lie within 25 cm of the ground, which tops() leaves to the terrain's cover
        m.ground -= 0.22
        m._sz_low = True
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05)
