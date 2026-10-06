"""castle_stairs_bottom_nolc: a steep wooden stair with a 10 cm square handrail on posts and a landing rail at the top.

(Opus, 6 Oct, c38) at v7 the handrail and the landing rail carried rolls two to three times their width (sausages);
strips up to 12 cm wide get a ridge as high as they are wide instead of the volumetric cap, the treads keep the cap."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, fn=lambda m_, v_: H.big_tops(m_, v_, 0.01), A7_THIN=0.12)
