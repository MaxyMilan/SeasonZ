"""smokestack_big_ruin_bottom: a broken chimney base on a large rubble bank.

(Astra Euler II, 7 Oct 2026, b1) the pending volumetric route needs about 22 GB
at a 6 cm lattice. Supported surface blankets follow the measured rubble bank
(34) and the exposed structural parts independently. Low open rubble receives
snow from v1, while thin bars and fittings let it through. Tapered edges stop
on support and a local source-contact floor protects sharp rubble ridges.
Prepared for a sequential build only after S1 and the rock runner finish.
(Astra Pascal, 7 Oct 2026, b1) source part analysis found the area filter
retained long 4-7 cm rods (4-6 and 246-255). Explicitly pass these through
in accordance with the thin-rod decision; masonry debris and platforms remain.
"""
import numpy as np
from mathutils import Vector
import snow_hand as H


def build(m, v):
    m.ground = float(m.V[:, 1].min()) - 0.25
    if not hasattr(m, '_sz_euler2_smoke_regions'):
        thin = [p for p in range(int(m.part_t.max()) + 1)
                if p in (4, 5, 6, *range(246, 256))
                or (p != 34 and H.part_top_area(m, p, .55) < .025)]
        H.through(m, thin)
        mound = (m.PART == 34) & (m.NYF >= .4)
        m.NYE = np.where(mound, np.maximum(m.NYE, np.interp(m.NYF, [.4, .5], [.57, .66])), m.NYE)
        exposed = m.tops(1, slope=False)
        tops = exposed & (m.NYF >= .65)
        groups = [(exposed & mound, .15)]
        groups += [(tops & (m.PART == p), .09) for p in np.unique(m.PART[tops]) if p != 34]
        m._sz_euler2_smoke_regions = [(r,z,spacing) for group,spacing in groups
            for r,z in m.regions(group, 1, close=0., tau=.02, min_area=.015)]
        m._sz_euler2_smoke_caps = {}
    key = float(m.thick(v))
    if key in m._sz_euler2_smoke_caps:
        return m._sz_euler2_smoke_caps[key]
    out = []
    for region,heights,spacing in m._sz_euler2_smoke_regions:
        cap = m.blanket(region, heights, v, rim='taper', over=0., smooth=0.,
                        spacing=spacing, fill=0., holes=.002, bury=False)
        if cap is None:
            continue
        verts,faces = cap
        role = np.asarray(m._caps[-1]['role'])
        for idx in np.flatnonzero(role <= 1):
            x,y,z = verts[idx]
            hit,normal,_,_ = m.bvh.ray_cast(Vector((x,y+.18,z)),Vector((0.,-1.,0.)),.36)
            if hit is not None and normal.y >= .39 and hit.y > y-.008:
                verts[idx,1] = hit.y+.008
        out.append((verts,faces))
    result = H.join(out)
    m._sz_euler2_smoke_caps[key] = result
    return result
