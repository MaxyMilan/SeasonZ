"""boat_small1: a small rowing boat lying on the ground, open, three thwarts.

(Opus, 6 Oct, c37) the open floor stayed bare at every depth (within 25 cm of the ground) and the gunwale cap
grew teeth on its inside. The floor holds snow too, the lip is short (30% of the depth + 1 cm, sinking 1.6 cm)."""
import snow_hand as H


def build(m, v):
    if not getattr(m, '_sz_low', False):
        # its floor lies within 25 cm of the ground, which tops() leaves to the terrain's cover
        m.ground -= 0.22
        m._sz_low = True
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05)
