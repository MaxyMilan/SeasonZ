"""mine_rail: a straight mine track: rails on sleepers in a low gravel bed.

(Opus, 6 Oct, m1, c37) only the rails and sleepers held snow, as fat separate pillows; the bed stayed bare (within
25 cm of the ground). Under snow a track is a white band with the rails showing: the bed holds snow too, the lip is
short (30% of the depth + 1 cm, sinking 1.6 cm)."""
import snow_hand as H


def build(m, v):
    if not getattr(m, '_sz_low', False):
        # its floor lies within 25 cm of the ground, which tops() leaves to the terrain's cover
        m.ground -= 0.22
        m._sz_low = True
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05)
