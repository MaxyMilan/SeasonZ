"""skilift_tower_end: the return station of a ski lift, a slanted mast with the bull wheel frame on top and a
counterweight block.

(Opus, 6 Oct, m1, c39) the frame of the bull wheel grew lumpy pillows and the thin connectors rolls. Tops narrower
than 20 cm get a ridge as high as they are wide (straight strips) or nothing; the counterweight keeps its cap."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, fn=lambda m_, v_: H.big_tops(m_, v_, 0.01), A7_THIN=0.20)
