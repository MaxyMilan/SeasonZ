"""wall_wood1d_5_2.

The flat rails are 0 and 1. Surviving pickets 2..18 have usable cut tops;
small posts 19 and 20 also get shallow cushions. Missing planks stay open.
No snow on upright faces; separated planks remain separate.
"""
import snow_hand as H
from snow_parts import cushion

RAILS = [0,1]
TOPS = [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]


def build(m, v):
    out = [m.beam(p, v) for p in RAILS]
    out.extend(cushion(m, p, v) for p in TOPS)

    return H.join(out)
