"""misc_cinderblocks: a stack of hollow cinder blocks (Expansion mapping).

(Opus, 6 Oct, e1; Astra Boyle) the stack's tops (a grid of 3 cm cell walls) stayed bare while two loose blocks grew
mushroom domes. The blanket recipe instead (H.auto: each top region its own blanket)."""
import snow_hand as H


def build(m, v):
    return H.auto(m, v)
