"""misc_concreteblock2: a concrete road barrier block with three steel lifting loops on top (parts 1-2, 7-8, 13-14).

(Opus, 6 Oct) the loops (13-137 cm2 of top) grew angular lumps by v4 (r10). Only the block (part 0) holds snow; the
loops stand out of its pillow."""
import snow_hand as H


def build(m, v):
    return H.big_tops(m, v, 0.02)
