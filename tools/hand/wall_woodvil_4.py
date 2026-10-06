"""wall_woodvil_4.

Part 0 is the square post; 4 and 5 are the two thin flat rails.
The other seventeen planks are spaced, with slanted but nearly level top cuts.
Each rail uses shelter-aware beam(). The cut-top cushions use the real
support width: a 2 cm plank holds only a few millimetres at maximum depth.
Open gaps stay open; vertical faces hold none.
"""
import snow_hand as H
from snow_parts import cushion

RAILS = [4,5]
TOPS = [0,1,2,3,6,7,8,9,10,11,12,13,14,15,16,17,18,19]


def build(m, v):
    return H.join([m.beam(p, v) for p in RAILS] +
                  [cushion(m, p, v) for p in TOPS])
