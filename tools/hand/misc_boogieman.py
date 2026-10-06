"""misc_boogieman: a scarecrow: a hat on a stick figure with outstretched arms.

(Opus, 6 Oct, r10, c37) the hat's pillow rolled out far past the brim (a mushroom). A short lip: 15% of the depth
(+1 cm), sinking 1.6 cm at most."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, A7_OVL=0.15, A7_LIPDROP=0.05)
