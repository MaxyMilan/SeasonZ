"""ruin_houseblock_corner_total: broken corner-house walls and slabs on rubble banks.

(Astra Curie, 7 Oct 2026, b1) the volume bridged the broken structure with split
sheets and long downward flaps. The two measured rubble banks (0, 1), surviving
slabs (5, 11) and masonry height bands receive separate supported blankets.
Low exposed floors are covered from v1. Tapered edges stop on their support;
thin fragments let snow through and a source-contact floor avoids ridge pokes.
Regions and equal physical-depth results are cached to finish the seven-depth
set without repeating identical work; every published depth remains explicit.

(Astra Euler II, 7 Oct 2026, b1) old-camera comparisons found interior splits
hidden by the new outermost camera targets. Each structural part now gets its
own naturally connected regions, avoiding arbitrary height-band seams and
bridges between masonry pieces. Finer support sampling follows rubble folds
and thin broken wall tops without stretching triangles across them.

(Astra Hypatia, 7 Oct 2026, b1) exact old-camera inspection found the underside
of several tapered caps peeling below broken wall tops. Keep the supported
top triangulation and close its boundary directly into the local source face,
replacing interpolated underside/curtain rings with short anchored edges.

The remaining brown slit includes exposed upward facets 4130/4323/4324 on
part 81, measured by camera and vertical rays. An exact supported thin dusting
on these narrow folded lips closes raster-edge misses without bridging the
real vertical fold (4326) or filling its crevice.
"""
import numpy as np
from mathutils import Vector
import snow_hand as H


def build(m, v):
    m.ground = float(m.V[:, 1].min()) - 0.25
    if not hasattr(m, '_sz_curie_corner_regions'):
        thin = [p for p in range(int(m.part_t.max()) + 1)
                if p not in (0, 1, 5, 11) and H.part_top_area(m, p, 0.55) < 0.025]
        H.through(m, thin)
        mound = np.isin(m.PART, (0, 1)) & (m.NYF >= 0.35)
        m.NYE = np.where(mound, np.maximum(m.NYE, np.interp(m.NYF, [.35, .45], [.57, .62])), m.NYE)
        exposed = m.tops(1, slope=False)
        tops = exposed & (m.NYF >= 0.65)
        groups = [exposed & mound & (m.PART == p) for p in (0, 1)]
        groups += [tops & (m.PART == p) for p in np.unique(m.PART[tops]) if p not in (0, 1)]
        m._sz_curie_corner_regions = [r for group in groups
            for r in m.regions(group, 1, close=0.0, tau=0.02, min_area=0.015)]
        m._sz_curie_corner_caps = {}
    key = float(m.thick(v))
    if key in m._sz_curie_corner_caps:
        return m._sz_curie_corner_caps[key]
    out = []
    for region, heights in m._sz_curie_corner_regions:
        cap = m.blanket(region, heights, v, rim='taper', over=0.0, smooth=0.0,
                        spacing=0.075, fill=0.0, holes=0.002, bury=False)
        if cap is not None:
            verts, faces = cap
            role = np.asarray(m._caps[-1]['role'])
            # Taper foot vertices must also meet the actual support. Leaving
            # their interpolated underside below a broken sloping wall made
            # a second visible lip and an apparent open slit along the top.
            for idx in range(len(verts)):
                x, y, z = verts[idx]
                hit, normal, _, _ = m.bvh.ray_cast(Vector((x, y + .18, z)), Vector((0., -1., 0.)), .36)
                clearance = .008 if role[idx] <= 1 else .001
                if hit is not None and normal.y >= .34 and hit.y > y - clearance:
                    verts[idx, 1] = hit.y + clearance
            out.append(_supported_skin(m, verts, faces, role))
    out.append(_folded_lip_dusting(m, v))
    cap = H.join(out)
    m._sz_curie_corner_caps[key] = cap
    return cap


def _supported_skin(m, verts, faces, role):
    faces = faces[np.all(role[faces] <= 1, axis=1)]
    if not len(faces):
        return verts, faces
    edges = np.vstack((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
    _, first, counts = np.unique(np.sort(edges, axis=1), axis=0, return_index=True, return_counts=True)
    boundary = edges[first[counts == 1]]
    ids = np.unique(boundary)
    foot = verts[ids].copy()
    for i, (x, y, z) in enumerate(foot):
        hit, normal, _, distance = m.bvh.find_nearest(Vector((x, y, z)))
        # Across an opening the nearest support may be beside the lip. A
        # downward-only ray could hit a lower wall and make a long curtain.
        if hit is not None:
            foot[i] = np.asarray(hit - normal * .003)
        else:
            foot[i, 1] = y - .003
    lookup = np.full(len(verts), -1, dtype=np.int64)
    lookup[ids] = np.arange(len(ids)) + len(verts)
    a, b = boundary.T
    side = np.vstack((np.column_stack((a, lookup[b], b)),
                      np.column_stack((a, lookup[a], lookup[b]))))
    joined = np.vstack((faces, side))
    used, inverse = np.unique(joined, return_inverse=True)
    return np.vstack((verts, foot))[used], inverse.reshape((-1, 3))


def _folded_lip_dusting(m, v):
    selected = m.T[[4130, 4323, 4324]]
    assert np.all(m.part_t[[4130, 4323, 4324]] == 81)
    edges = np.vstack((selected[:, [0, 1]], selected[:, [1, 2]], selected[:, [2, 0]]))
    _, first, count = np.unique(np.sort(edges, axis=1), axis=0, return_index=True, return_counts=True)
    border = m.V[edges[first[count == 1]]][:, :, [0, 2]]
    verts, faces = [], []
    for tri in selected:
        a, b, c = m.V[tri]
        n = int(np.ceil(max(np.linalg.norm(a-b), np.linalg.norm(b-c), np.linalg.norm(c-a))/.045))
        ids = {}
        for i in range(n+1):
            for j in range(n+1-i):
                p = a + (b-a)*(i/n) + (c-a)*(j/n)
                ab = border[:,1]-border[:,0]
                t = np.clip(((p[[0,2]]-border[:,0])*ab).sum(1)/np.maximum((ab*ab).sum(1),1e-12),0,1)
                d = float(np.linalg.norm(p[[0,2]]-(border[:,0]+t[:,None]*ab),axis=1).min())
                p[1] += .003 + min(.018,.09*float(m.thick(v)))*(1-np.exp(-d/.025))
                ids[i,j] = len(verts);verts.append(p)
        for i in range(n):
            for j in range(n-i):
                faces.append((ids[i,j],ids[i+1,j],ids[i,j+1]))
                if i+j<n-1:
                    faces.append((ids[i+1,j],ids[i+1,j+1],ids[i,j+1]))
    return np.asarray(verts), np.asarray(faces,dtype=np.int64)
