"""tower_tc4_top: the top of a lattice mast: a narrow lattice with antenna cross arms over a platform.

(Opus, 6 Oct, b1) the cross arms at the very top carried cotton-ball pillows at v7. Tops narrower than 20 cm get a
ridge or nothing; the platform keeps its cap."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, fn=lambda m_, v_: H.big_tops(m_, v_, 0.01), A7_OVL=0.3, A7_LIPDROP=0.05, A7_THIN=0.20)
