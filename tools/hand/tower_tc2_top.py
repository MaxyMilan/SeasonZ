"""tower_tc2_top: the top of a radio mast: a tube with rows of thin antenna arms and a small platform.

(Opus, 6 Oct, b1) the antenna arms (flat bars 8-12 cm wide) carried flat sausages of snow at v4-v7. Tops narrower
than 15 cm get a ridge or nothing; the platform keeps its cap."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, fn=lambda m_, v_: H.big_tops(m_, v_, 0.01), A7_OVL=0.3, A7_LIPDROP=0.05, A7_THIN=0.15)
