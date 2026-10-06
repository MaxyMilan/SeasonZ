"""farm_hopper: a feed silo on a steel lattice stand, a railed platform round its top.

(Opus, 6 Oct, b1) the top railing carried a sausage far wider than the tube and a jagged fringe hung down the
silo's rim at v4-v7. Tops narrower than 10 cm (railing, ladder) a ridge or nothing, a short lip (30% of the depth
+ 1 cm, sinking 1.6 cm at most)."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, fn=lambda m_, v_: H.big_tops(m_, v_, 0.01), A7_OVL=0.3, A7_LIPDROP=0.05, A7_THIN=0.10)
