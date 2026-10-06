"""misc_gcontainer_big: a large open skip full of rubbish; part 0 is the chassis with the lifting A-frames at both
ends, the rim (3-5, 11, 12) and the load (13-23) hold the snow.

(Opus, 6 Oct) the A-frame (part 0) carried a thick sausage of snow down its slanted arms and the load's pillow hung
over the rim onto it (m1). Part 0 holds none and receives no spill."""
import snow_hand as H


def build(m, v):
    m._sz_block = (0,)
    return H.hybrid(m, v)
