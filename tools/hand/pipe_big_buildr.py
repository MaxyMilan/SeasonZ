"""pipe_big_buildr: industrial pipes turning across a tall steel support gantry and narrow walkway.

(Astra Euler, 7 Oct 2026, b1) the volume route grew blocky fitting lobes and upright spikes at truss junctions,
and thick drapes down steep pipe ends. Measured substantial upward-facing surfaces receive individual blankets.
Thin fittings let snow through; steep faces stay bare. Separate regions with no gap closing preserve height
steps and openings. Straight frame members use width-limited beam ridges; measured junction plates 65/76/109 take a half-depth
blanket. Unsupported fragments are pruned against the actual source mesh.
"""
import snow_hand as H
import numpy as np
from mathutils import Vector


def build(m, v):
    if not hasattr(m, '_sz_euler_panels'):
        m._sz_euler_panels = tuple(p for p in range(int(m.part_t.max()) + 1)
                                    if H.part_top_area(m, p, ny_min=0.75) >= 0.1)
        H.through(m, [p for p in range(int(m.part_t.max()) + 1) if p not in m._sz_euler_panels])
    out = []
    for p in m._sz_euler_panels:
        if m.is_beam(p):
            out.append(m.beam(p, v, step=0.2))
            continue
        tops = m.tops(v, parts=(p,), ny_min=0.75) & (m.NYF >= 0.75)
        for region, heights in m.regions(tops, v, close=0.0, min_area=0.008):
            out.append(m.blanket(region, heights, v, depth=0.5 if p in (65, 76, 109) else 1.0,
                                 over=0.003, shoulder=0.25,
                                 smooth=0.025, fill=0.003, bury=False, holes=0.0))
    cap = H.join(out)
    if cap is None:
        return None
    verts, faces = np.asarray(cap[0], float), np.asarray(cap[1], np.int64)
    uf = H.UF(len(verts))
    for a, b, c in faces.tolist():
        uf.union(a, b)
        uf.union(b, c)
    roots = np.array([uf.find(int(f[0])) for f in faces])
    keep = np.zeros(len(faces), bool)
    for root in np.unique(roots):
        ids = np.flatnonzero(roots == root)
        points = np.unique(faces[ids])
        sample = points[::max(1, len(points) // 200)]
        if any(m.bvh_all.find_nearest(Vector(verts[i]), 0.03)[0] is not None for i in sample):
            keep[ids] = True
    return (verts, faces[keep]) if keep.any() else None
