"""mine_building: a tall industrial mine building with stepped roofs and raised copings.

(Astra Noether, 7 Oct 2026, b1) the volume left a broad horizontal coping corner
bare at v1 and pinched the deep lower-roof corner into overlapping triangular
flaps. Supported blankets follow the actual upward roof and coping regions,
separating their height steps and preserving source contact with no smoothing.
Thin fittings let snow through, while short lips avoid facade curtains.

(Astra Curie, 7 Oct 2026, b1) review still found pinched deep lip folds and a
triangular hanging flap. Tapered edges end on the roof support with no rolled
skirt; surface sampling preserves the real roof/copings and their small steps.
"""
import numpy as np
from mathutils import Vector
import snow_hand as H


def build(m, v):
    thin = [p for p in range(int(m.part_t.max()) + 1)
            if H.part_top_area(m, p, ny_min=0.8) < 0.025]
    H.through(m, thin)
    tops = m.tops(v, ny_min=0.8, slope=False) & (m.NYF >= 0.8)
    out = []
    for region, heights in m.regions(tops, v, close=0.0, tau=0.025, min_area=0.008):
        cap = m.blanket(region, heights, v, rim='taper', over=0.0, smooth=0.0,
                             spacing=0.18, shoulder=0.25, fill=0.0, holes=0.0,
                             bury=False)
        if cap is not None:
            verts = np.asarray(cap[0], float)
            extent = np.ptp(verts, axis=0)
            # A raster sliver beyond the narrow gutter had no source contact.
            if min(extent[0], extent[2]) < 0.05 and len(verts) < 500:
                if min(m.bvh_all.find_nearest(Vector(p))[3] for p in verts) > 0.03:
                    continue
        out.append(cap)
    cap = H.join(out)
    if cap is None:
        return None
    verts, faces = np.asarray(cap[0], float), np.asarray(cap[1], np.int64)
    uf = H.UF(len(verts))
    for a, b, c in faces.tolist():
        uf.union(a, b)
        uf.union(b, c)
    roots = np.array([uf.find(i) for i in range(len(verts))])
    rejected = []
    ids, counts = np.unique(roots, return_counts=True)
    for root, count in zip(ids, counts):
        if count >= 500:
            continue
        component = verts[roots == root]
        extent = np.ptp(component, axis=0)
        if min(extent[0], extent[2]) < 0.05:
            if min(m.bvh_all.find_nearest(Vector(p))[3] for p in component) > 0.03:
                rejected.append(root)
    if rejected:
        faces = faces[~np.isin(roots[faces[:, 0]], rejected)]
        used, inverse = np.unique(faces, return_inverse=True)
        return verts[used], inverse.reshape(-1, 3)
    return verts, faces
