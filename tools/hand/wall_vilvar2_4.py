"""wall_vilvar2_4: part 0 is the square post; parts 5 and 6 are flat rails.

The remaining 24 vertical planks have thin gently slanted cut tops.
Rails get beam caps with shelter from the upper rail accounted for. The
post and each plank get their own shallow, width-limited small-top cushion.
No joining across board gaps and no snow on the upright faces.
"""
import snow_hand as H
from snow_parts import cushion

RAILS = (5, 6)
TOPS = [0,1,2,3,4,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26]


def build(m, v):
    return H.join([m.beam(p, v) for p in RAILS] +
                  [cushion(m, p, v) for p in TOPS])
