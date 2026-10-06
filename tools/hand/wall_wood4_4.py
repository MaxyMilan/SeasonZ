"""wall_wood4_4.

The extremely thin rails 0,1 are 4 mm plates and only hold trace snow
(up to 1.2 mm); the lower rail is directly sheltered by the upper one.
Flat pickets 2,5,8,11,14,17,20,23,26,29,32 get tiny cushions.
The alternating slanted tips (other parts 3..31) are too steep and thin.
Masonry base ledge 33 and column coping 34 collect broad smooth cushions
sampled on their original surfaces, with rounded seated edges.
Column sides 35 receive none.
No snow on upright faces; separated planks remain separate.
"""
import snow_hand as H
from snow_parts import cushion, coping

RAILS = [0,1]
TOPS = [2,5,8,11,14,17,20,23,26,29,32]


def build(m, v):
    out = [cushion(m, p, v, min_width=0.003) for p in RAILS]
    out.extend(cushion(m, p, v) for p in TOPS)
    out.extend(coping(m,p,v) for p in (33,34))
    return H.join(out)
