"""monument_war2: a war memorial obelisk on a stepped plinth on a broad square base slab.

(Opus, 6 Oct, m1, c37) the broad base slab (within 25 cm of the ground) stayed bare while the plinth's steps and the
obelisk's top carried snow. The slab holds snow too, with a short lip."""
import snow_hand as H


def build(m, v):
    if not getattr(m, '_sz_low', False):
        # its lowest broad tops lie within 25 cm of the ground, which tops() leaves to the terrain's cover
        m.ground -= 0.22
        m._sz_low = True
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05)
