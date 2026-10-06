"""misc_woodtable_outdoor: a picnic table. Top of five planks (parts 0-4), two benches of two planks each (13-16),
the A frames and cross bars (5-12, 17-25) below.

Snow on the table top and the two bench seats, each one blanket (the 1 cm gaps between their planks bridged in every
depth), the outline softened over the uneven plank ends (they stood out as fingers along the rounded edge). The frame
holds none: the slanted legs and the bar ends carried shapeless blobs under the seats."""
import snow_hand as H

TOP = [0, 1, 2, 3, 4]
BENCHES = [13, 14, 15, 16]


def build(m, v):
    out = []
    for R, Zc in m.regions(m.tops(v, parts=TOP + BENCHES, steep=0.6), v):
        out.append(m.blanket(R, Zc, v))
    return H.join(out)

