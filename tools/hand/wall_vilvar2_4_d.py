"""wall_vilvar2_4_d.

Broken flat rail segments 4,11,12,13 get separate beam caps to their true ends.
Square post 0 and surviving cut-top boards 1,2,3,5,6,7,9,10 get cushions.
The small usable ledge on hanging fragment 8 gets only a light cap
(cover depth 0.12); steep splinter faces stay bare.
No snow on upright faces; separated planks remain separate.
"""
import snow_hand as H
from snow_parts import cushion

RAILS = [4,11,12,13]
TOPS = [0,1,2,3,5,6,7,9,10]


def build(m, v):
    out = [m.beam(p, v) for p in RAILS]
    out.extend(cushion(m, p, v) for p in TOPS)
    out.append(m.cover(v, m.tops(v, parts=[8], steep=0.6), depth=0.12))
    return H.join(out)
