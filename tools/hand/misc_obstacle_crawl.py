"""misc_obstacle_crawl: an assault course crawl frame: posts, a rail frame and wires.

(Opus, 6 Oct, o1) classified kind 0, so the volumetric cap ran: thin rails and bars stayed bare or grew vertical sheets,
slabs and post-top lumps. Built as a fence (kind 1): logs their crescent, beams their ridge, sawn tops their cushion.
(o1b, o1c) the barbed wire zigzagging over the frame (parts 8-19, two-sided, 0.03 m2 of top each: more than the
rails, so no area threshold parts them) grew crumpled ribbons by v7, also after see_through(.02). Those parts let
the snow through and leave the fence tables: only the posts and the rail frame hold snow."""
import numpy as np
import snow_hand as H

WIRE = tuple(range(8, 20))


def build(m, v):
    m.kind = 1
    if getattr(m, '_sz_see', None) is None:
        sel = np.isin(m.part_t, WIRE)
        m.occ_t = m.occ_t & ~sel
        m.good_t = m.good_t & ~sel
        m._raster()
        m._bvh()
        m._sz_see = WIRE
    if not hasattr(m, '_sz_fence'):
        H.fence_auto(m, v)
        keep = lambda L: [p for p in L if p not in WIRE]
        logs, beams, cush, strips, big = (keep(L) for L in m._sz_fence)
        m._sz_fence = (logs, beams, cush, strips, big)
        m._sz_parts = tuple(big)
        m._sz_block = tuple(logs + beams + strips)
        m.reset()
    return H.fence_auto(m, v)
