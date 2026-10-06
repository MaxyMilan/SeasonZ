"""workshop_fuelstation: a small workshop with a flat roof, a railing and a side stair (Expansion mapping).

(Opus, 6 Oct, e2; Astra Feynman) v4-v7 clean; at v1 the thin layer opened long jagged seams and holes on the roof.
v1 and v2 show the v3 cap."""
import snow_hand as H


def build(m, v):
    return H.big_tops(m, max(v, 3), 0.01)
