"""roadblock_cncblocks_long: four concrete blocks in two layers: 1 and 5 on top, 3 and 4 below and showing beside
them; 0 and 2 are lifting loops.

(Opus, 6 Oct) in one field the upper blocks' lip flowed down the front onto the lower blocks in angular flaps (m1,
c32). Two caps (H.separate), each blocking the other layer; the loops hold none."""
import snow_hand as H


def build(m, v):
    return H.separate(m, v, [((1, 5), (3, 4, 0, 2)), ((3, 4), (1, 5, 0, 2))])
