"""misc_obstacle_bridge: an obstacle course bridge: a plank walkway on posts with a ramp down to the ground at each end.

(Opus, 6 Oct, c37) the lower end of the ramp stayed bare at every depth (within 25 cm of the ground, which tops()
leaves to the terrain's cover) while the slope above it was white: the snow stopped halfway down the tread. The
whole tread holds snow, with a short lip (30% of the depth + 1 cm, sinking 1.6 cm)."""
import snow_hand as H


def build(m, v):
    if not getattr(m, '_sz_low', False):
        m.ground -= 0.22
        m._sz_low = True
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05)

