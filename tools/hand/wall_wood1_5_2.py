"""wall_wood1_5_2.

Flat rails 0 and 1 receive beam caps. Pickets 2..29 and small posts 30,31
receive thin cushions on their actual slanted cut tops.
No snow on upright faces; separated planks remain separate.
"""
import snow_hand as H
from snow_parts import cushion

RAILS = [0,1]
TOPS = [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31]


def build(m, v):
    out = [m.beam(p, v) for p in RAILS]
    out.extend(cushion(m, p, v) for p in TOPS)

    return H.join(out)
