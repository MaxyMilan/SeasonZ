"""misc_obstacle_runaround: an assault course run-around frame of bent tubes.

(Opus, 6 Oct, o1) classified kind 0, so the volumetric cap ran: thin rails and bars stayed bare or grew vertical sheets,
slabs and post-top lumps. Built as a fence (kind 1): logs their crescent, beams their ridge, sawn tops their cushion."""
import snow_hand as H


def build(m, v):
    m.kind = 1
    return H.fence_auto(m, v)
