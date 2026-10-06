"""misc_seesaw: a playground seesaw, a beam on a pivot with a seat (7, 8) and handle at each end.

(Opus, 6 Oct, r10, c37) the low seat (7) lies within 25 cm of the ground, which tops() leaves to the terrain's
cover: it stayed bare at every depth while the raised seat got its pad. Both seats hold snow (the ground limit moved
down), with a short lip (30% of the depth + 1 cm, sinking 1.6 cm)."""
import snow_hand as H


def build(m, v):
    if not getattr(m, '_sz_low', False):
        m.ground -= 0.22
        m._sz_low = True
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05)
