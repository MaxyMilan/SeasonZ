"""tisy_garages: military garage entrances beneath a broad earthwork roof.

(Astra Euler II, 7 Oct 2026, b1) the original volume lost broad roof cover between depths and left radial fans and hanging wedges.
The measured earthwork (0) receives a supported tapered blanket, with separate
caps on the exposed concrete roof/entry parts. Low exposed ground and floors
receive snow from v1; vertical facades and thin fittings do not collect it.
Source-contact checks preserve the faceted embankment. Cached regions and
equal physical depths keep a full seven-depth build practical in this session.
S1 has finished; this is the independently requested FIX repair with an 8 GB commit guard.
"""
import numpy as np
from mathutils import Vector
import snow_hand as H


def build(m, v):
    m.ground = float(m.V[:, 1].min()) - .25
    if not hasattr(m, '_sz_euler2_tisy1_regions'):
        thin = [p for p in range(int(m.part_t.max()) + 1)
                if p != 0 and H.part_top_area(m, p, .55) < .025]
        H.through(m, thin)
        mound = (m.PART == 0) & (m.NYF >= .4)
        m.NYE = np.where(mound, np.maximum(m.NYE, np.interp(m.NYF, [.4,.5],[.57,.66])), m.NYE)
        exposed = m.tops(1, slope=False)
        tops = exposed & (m.NYF >= .65)
        groups = [(exposed & mound,.15)]
        groups += [(tops & (m.PART == p),.10) for p in np.unique(m.PART[tops]) if p != 0]
        m._sz_euler2_tisy1_regions = [(r,z,spacing) for group,spacing in groups
            for r,z in m.regions(group,1,close=0.,tau=.02,min_area=.015)]
        m._sz_euler2_tisy1_caps = {}
    key = float(m.thick(v))
    if key in m._sz_euler2_tisy1_caps:
        return m._sz_euler2_tisy1_caps[key]
    out = []
    for region,heights,spacing in m._sz_euler2_tisy1_regions:
        cap = m.blanket(region,heights,v,rim='taper',over=0.,smooth=0.,
                        spacing=spacing,fill=0.,holes=.002,bury=False)
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
    m._sz_euler2_tisy1_caps[key] = result
    return result
