"""wall_wood3_4.

Flat 11 mm rails 4 and 5 receive thin beam caps (4.8..6.6 mm);
narrow cut tops 6..40 receive cushions. The broad masonry post coping (0)
and wall coping (3) collect continuous cushions from their real surfaces.
The coping is cut against the actual warped pickets; it does not borrow
upright-face heights from the raster. Corners seat on the real bevels.
The supporting masonry below these caps (1,2) has no independent snow.
No snow on upright faces; separated planks remain separate.
"""
import snow_hand as H
from snow_parts import cushion, coping

RAILS = [4,5]
TOPS = [6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40]


def build(m, v):
    out = [m.beam(p, v, depth=(0.0045 + 0.0003*v)/m.thick(v), inset=0.001) for p in RAILS]
    out.extend(cushion(m, p, v) for p in TOPS)
    out.append(coping(m,0,v,smooth=True))
    out.append(coping(m,3,v,cutters=TOPS,smooth=True))
    return H.join(out)
