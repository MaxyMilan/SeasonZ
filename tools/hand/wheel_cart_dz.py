"""wheel_cart_dz: a wheelbarrow, a steel tray on a tube frame with two handles.

(Opus, 6 Oct, c37) the v7 fill of the tray rolled over its front rim as a hanging sheet. A short lip: 30% of the
depth (+1 cm), sinking 1.6 cm at most below the rim."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05)
