"""misc_woodtable_indoor: a plank table (top boards 2, 3, 6, 7, 8, 32 cm up) between two benches of two boards each
(0-1 and 4-5, about 30 cm lower); battens and legs (9-18) hold no snow.

(Opus, 6 Oct) in one field the table top's v7 pillow flowed down onto the benches (marshmallow, r10). Three separate
caps (H.separate); each blocks the others' boards."""
import snow_hand as H

TOP = (2, 3, 6, 7, 8)


def build(m, v):
    return H.separate(m, v, [(TOP, (0, 1, 4, 5)), ((0, 1), TOP), ((4, 5), TOP)])
