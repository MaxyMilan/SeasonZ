"""wall_wood1d_5.

Parts 0 and 1 are flat rails; 17 and 18 are slender posts.
Intact/upper remaining pickets get shallow cut-top cushions.
Broken stumps 21 and 23 have steep splinter faces (normal y <= 0.57),
so they hold no separate snow cushion. No snow on broken vertical faces.
Each rail uses shelter-aware beam(). The cut-top cushions use the real
support width: a 2 cm plank holds only a few millimetres at maximum depth.
Open gaps stay open; vertical faces hold none.
"""
import snow_hand as H
from snow_parts import cushion

RAILS = [0,1]
TOPS = [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,22]


def build(m, v):
    return H.join([m.beam(p, v) for p in RAILS] +
                  [cushion(m, p, v) for p in TOPS])
