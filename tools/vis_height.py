"""The top of a model as snow sees it: the highest visual surface over every point of a grid, from its LOD 0 triangles
(odol_extract), with the normal of the face found there."""
import os, math, re
import numpy as np

SEE_THROUGH = re.compile(r'(wire|barbed|pletivo|drat_|ostnat|mesh|grating|^c_[a-z]+_ca)')
# glass: snow slides off it as soon as it is pitched (the slanted window band of a control tower, a skylight)
GLASS = re.compile(r'(glass|sklo|window|okno)')

class Tris(np.ndarray):
    """the triangle index array, with .glass: a flag per triangle for faces drawn with a glass texture"""
    pass

def triangles(lod):
    """the drawn triangles of a LOD that can carry snow"""
    V = np.asarray(lod.vertices, dtype=np.float64)
    # proxy faces (one small triangle per door, window, lamp or antenna the engine draws from another model) are
    # never drawn: no snow lies on them
    skip = set()
    for sel in getattr(lod, 'named_selections', ()):
        if sel.name.lower().startswith('proxy:'):
            skip.update(sel.faces)
    # wire mesh, barbed wire and grass tufts (alpha textures of a fence, a gate, the grass on a bunker) hold no
    # layer of snow: it falls through them. As solid faces they made torn sheets over a crumpled fence
    textures = getattr(lod, 'textures', ()) or ()
    for sec in getattr(lod, 'sections', ()) or ():
        ti = getattr(sec, 'texture_index', -1)
        if 0 <= ti < len(textures) and SEE_THROUGH.search(textures[ti].replace('\\', '/').split('/')[-1].lower()):
            skip.update(range(sec.face_start, sec.face_end))
    tris = []
    glass_faces = set()
    for sec in getattr(lod, 'sections', ()) or ():
        ti = getattr(sec, 'texture_index', -1)
        if 0 <= ti < len(textures) and GLASS.search(textures[ti].replace('\\', '/').split('/')[-1].lower()):
            glass_faces.update(range(sec.face_start, sec.face_end))
    glass = []
    for fi, f in enumerate(lod.faces):
        if fi in skip:
            continue
        idx = f if isinstance(f, (list, tuple)) else f.indices
        for k in range(1, len(idx) - 1):
            tris.append((idx[0], idx[k], idx[k + 1]))
            glass.append(fi in glass_faces)
    T = np.asarray(tris, dtype=np.int64).reshape(-1, 3).view(Tris)
    T.glass = np.asarray(glass, dtype=bool)
    return V, T

def zbuffer(V, T, u0, v0, step, nu, nv, thin_rise=0.06, skip_vertical=False):
    """highest surface y at the points (u0 + i step, v0 + j step); nan where none. Also the normal y of that face"""
    Z = np.full((nv, nu), -np.inf)
    N = np.zeros((nv, nu))
    A = V[T[:, 0]]; B = V[T[:, 1]]; C = V[T[:, 2]]
    n = np.cross(B - A, C - A)
    ln = np.linalg.norm(n, axis=1)
    # rods, cables and antenna elements (triangles under 2.5 cm wide) hold no snow: they would be bridged into a lump.
    # Thin strips lying on a surface (the batten over a joint of roof sheets, a flashing) count: the snow covers them
    longest = np.maximum(np.maximum(np.linalg.norm(B - A, axis=1), np.linalg.norm(C - B, axis=1)), np.linalg.norm(A - C, axis=1))
    wide = (ln > 1e-9) & (ln / np.maximum(longest, 1e-9) >= 0.025)
    if skip_vertical:
        # fences and walls: near vertical faces (the sheets of a tin fence, the boards of a fence) hold no snow and
        # hide nothing from above but the rail or ledge right beside them, which the snow covers up to the sheet
        wide &= np.abs(n[:, 1]) / np.maximum(ln, 1e-12) >= 0.12
        # the level top of a board or plank (1 to 2.5 cm wide) is no rod: it holds a strip of snow. It is drawn a
        # little wider than it is, so the fine grid finds it along its whole length (its true edge is found later
        # on the model, where the snow ends)
        up = (ln > 1e-9) & (np.abs(n[:, 1]) / np.maximum(ln, 1e-12) >= 0.85)
        board = up & ~wide & (ln / np.maximum(longest, 1e-9) >= 0.01)
        wide |= board
        grow = np.where(board, 0.6 * step, 0.0)
    else:
        grow = None
    thin = (ln > 1e-9) & ~wide
    tag = getattr(T, 'glass', None)
    G = np.zeros((nv, nu), dtype=bool) if tag is not None else None
    Z = fill(Z, N, V, T, A, B, C, n, ln, wide, u0, v0, step, nu, nv, grow, tag, G)
    Zt = np.full((nv, nu), -np.inf)
    Nt = np.zeros((nv, nu))
    Zt = fill(Zt, Nt, V, T, A, B, C, n, ln, thin, u0, v0, step, nu, nv)
    # a strip narrower than the grid is hit by some samples only: it counts at their neighbours too
    Zp = np.pad(Zt, 1, constant_values=-np.inf)
    Zt = np.max(np.stack([Zp[1 + dj:1 + dj + nv, 1 + di:1 + di + nu] for dj in (-1, 0, 1) for di in (-1, 0, 1)]), 0)
    lying = np.isfinite(Z) & (Zt > Z) & (Zt - Z <= thin_rise)
    if os.environ.get('SZ_NOTHIN'):
        lying &= False
    Z = np.where(lying, Zt, Z)
    if G is not None:
        G &= ~lying
    Z[np.isinf(Z)] = np.nan
    zbuffer.glass = G
    return Z, N

def fill(Z, N, V, T, A, B, C, n, ln, ok, u0, v0, step, nu, nv, grow=None, tag=None, G=None):
    """the highest of the triangles ok at each grid point, into Z (and their normal y into N)"""
    nyabs = np.abs(n[:, 1]) / np.maximum(ln, 1e-12)
    xs = np.stack([A[:, 0], B[:, 0], C[:, 0]], 1)
    zs = np.stack([A[:, 2], B[:, 2], C[:, 2]], 1)
    gr = np.zeros(len(A)) if grow is None else grow
    i0 = np.clip(np.ceil((xs.min(1) - gr - u0) / step).astype(int), 0, nu)
    i1 = np.clip(np.floor((xs.max(1) + gr - u0) / step).astype(int), -1, nu - 1)
    j0 = np.clip(np.ceil((zs.min(1) - gr - v0) / step).astype(int), 0, nv)
    j1 = np.clip(np.floor((zs.max(1) + gr - v0) / step).astype(int), -1, nv - 1)
    for t in np.nonzero(ok & (i1 >= i0) & (j1 >= j0) & (nyabs > 1e-4))[0]:
        a, b, c = A[t], B[t], C[t]
        ii = np.arange(i0[t], i1[t] + 1)
        jj = np.arange(j0[t], j1[t] + 1)
        X, Zg = np.meshgrid(u0 + ii * step, v0 + jj * step)
        d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        if abs(d) < 1e-12:
            continue
        l1 = ((b[2] - c[2]) * (X - c[0]) + (c[0] - b[0]) * (Zg - c[2])) / d
        l2 = ((c[2] - a[2]) * (X - c[0]) + (a[0] - c[0]) * (Zg - c[2])) / d
        l3 = 1.0 - l1 - l2
        if gr[t] > 0:
            # widened by gr: each barycentric coordinate may go below zero by gr over the height of the triangle
            # above the opposite edge (in plan)
            area2 = abs(d)
            hs = []
            for p, q in ((b, c), (c, a), (a, b)):
                el = math.hypot(p[0] - q[0], p[2] - q[2])
                hs.append(area2 / max(el, 1e-9))
            m = (l1 >= -gr[t] / hs[0]) & (l2 >= -gr[t] / hs[1]) & (l3 >= -gr[t] / hs[2])
        else:
            e = -1e-6
            m = (l1 >= e) & (l2 >= e) & (l3 >= e)
        if not m.any():
            continue
        y = l1 * a[1] + l2 * b[1] + l3 * c[1]
        sub = Z[j0[t]:j1[t] + 1, i0[t]:i1[t] + 1]
        nsub = N[j0[t]:j1[t] + 1, i0[t]:i1[t] + 1]
        upd = m & (y > sub)
        sub[upd] = y[upd]
        nsub[upd] = nyabs[t]
        if G is not None:
            gsub = G[j0[t]:j1[t] + 1, i0[t]:i1[t] + 1]
            gsub[upd] = bool(tag[t])
    return Z

