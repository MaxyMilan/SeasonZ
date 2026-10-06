"""Experimental volume snow; deliberately not wired into snow_hand.build.

Run in Blender (numpy, bmesh and BVHTree only; no scipy/skimage). Deposition
samples are the sky-visible upward surfaces selected by Model.tops. Balls with
slope-dependent radii form a *three-dimensional* implicit union. A separable
Gaussian rounds its small seams; a growing radius bridges nearby supports.
Marching tetrahedra (a consistent six-tetrahedron decomposition of each voxel)
extracts the surface. The model's signed distance carves the volume with a
clearance. This is an experiment, not a production-ready replacement.

build(m, variant) -> (vertices, triangles), and registers real cap metadata.
Stats in m.volume_stats include rejected reductions and remaining collisions.
The collision guard rejects decimation which adds model intersections; it may
therefore fail the budget. Such a failure is reported, never silently exported.
"""
import math
import time
import numpy as np
import snow_hand as H


def _signed_queries(m, points):
    """Nearest oriented source distance (assumes consistently wound closed parts).

    This sign is a local approximation on nonmanifold/intersecting input; final
    triangle/model BVH intersection counts are an independent acceptance gate.
    """
    from mathutils import Vector
    bvh = m.bvh_all
    sign = getattr(m, '_volume_orientation', None)
    if sign is None:
        A, B, C = m.V[m.T[:, 0]], m.V[m.T[:, 1]], m.V[m.T[:, 2]]
        vol = np.bincount(m.part_t, weights=np.einsum('ij,ij->i', A, np.cross(B, C)))
        sign = np.where(vol[m.part_t[m._all_t]] < 0, -1., 1.)
        m._volume_orientation = sign
    dist = np.empty(len(points), dtype=np.float64)
    normals = np.empty((len(points), 3), dtype=np.float64)
    for i, p in enumerate(points):
        loc, n, idx, d = bvh.find_nearest(Vector(p))
        nr = np.asarray(n) * sign[idx]
        dist[i] = d if np.dot(p - np.asarray(loc), nr) >= -1e-8 else -d
        normals[i] = nr
    return dist, normals


def _blur3(field, sigma_cells):
    if sigma_cells < .15:
        return field
    radius = max(1, int(math.ceil(2.5 * sigma_cells)))
    k = np.arange(-radius, radius + 1)
    weights = np.exp(-.5 * (k / sigma_cells) ** 2)
    weights /= weights.sum()
    out = field
    for axis in range(3):
        pad = [(0, 0)] * 3
        pad[axis] = (radius, radius)
        src = np.pad(out, pad, mode='edge')
        out = np.zeros_like(out)
        for j, w in enumerate(weights):
            sl = [slice(None)] * 3
            sl[axis] = slice(j, j + field.shape[axis])
            out += src[tuple(sl)] * w
    return out


def _march(field, origin, pitch, return_edges=False):
    """Vectorized marching tetrahedra; share vertices by global grid edge IDs.

    Positive is snow. Orient triangles away from their positive tetrahedron
    vertices, independently of source winding. Global diagonals agree between
    cells, including ambiguous marching-cubes cases.
    """
    shape = np.asarray(field.shape)
    corners = np.array(((0,0,0),(1,0,0),(1,1,0),(0,1,0),
                        (0,0,1),(1,0,1),(1,1,1),(0,1,1)))
    low = np.full(tuple(shape - 1), np.inf, np.float32)
    high = np.full(tuple(shape - 1), -np.inf, np.float32)
    for c in corners:
        sl = tuple(slice(int(v), int(v + n - 1)) for v, n in zip(c, shape))
        np.minimum(low, field[sl], out=low)
        np.maximum(high, field[sl], out=high)
    cells = np.column_stack(np.nonzero((low < 0) & (high > 0)))
    del low, high
    if not len(cells):
        empty=(np.empty((0,3)),np.empty((0,3),np.int64))
        return (*empty,np.empty((0,2,3),np.int64)) if return_edges else empty
    strides = np.array((shape[1]*shape[2], shape[2], 1))
    ids = cells @ strides[:, None] + corners @ strides
    vals = field.ravel()[ids]
    tets = ((0,1,2,6),(0,2,3,6),(0,3,7,6),(0,7,4,6),(0,4,5,6),(0,5,1,6))
    edges = ((0,1),(0,2),(0,3),(1,2),(1,3),(2,3))
    face_edges, outward = [], []
    for tet in tets:
        tet = np.asarray(tet)
        tv = vals[:, tet]
        masks = (tv > 0) @ np.array((1,2,4,8))
        for case in range(1, 15):
            sel = np.flatnonzero(masks == case)
            if not len(sel):
                continue
            pos = [i for i in range(4) if case & (1 << i)]
            neg = [i for i in range(4) if not case & (1 << i)]
            if len(pos) == 1:
                triangles = [[(pos[0], n) for n in neg]]
            elif len(neg) == 1:
                triangles = [[(neg[0], p) for p in pos]]
            else:
                a,b = pos; c,d = neg
                triangles = [[(a,c),(a,d),(b,d)],[(a,c),(b,d),(b,c)]]
            direction = (corners[tet[neg]].mean(0) - corners[tet[pos]].mean(0)) * pitch
            for tri in triangles:
                e = np.array([(tet[a],tet[b]) for a,b in tri])
                face_edges.append(np.sort(ids[sel[:,None,None], e[None]], axis=-1))
                outward.append(np.broadcast_to(direction, (len(sel),3)))
    face_edges = np.concatenate(face_edges)
    outward = np.concatenate(outward)
    unique, inv = np.unique(face_edges.reshape(-1,2), axis=0, return_inverse=True)
    p0 = np.column_stack(np.unravel_index(unique[:,0], tuple(shape)))
    p1 = np.column_stack(np.unravel_index(unique[:,1], tuple(shape)))
    a, b = field.ravel()[unique[:,0]], field.ravel()[unique[:,1]]
    w = a / (a-b)
    V = origin + (p0 + (p1-p0) * w[:,None]) * pitch
    F = inv.reshape(-1,3)
    normals = np.cross(V[F[:,1]]-V[F[:,0]], V[F[:,2]]-V[F[:,0]])
    rev = np.einsum('ij,ij->i', normals, outward) < 0
    F[rev] = F[rev][:,[0,2,1]]
    return (V,F,np.stack((p0,p1),axis=1)) if return_edges else (V,F)


def _compact(V, F):
    used, inv = np.unique(F, return_inverse=True)
    return V[used], inv.reshape(-1,3)


def intersections(m, V, F):
    from mathutils.bvhtree import BVHTree
    if not len(F):
        return []
    b = BVHTree.FromPolygons(V.tolist(), F.tolist(), all_triangles=True)
    return b.overlap(m.bvh_all)


def _sky_heights(m, points):
    from mathutils import Vector
    ceiling = float(m.V[:,1].max()+5.)
    down = Vector((0,-1,0))
    out = np.full(len(points), -1e6)
    for i,p in enumerate(points):
        hit = m.bvh_all.ray_cast(Vector((float(p[0]),ceiling,float(p[2]))),down)[0]
        if hit is not None:
            out[i] = hit.y
    return out


def _lift_clear(m, V, F, clearance, max_passes=12):
    """Raise conflicting triangles above their overlapping source polygons.

    Vertices alone miss a peak crossing a large decimated face. On each BVH
    pair compute the actual xz polygon overlap: height difference is affine,
    so its maximum is at a polygon corner. Lift all three snow vertices by
    that maximum. This can distort a rim; record the movement and inspect it.
    """
    V=V.copy()
    original=V.copy()
    y=_sky_heights(m,V)
    V[:,1]=np.maximum(V[:,1],y+clearance)
    for iteration in range(max_passes):
        pairs=intersections(m,V,F)
        if not pairs:
            break
        lifts=np.zeros(len(V))
        for si,mi in pairs:
            snow=V[F[si]]
            model=m.V[m.T[m._all_t[mi]]]
            # Clip the source triangle by the projected snow triangle.
            poly=[p.copy() for p in model]
            area=np.cross(snow[1]-snow[0],snow[2]-snow[0])[1]
            if abs(area)<1e-12:
                continue
            sgn=-1. if area>0 else 1.
            for k in range(3):
                a,b=snow[k],snow[(k+1)%3]
                def side(p):
                    return sgn*((b[0]-a[0])*(p[2]-a[2])-(b[2]-a[2])*(p[0]-a[0]))
                nxt=[]
                for u,w in zip(poly,poly[1:]+poly[:1]):
                    du,dw=side(u),side(w)
                    if du>=-1e-10:
                        nxt.append(u)
                    if (du>=0)!=(dw>=0):
                        nxt.append(u+(w-u)*(du/(du-dw)))
                poly=nxt
                if not poly:
                    break
            if not poly:
                continue
            plane=np.cross(snow[1]-snow[0],snow[2]-snow[0])
            need=0.
            for p in poly:
                sy=snow[0,1]-(plane[0]*(p[0]-snow[0,0])+plane[2]*(p[2]-snow[0,2]))/plane[1]
                need=max(need,p[1]+clearance-sy)
            lifts[F[si]]=np.maximum(lifts[F[si]],need+1e-5)
        if not np.any(lifts):
            break
        V[:,1]+=lifts
    return V,dict(lift_max_m=float((V[:,1]-original[:,1]).max()),
                  lifted_vertices=int(np.count_nonzero(V[:,1]>original[:,1]+1e-5)))


def _decimate(V, F, budget):
    import bpy
    me = bpy.data.meshes.new('volume_experiment')
    me.from_pydata(V.tolist(), [], F.tolist())
    obj = bpy.data.objects.new('volume_experiment', me)
    bpy.context.scene.collection.objects.link(obj)
    mod = obj.modifiers.new('volume_budget', 'DECIMATE')
    mod.ratio = min(1., budget / len(F))
    mod.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get()
    result = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    result.calc_loop_triangles()
    v = np.array([p.co[:] for p in result.vertices], dtype=float)
    f = np.array([p.vertices[:] for p in result.loop_triangles], dtype=np.int64)
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(me)
    bpy.data.meshes.remove(result)
    return v, f


def _contact_rim(m,V,F,clearance):
    """Roll the open extraction edge back to its nearest real support."""
    from mathutils import Vector
    directed=np.concatenate((F[:,[0,1]],F[:,[1,2]],F[:,[2,0]]))
    _,inv,count=np.unique(np.sort(directed,axis=1),axis=0,return_inverse=True,return_counts=True)
    boundary=directed[count[inv]==1]
    verts=np.unique(boundary)
    target=[]
    for i in verts:
        loc,_,_,d=m.bvh_all.find_nearest(Vector(V[i]))
        loc=np.array(loc)
        direction=V[i]-loc
        direction/=max(np.linalg.norm(direction),1e-12)
        target.append(loc+clearance*direction)
    target=np.array(target)
    rows=[V]
    extra=[]
    prior=np.arange(len(V))
    for j,t in enumerate((.5,1.)):
        new=V[verts]*(1-t)+target*t
        ids=np.full(len(V),-1,dtype=int)
        ids[verts]=len(V)+j*len(verts)+np.arange(len(verts))
        a,b=boundary.T
        extra.extend((np.column_stack((prior[b],prior[a],ids[a])),
                      np.column_stack((prior[b],ids[a],ids[b]))))
        rows.append(new)
        prior=ids
    return np.vstack(rows),np.vstack([F]+extra)


def _register(m, V, F, clearance, pitch):
    """One entry per connected component so floating islands remain detectable."""
    uf = H.UF(len(V))
    for a,b,c in F.tolist():
        uf.union(a,b); uf.union(b,c)
    roots = np.array([uf.find(int(f[0])) for f in F])
    out = []
    for root in np.unique(roots):
        vs, fs = _compact(V, F[roots == root])
        d, _ = _signed_queries(m, vs)
        fn = np.cross(vs[fs[:,1]] - vs[fs[:,0]], vs[fs[:,2]] - vs[fs[:,0]])
        vn = np.zeros_like(vs)
        for j in range(3):
            np.add.at(vn, fs[:,j], fn)
        # Physical contact/underside vertices, rather than marking every edge
        # a legal foot. Closed output has no boundary in normal circumstances.
        E=np.sort(np.concatenate((fs[:,[0,1]],fs[:,[1,2]],fs[:,[2,0]])),axis=1)
        edges,counts=np.unique(E,axis=0,return_counts=True)
        boundary=np.zeros(len(vs),bool)
        boundary[np.unique(edges[counts==1])]=True
        contact = boundary & (np.abs(d) <= .02)
        role = np.where(contact, 3, np.where(vn[:,1] < -.001, 2, 0))
        foot = contact.copy()
        anchor = np.full(len(vs), -1, dtype=np.int64)
        m._caps.append(dict(V=vs,F=fs,role=role,anchor=anchor,foot=foot))
        out.append((vs,fs))
    return H.join(out)


def build(m, variant, *, voxel=None, budget=5800, clearance=.0025,
          smooth=.18, carve=True, guard=True, rim=False):
    """Build a volume; all lengths in metres in the game's y-up coordinates.

    No reset here: like Model.log(), callers can join several builders. The
    experiment recipes call m.reset() through the ordinary recipe harness.
    """
    start = time.perf_counter()
    depth = m.thick(variant)
    h = float(voxel or (.008 if depth < .04 else .012))
    # Use dense deposition even at v1, since a radius smaller than seed spacing
    # would make separate grains. m.Z is used only for seed positions; the
    # volume and extraction do not require one height per horizontal location.
    selected = m.tops(variant)
    m._sel |= selected
    m._claimed |= selected
    # The support continues into a slope where the snow naturally thins out.
    m._soft |= selected & (m.NYE < .85)
    stride = max(1, int(min(.035, max(.01, depth*.28)) / m.g))
    jj, ii = np.nonzero(selected & (np.indices(selected.shape)[0] % stride == 0)
                        & (np.indices(selected.shape)[1] % stride == 0))
    if not len(jj):
        m.volume_stats = dict(empty=True)
        return None
    seeds = np.column_stack((m.u0 + ii*m.g, m.Z[jj,ii], m.v0 + jj*m.g))
    # Keep small positive deposition near the slope cutoff. As in blanket,
    # slope weight controls depth but does not redefine the promised coverage.
    weight = H.SC.slope_w(m.scls, variant, m.NYE[jj,ii], m.skind)
    radii = depth * np.maximum(.22, weight)
    pad = depth + 4*h
    origin = np.floor((seeds.min(0) - pad) / h) * h
    size = np.ceil((seeds.max(0) + pad - origin) / h).astype(int) + 1
    if np.prod(size) > 110_000_000:
        raise ValueError('Volume grid exceeds 110 million samples; choose coarser voxel')
    field = np.full(tuple(size), -2*depth-4*h, np.float32)
    # SDF union of spheres, clipped outside a narrow band needed by smoothing.
    for p,r in zip(seeds,radii):
        reach = r + 3*h
        low = np.maximum(0, np.floor((p-reach-origin)/h).astype(int))
        high = np.minimum(size, np.ceil((p+reach-origin)/h).astype(int)+1)
        x,y,z = [origin[k] + np.arange(low[k],high[k])*h-p[k] for k in range(3)]
        sdf = r - np.sqrt(x[:,None,None]**2+y[None,:,None]**2+z[None,None,:]**2)
        sl = tuple(slice(a,b) for a,b in zip(low,high))
        np.maximum(field[sl], sdf, out=field[sl])
    deposit_s = time.perf_counter()-start
    # Gaussian radius grows with depth. Work on bounded distances: unsampled
    # far exterior must not erode the rim during the convolution.
    sigma = min(2., max(.35, smooth*depth/h))
    np.maximum(field, -3*h, out=field)
    field = _blur3(field, sigma)
    carved = 0
    if carve:
        # Exact nearest-triangle magnitude, approximate oriented sign. Query
        # only the snow's narrow band, preserving all possible zero crossings.
        # Use the exterior visible from the sky for the sign. Unlike nearest
        # triangle normals this remains stable on overlapping/double-sided
        # visual meshes. Its conservative shadow carve also forbids snow
        # beneath an overhang. The magnitude still comes from the full mesh.
        xz=np.array(np.meshgrid(np.arange(size[0]),np.arange(size[2]),indexing='ij')).reshape(2,-1).T
        xy_points=np.column_stack((origin[0]+xz[:,0]*h,np.zeros(len(xz)),origin[2]+xz[:,1]*h))
        skyline=_sky_heights(m,xy_points).reshape(size[0],size[2])
        idx = np.column_stack(np.nonzero(field > -1.8*h))
        for k in range(0,len(idx),25000):
            q = idx[k:k+25000]
            P = origin + q*h
            d,_ = _signed_queries(m,P)
            d=np.abs(d)*np.where(P[:,1]>=skyline[q[:,0],q[:,2]],1.,-1.)
            old = field[tuple(q.T)]
            field[tuple(q.T)] = np.minimum(old, d-clearance)
            carved += int(np.count_nonzero((old > 0)&(d < clearance)))
    field_s = time.perf_counter()-start
    V,F = _march(field, origin, h)
    del field
    if not len(F):
        m.volume_stats = dict(empty=True, voxel=h, selected=int(selected.sum()))
        return None
    # A cap is an open shell: discard the carved contact underside. Every
    # surviving boundary is checked for proximity to the real support.
    n=np.cross(V[F[:,1]]-V[F[:,0]],V[F[:,2]]-V[F[:,0]])
    F=F[n[:,1]>1e-12]
    V,F=_compact(V,F)
    V,raw_lift=_lift_clear(m,V,F,clearance)
    raw_tris = len(F)
    pre = intersections(m,V,F)
    rejected = []
    chosen = 'raw'
    # Try the requested budget, then the hard LOD0 ceiling. Reject reductions
    # with additional intersection pairs. We also report all residual pairs.
    for target in sorted(set((int(budget),12000))):
        if len(F) <= target:
            break
        vs,fs = _decimate(V,F,int(target*.68) if rim else target)
        if rim:
            vs,fs=_contact_rim(m,vs,fs,clearance)
        vs,lift=_lift_clear(m,vs,fs,clearance)
        hit = intersections(m,vs,fs)
        if (not guard or not hit) and len(fs)<=target:
            V,F = vs,fs
            chosen = str(target)
            break
        rejected.append(dict(target=target,triangles=len(fs),intersections=len(hit)))
    post = intersections(m,V,F)
    result = _register(m,V,F,clearance,h)
    m.volume_stats = dict(voxel=h,grid=size.tolist(),seeds=len(seeds),depth=depth,
                          smooth_sigma_m=sigma*h,selected=int(selected.sum()),
                          raw_tris=raw_tris,triangles=len(F),carved_samples=carved,
                          intersections_before=len(pre),intersections_after=len(post),
                          decimation=chosen,rejected=rejected,raw_lift=raw_lift,
                          final_lift=lift if chosen!='raw' else raw_lift,budget_ok=len(F)<=budget,
                          lod0_ok=len(F)<=12000,deposit_s=deposit_s,field_s=field_s,
                          seconds=time.perf_counter()-start)
    return result
