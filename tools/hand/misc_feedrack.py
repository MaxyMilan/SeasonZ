"""misc_feedrack: a hay rack with a pitched roof of boards and raised battens.

(Opus, 6 Oct) the band parted the battens from the boards between them and the cap showed hard terraces along each
batten at v4-v7 (r10). Without the band the roof's snow lies over the battens as one pillow."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, A7_BANDH=0.)
