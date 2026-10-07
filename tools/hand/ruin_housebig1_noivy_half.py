"""ruin_housebig1_noivy_half: surviving house slabs and gables above a broad rubble mound.

(Astra Noether, 7 Oct 2026, e2) the volume left a floating shard above the walls,
a wide crescent opening and triangular holes in the rubble blanket. The measured
mound (part 202) gets its own supported snow on actual upward faces through
60 degrees: the native smoothed-slope gate left broad fallen slabs bare.
Structural upward faces are split into masonry height bands so triangulation
cannot draw curtains between surviving floors. Thin fragments let snow through;
low exposed surfaces receive snow from v1, with tapered edges and no gap closing.

(Astra Curie, 7 Oct 2026, e2) remaining mound facets measured just under .5
normal.y still stayed bare, while interpolated caps intersected convex rubble.
The remaining broad mound facet measured normal.y=.384/.428 (67/65 degrees).
Its rough stone retains a thin dusting, grading from .35 to .45 actual normal.y;
less steep rubble keeps the fuller cover, with retained snow weight
(the roof rule otherwise zeros these already selected facets); denser sampling
and a local source-contact floor keep its blanket on the supporting stone.
Structural bands retain their stricter cutoff to prevent the old inner curtains.
"""
import numpy as np
import snow_hand as H
from mathutils import Vector


def build(m, v):
    m.ground = float(m.V[:, 1].min()) - 0.25
    if not getattr(m, '_sz_noether_parts', False):
        thin = [p for p in range(int(m.part_t.max()) + 1)
                if H.part_top_area(m, p, 0.65) < 0.08]
        H.through(m, thin)
        m._sz_noether_parts = True
    # The building roof slope rule otherwise zeroes snow on accepted rubble facets.
    mound_cells = (m.PART == 202) & (m.NYF >= 0.35)
    m.NYE = np.where(mound_cells, np.maximum(m.NYE, np.interp(m.NYF, [0.35, 0.45], [0.57, 0.62])), m.NYE)
    tops = m.tops(v, ny_min=0.65, slope=False) & (m.NYF >= 0.65)
    groups = [m.tops(v, parts=(202,), slope=False) & (m.NYF >= 0.35)]
    rest = tops & (m.PART != 202)
    for low, high in ((-100., -1.2), (-1.2, 0.3), (0.3, 2.6), (2.6, 100.)):
        groups.append(rest & (m.Z >= low) & (m.Z < high))
    out = []
    for group in groups:
        for region, heights in m.regions(group, v, close=0.0, tau=0.02, min_area=0.015):
            cap = m.blanket(region, heights, v, rim='taper', over=0.0, smooth=0.0,
                                 spacing=0.075, fill=0.0, holes=0.002, bury=False)
            if cap is not None:
                verts, faces = cap
                role = np.asarray(m._caps[-1]['role'])
                for idx in np.flatnonzero(role <= 1):
                    x, y, z = verts[idx]
                    hit, normal, _, _ = m.bvh.ray_cast(Vector((x, y + 0.18, z)), Vector((0., -1., 0.)), 0.36)
                    if hit is not None and normal.y >= 0.34 and hit.y > y - 0.008:
                        verts[idx, 1] = hit.y + 0.008
                out.append((verts, faces))
    return H.join(out)
