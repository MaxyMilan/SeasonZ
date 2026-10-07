"""rock_bright_wallh2: a bright horizontal irregular cliff with exposed upward ledges and deep crevices.

(Astra Euler II, 7 Oct 2026, c70) the rock runner volume hit its memory guard.
Use the independently accepted rock_wallv surface method; its old volume left projecting
sheets and upright slabs along steep flanks. Snow now follows exposed upward surface regions;
zero gap closing keeps crevices open and tapered short edges end on their stone support.
Dense thin-layer sampling and a local source-contact floor prevent convex stone ridges
from poking through the interpolated blanket, without lifting any detached component.
"""
import snow_hand as H
import numpy as np
from mathutils import Vector


def build(m, v):
    if not hasattr(m, '_sz_euler2_rock_regions'):
        tops = m.tops(1, ny_min=0.65, slope=False) & (m.NYF >= 0.65)
        m._sz_euler2_rock_regions = list(m.regions(tops, 1, close=0.0, tau=0.02, min_area=0.015))
    out = []
    for region, heights in m._sz_euler2_rock_regions:
        cap = m.blanket(region, heights, v, rim='taper', over=0.0,
                        smooth=0.0, spacing=0.075 if v <= 2 else 0.15,
                        fill=0.0, holes=0.002, bury=False)
        if cap is not None:
            verts, faces = cap
            # A convex source ridge must not emerge through an interpolated thin top.
            role = m._caps[-1]['role']
            for idx in np.flatnonzero(np.asarray(role) <= 1):
                x, y, z = verts[idx]
                hit, normal, _, _ = m.bvh.ray_cast(Vector((x, y + 0.12, z)),
                                                   Vector((0.0, -1.0, 0.0)), 0.24)
                if hit is not None and normal.y >= 0.6 and hit.y > y - 0.008:
                    verts[idx, 1] = hit.y + 0.008
            out.append((verts, faces))
    return H.join(out)
