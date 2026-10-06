"""misc_woodtable_outdoor: a picnic table: top boards (0-4) on two A-frames (5, 6, 7, 12) with battens (8, 9), and two
benches of two boards each (13, 14 and 15, 16) on crossbars (17, 18).

Pillows (snow_addon via hybrid) on the table top and on each bench; the frames, battens and crossbars emit nothing:
their few exposed centimetres beside the boards grew knobs and lumps at the bench ends (c22)."""
import snow_hand as H


def build(m, v):
    m._sz_parts = (0, 1, 2, 3, 4, 13, 14, 15, 16)
    return H.hybrid(m, v)
