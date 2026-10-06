"""cemetery_tombstone8_damaged: a broken tombstone: the standing stump on its plinth and the broken-off slab lying beside it.

(Opus, 6 Oct, r10, c37) the v7 pillow rolled over the slanted break of the stump like a sausage and the lying
slab (within 25 cm of the ground) stayed bare. The slab holds snow too, the lip is short (30% of the depth + 1 cm,
sinking 1.6 cm).
(c43) the stump's narrow slanted break (about 15 cm) grew a tall dome at v4-v7: tops narrower than 18 cm get a
ridge or nothing."""
import snow_hand as H


def build(m, v):
    if not getattr(m, '_sz_low', False):
        # its floor lies within 25 cm of the ground, which tops() leaves to the terrain's cover
        m.ground -= 0.22
        m._sz_low = True
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05, A7_THIN=0.18)
