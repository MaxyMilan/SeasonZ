"""house_1w13_dam: a damaged one-storey log house on a stone plinth, holes in its roof, a stone stair (Expansion mapping).

(Opus, 6 Oct, e1; Astra McClintock) the plinth's sloped drip ledge stayed bare at every depth on the gable side (no
eave above it there), and at v1 the stair treads tore into triangular gaps. The drip ledge slopes past the default
limit: snow holds to 55 degrees, full depth to 40; v1 and v2 show the v3 cap. The snow draping into the roof's holes
stays: the roof is broken."""
import snow_hand as H


def build(m, v):
    return H.consts(m, max(v, 3), fn=lambda m_, v_: H.big_tops(m_, v_, 0.01), A5_STEEP_SMOOTH=55.0, A5_FULL_SMOOTH=40.0)
