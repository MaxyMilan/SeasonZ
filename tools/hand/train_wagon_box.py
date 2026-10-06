"""train_wagon_box: a covered goods wagon with a barrel roof (part 121); ribs on the end walls reach up to the roof's
curved ends.

(Opus, 6 Oct) the roof's lip rolled out over the ends and the ribs cut it into notched curtains (m1, c32). The lip may
overhang by at most 10% of the depth (+1 cm) and sink 2.8 cm at most; buffers, couplers and small fittings (under
100 cm2 of top) hold none."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, fn=lambda m_, v_: H.big_tops(m_, v_, 0.01), A7_OVL=0.1, A7_LIPDROP=0.1)
