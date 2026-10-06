"""wall_vilvar1_6.

Square posts 0 and 30 get shallow cushions. Flat rails 1 and 2 get beam caps.
Pickets 3..29 have narrow pointed roofs (most slopes over 50 degrees):
leave these sharp tips bare, including the tiny flat fragment on part 3.
No snow on upright faces; separated planks remain separate.
"""
import snow_hand as H
from snow_parts import cushion

RAILS = [1,2]
TOPS = [0,30]


def build(m, v):
    out = [m.beam(p, v) for p in RAILS]
    out.extend(cushion(m, p, v) for p in TOPS)

    return H.join(out)
