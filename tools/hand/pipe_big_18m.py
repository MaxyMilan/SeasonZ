"""pipe_big_18m: an 18 m pipe bridge: big pipes in a lattice truss on two legs.

(Opus, 6 Oct, b1) the truss's thin rails and diagonals carried fat faceted sausages at v4-v7. Tops narrower
than 16 cm (rails, diagonals) get a ridge or nothing, the pipes and the walkway their caps, the lip short."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, fn=lambda m_, v_: H.big_tops(m_, v_, 0.01), A7_OVL=0.15, A7_LIPDROP=0.03, A7_THIN=0.16)
