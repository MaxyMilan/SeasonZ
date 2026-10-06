"""ruin_chimney: a free-standing ruined chimney stack with a stump of wall at its foot.

(Opus, 6 Oct, c37) the stack's cap ran down the stack and joined the much lower wall stump (marshmallow, v7).
(c62) fields per part changed nothing (one part): a small ledge on the stack's side carried its own snow and the
top cap bridged down to it. Small or narrow tops below a bigger one stay bare (H.ledges), a short lip."""
import snow_hand as H


def build(m, v):
    H.ledges(m, 0.10, 0.5)
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05)
