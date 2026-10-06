"""wall_wood1_5.

Parts 0 and 1 are flat narrow rails; 2..33 are thin upright pickets.
Parts 34 and 35 are slender supports with small square tops.
The x=1.2..1.45 top regression is handled as its actual cut quad:
no raster ridge and no depth-driven tent in v5..v7.
Each rail uses shelter-aware beam(). The cut-top cushions use the real
support width: a 2 cm plank holds only a few millimetres at maximum depth.
Open gaps stay open; vertical faces hold none.
"""
import snow_hand as H
from snow_parts import cushion

RAILS = [0,1]
TOPS = [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35]


def build(m, v):
    return H.join([m.beam(p, v) for p in RAILS] +
                  [cushion(m, p, v) for p in TOPS])
