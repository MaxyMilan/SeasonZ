"""wall_barricade1_10: a junk barricade of pipes, planks, a shelf and chairs (Expansion mapping).

(Opus, 6 Oct, e1; Astra Boyle) as a fence (kind 1, its walls folder) every pipe got a log crescent that wrapped it
white and the shelf under a leaning panel a cushion, with teeth under the lips. A heap, not a fence: kind 0 and the
volumetric cap over parts with 1 dm2 of top."""
import snow_hand as H


def build(m, v):
    m.kind = 0
    return H.big_tops(m, v, 0.01)
