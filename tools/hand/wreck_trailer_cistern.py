"""wreck_trailer_cistern: a wrecked tanker trailer, a horizontal cistern (a cylinder) on a two-axle chassis.

(Opus, 6 Oct, r10, c37) the cistern's v7 pillow hung down its curved flanks and over its ends in large lobes, as on
tank_small_gas. The wreck route (parts with 1 dm2 of top, short lip, thin strips ridges) up to the fourth depth: a
round tank sheds what falls after that."""
import snow_hand as H


def build(m, v):
    return H.consts(m, min(v, 4), fn=lambda m_, v_: H.big_tops(m_, v_, 0.01), A7_OVL=0.3, A7_LIPDROP=0.05, A7_THIN=0.07)
