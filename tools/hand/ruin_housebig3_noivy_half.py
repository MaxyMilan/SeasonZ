"""ruin_housebig3_noivy_half: ruined house floors and walls above broad rubble slopes.

(Astra Gauss, 7 Oct 2026, e2) Laplace surface blankets removed the outer rubble
fans, but the automatic beam and slope route retained curtains below the upper
slab. Separate upper slabs, height bands and rubble regions hold tapered blankets; thin steep fragments
let snow through. Short lips and zero gap closing preserve open framing. Low
exposed floors keep their snow from v1.

(Astra Noether, 7 Oct 2026, e2) the native slope/gradient gate still removed broad
fallen mound slabs with measured source normal.y=.526-.559. Keep upward mound
faces through 60 degrees using actual normals, independently of the stricter
structural cutoff and the smoothed slope gate. Slabs and masonry bands stay split.

(Astra Curie, 7 Oct 2026, e2) remaining mound facets measured just under .5
normal.y still stayed bare, while interpolated caps intersected convex rubble.
The mound alone accepts actual upward faces to .45 with retained snow weight
(the roof rule otherwise zeros these already selected facets); denser sampling
and a local source-contact floor keep its blanket on the supporting stone.
Structural bands retain their stricter cutoff to prevent the old inner curtains.
"""
import numpy as np
import snow_hand as H
from mathutils import Vector


def build(m, v):
    m.ground = float(m.V[:, 1].min()) - 0.25
    if not getattr(m, '_sz_gauss_parts', False):
        thin = []
        for p in range(int(m.part_t.max()) + 1):
            pts = m.V[np.unique(m.T[m.part_t == p])]
            ex = np.ptp(pts, axis=0)
            if H.part_top_area(m, p, 0.65) < 0.08:
                thin.append(p)
        H.through(m, thin)
        m._sz_gauss_parts = True
    # The building roof slope rule otherwise zeroes snow on accepted rubble facets.
    mound_cells = (m.PART == 344) & (m.NYF >= 0.45)
    m.NYE = np.where(mound_cells, np.maximum(m.NYE, 0.62), m.NYE)
    tops = m.tops(v, ny_min=0.65, slope=False) & (m.NYF >= 0.65)
    out = []
    # The rubble mound, upper slabs and stepped masonry must not share an
    # outline: its triangulation otherwise draws a curtain across open air.
    mound = m.tops(v, parts=(344,), slope=False) & (m.NYF >= 0.45)
    groups = [mound, tops & (m.PART == 402)]
    rest = tops & ~np.isin(m.PART, (344, 402))
    for low, high in ((-100., 0.), (0., 1.5), (1.5, 2.8), (2.8, 100.)):
        groups.append(rest & (m.Z >= low) & (m.Z < high))
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
                    if hit is not None and normal.y >= 0.44 and hit.y > y - 0.008:
                        verts[idx, 1] = hit.y + 0.008
                out.append((verts, faces))
    return H.join(out)
