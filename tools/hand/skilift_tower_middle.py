"""skilift_tower_middle: a ski lift mast with two cross arms carrying the sheave trains (rows of small wheels).

(Opus, 6 Oct, r10, c39) the cross arms (10-15 cm wide) grew round balls of snow at v5-v7 and the clamps beads. Tops
narrower than 20 cm get a ridge as high as they are wide (straight strips) or nothing (wheels, clamps); the base
keeps its cap."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, fn=lambda m_, v_: H.big_tops(m_, v_, 0.01), A7_THIN=0.20)
