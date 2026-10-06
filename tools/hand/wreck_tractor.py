"""wreck_tractor: a wrecked tractor: cab, bonnet, big rear wheels under mudguards.

(Opus, 6 Oct) r10/c37: the mudguards' pillows ran down the curved guards onto the tyre tops as thick lobes (c48
separate fields: crashed on a part without top). c53 (thinning on curved panels) changed nothing; c58 (the wreck
route's H.ledges) left the lobes: the big tyres count as major surfaces. c54a: the crown rule (cells within 10 cm
of the highest top within 35 cm in plan) strips the tyre tops under the guards and keeps the guards' and cab's
caps clean."""
import snow_hand as H


def build(m, v):
    return H.wreck(m, v, CROWN=[0.10, 0.35], LEDGES=None)
