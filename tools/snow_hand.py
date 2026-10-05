"""Hand-made snow: the building blocks of the per-model recipes in tools/hand (one per model, written and checked by
hand). A recipe picks the surfaces of its model that hold snow and lays each region of them as a blanket: its outline
smooth, its top following the surface (hollows filled, ridges rounded), its edge rounded where the surface falls away
(a cornice in deep snow) and run into a face that rises beside it.

    m = Model(name)                       the model's LOD 0 from the game, its top on a fine grid, its parts
    sel = m.tops(variant)                 the cells of the top a falling snow reaches (flat enough, above the ground)
    for reg, zc in m.regions(sel, variant):   the separate surfaces (gaps closed for the depth, split at steps)
        V, F = m.blanket(reg, zc, variant)    one blanket of one depth

A recipe (tools/hand/<name>.py) defines build(m, variant) -> list of (V, F); without one, auto() is used.
"""
import os, sys, math, importlib.util, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bake_snow as B
import odol_extract as X
import vis_height as VH
import snow_craft as SC

SKIRT = 0.02
DRING = ((0.0, 1.0), (0.55, 0.97), (0.92, 0.8), (1.0, 0.52), (0.82, 0.22), (0.25, None))
SRC = os.environ.get('SZ_SZBAKE', r'C:\Users\Gebruiker\Documents\Codex\DayZ\dayz-mission-audit\seasonz-mvp-20261004'
                     r'\runtime\profiles\client\szbake')
HAND = os.path.join(HERE, 'hand')
N4 = ((0, 1), (0, -1), (1, 0), (-1, 0))
N8 = N4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))
OPEN, WALL, TAPER = 0, 1, 2

_FILES = None


def files():
    """model name (as the craft names it) -> its bake file"""
    global _FILES
    if _FILES is None:
        used, _FILES = {}, {}
        for fn in sorted(os.listdir(SRC)):
            if fn.endswith('.txt'):
                with open(os.path.join(SRC, fn), encoding='latin-1') as fh:
                    first = fh.readline().split()
                if len(first) > 1 and first[0] == 'model':
                    _FILES[B.short_name(first[1], used)] = os.path.join(SRC, fn)
    return _FILES


# ---------------- grid tools ----------------
def sh(A, dj, di, fill):
    """A moved by (dj, di): out[j, i] = A[j - dj, i - di]"""
    out = np.full_like(A, fill)
    nv, nu = A.shape
    if abs(dj) >= nv or abs(di) >= nu:
        return out
    out[max(0, dj):nv + min(0, dj), max(0, di):nu + min(0, di)] = A[max(0, -dj):nv + min(0, -dj), max(0, -di):nu + min(0, -di)]
    return out


def dilate(M, r):
    for k in range(int(r)):
        out = M.copy()
        for dj, di in (N8 if k % 2 == 0 else N4):
            out |= sh(M, dj, di, False)
        M = out
    return M


def erode(M, r):
    for k in range(int(r)):
        out = M.copy()
        for dj, di in (N8 if k % 2 == 0 else N4):
            out &= sh(M, dj, di, False)
        M = out
    return M


def maxf(A, r):
    for k in range(int(r)):
        out = A.copy()
        for dj, di in (N8 if k % 2 == 0 else N4):
            out = np.maximum(out, sh(A, dj, di, -np.inf))
        A = out
    return A


def minf(A, r):
    for k in range(int(r)):
        out = A.copy()
        for dj, di in (N8 if k % 2 == 0 else N4):
            out = np.minimum(out, sh(A, dj, di, np.inf))
        A = out
    return A


def box(A, r):
    """sums over (2r+1)^2 windows"""
    r = int(r)
    if r <= 0:
        return A.astype(np.float64)
    c = np.cumsum(np.cumsum(np.pad(A.astype(np.float64), ((r + 1, r), (r + 1, r))), 0), 1)
    n = 2 * r + 1
    return c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]


def blur(A, W, r):
    """the average of A over the cells W within (2r+1)^2 windows"""
    W = W.astype(np.float64)
    return box(np.where(W > 0, A, 0.0) * W, r) / np.maximum(box(W, r), 1e-12)


def distance(M, kmax):
    """distance (cells) from each cell of M to the nearest cell outside it, up to kmax"""
    d = np.zeros(M.shape)
    cur = M.copy()
    for k in range(int(kmax)):
        if not cur.any():
            break
        d[cur] += 1.0
        out = cur.copy()
        for dj, di in (N4 if k % 2 == 0 else N8):
            out &= sh(cur, dj, di, False)
        cur = out
    return np.where(M, d - 0.5, 0.0)


def label(M, lx, lz):
    """components of M joined by the links lx ((j, i) with (j, i+1)) and lz ((j, i) with (j+1, i)): labels 0..n-1, -1"""
    big = M.size
    lab = np.where(M, np.arange(M.size).reshape(M.shape), big)
    for _ in range(5000):
        new = lab.copy()
        m = np.minimum(lab[:, :-1], lab[:, 1:])
        new[:, :-1] = np.where(lx, np.minimum(new[:, :-1], m), new[:, :-1])
        new[:, 1:] = np.where(lx, np.minimum(new[:, 1:], m), new[:, 1:])
        m = np.minimum(lab[:-1, :], lab[1:, :])
        new[:-1, :] = np.where(lz, np.minimum(new[:-1, :], m), new[:-1, :])
        new[1:, :] = np.where(lz, np.minimum(new[1:, :], m), new[1:, :])
        flat = new.ravel()
        ok = flat < big
        for _ in range(6):
            flat[ok] = flat[flat[ok]]
        new = flat.reshape(M.shape)
        if np.array_equal(new, lab):
            break
        lab = new
    out = np.full(M.shape, -1, dtype=np.int64)
    u, inv = np.unique(lab[M], return_inverse=True)
    out[M] = inv.ravel()
    return out, len(u)


def contours(Fv, level=0.5):
    """closed iso lines of Fv at level (marching squares): loops of (i, j) grid points with the higher side on the left"""
    Fv = np.pad(Fv, 1, constant_values=level - 1.0)
    nv, nu = Fv.shape
    hi = Fv > level
    a, b, c, d = hi[:-1, :-1], hi[:-1, 1:], hi[1:, 1:], hi[1:, :-1]
    case = a * 1 + b * 2 + c * 4 + d * 8
    NH = nv * nu

    def hpt(j, i):
        f0, f1 = Fv[j, i], Fv[j, i + 1]
        return (i + (level - f0) / (f1 - f0) - 1.0, j - 1.0)

    def vpt(j, i):
        f0, f1 = Fv[j, i], Fv[j + 1, i]
        return (i - 1.0, j + (level - f0) / (f1 - f0) - 1.0)

    TAB = {1: ((3, 0),), 2: ((0, 1),), 3: ((3, 1),), 4: ((1, 2),), 6: ((0, 2),), 7: ((3, 2),), 8: ((2, 3),),
           9: ((0, 2),), 11: ((1, 2),), 12: ((1, 3),), 13: ((0, 1),), 14: ((3, 0),)}
    segs = []
    js, iis = np.nonzero((case > 0) & (case < 15))
    for j, i in zip(js.tolist(), iis.tolist()):
        cs = int(case[j, i])
        eid = (j * nu + i, NH + j * nu + i + 1, (j + 1) * nu + i, NH + j * nu + i)
        if cs in (5, 10):
            centre = (Fv[j, i] + Fv[j, i + 1] + Fv[j + 1, i] + Fv[j + 1, i + 1]) / 4.0 > level
            if cs == 5:
                pr = ((0, 1), (2, 3)) if centre else ((3, 0), (1, 2))
            else:
                pr = ((3, 0), (1, 2)) if centre else ((0, 1), (2, 3))
        else:
            pr = TAB[cs]
        for e0, e1 in pr:
            segs.append((eid[e0], eid[e1]))
    pts = {}

    def point(e):
        if e not in pts:
            if e < NH:
                pts[e] = hpt(e // nu, e % nu)
            else:
                k = e - NH
                pts[e] = vpt(k // nu, k % nu)
        return pts[e]

    by = collections.defaultdict(list)
    for k, (e0, e1) in enumerate(segs):
        by[e0].append(k)
        by[e1].append(k)
    used = np.zeros(len(segs), bool)
    loops = []
    for k0 in range(len(segs)):
        if used[k0]:
            continue
        used[k0] = True
        e_start, e = segs[k0]
        chain = [e_start, e]
        while e != e_start:
            nxt = [k for k in by[e] if not used[k]]
            if not nxt:
                break
            k = nxt[0]
            used[k] = True
            e = segs[k][1] if segs[k][0] == e else segs[k][0]
            chain.append(e)
        if len(chain) > 3 and chain[-1] == chain[0]:
            loop = np.array([point(x) for x in chain[:-1]])
            loops.append(loop)
    out = []
    for L in loops:
        # the higher side on the left: probe left of the longest segment
        dv = np.roll(L, -1, 0) - L
        k = int(np.argmax(np.hypot(dv[:, 0], dv[:, 1])))
        p = (L[k] + L[(k + 1) % len(L)]) / 2.0
        t = dv[k] / max(1e-9, float(np.hypot(*dv[k])))
        q = p + 0.25 * np.array([-t[1], t[0]])
        if bilinear(Fv, q[0] + 1.0, q[1] + 1.0) < level:
            L = L[::-1]
        out.append(L)
    return out


def bilinear(A, x, y):
    """A at (x = column, y = row), clamped"""
    nv, nu = A.shape
    x = np.clip(np.asarray(x, dtype=np.float64), 0, nu - 1.000001)
    y = np.clip(np.asarray(y, dtype=np.float64), 0, nv - 1.000001)
    i0 = np.floor(x).astype(int)
    j0 = np.floor(y).astype(int)
    fx, fy = x - i0, y - j0
    return (A[j0, i0] * (1 - fx) * (1 - fy) + A[j0, i0 + 1] * fx * (1 - fy) + A[j0 + 1, i0] * (1 - fx) * fy +
            A[j0 + 1, i0 + 1] * fx * fy)


def extend(A, have, want, steps=60):
    """A carried from the cells have into the cells want (each step the average of the neighbours that have it)"""
    A = np.where(have, A, 0.0)
    have = have.copy()
    for _ in range(steps):
        nb = dilate(have, 1) & want & ~have
        if not nb.any():
            break
        A = np.where(nb, blur(A, have, 1), A)
        have = have | nb
    return A, have


def small_holes(M, area_cells):
    """the holes of M (not open to the border) of at most area_cells"""
    H_ = ~M
    lx = H_[:, 1:] & H_[:, :-1]
    lz = H_[1:, :] & H_[:-1, :]
    lab, n = label(H_, lx, lz)
    if n == 0:
        return np.zeros(M.shape, bool)
    cnt = np.bincount(lab[lab >= 0], minlength=n)
    edge = np.unique(np.concatenate([lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]]))
    ok = cnt <= area_cells
    ok[edge[edge >= 0]] = False
    return (lab >= 0) & ok[np.maximum(lab, 0)]


def simplify_loop(L, tol):
    """Douglas-Peucker on a closed loop"""
    n = len(L)
    if n < 8:
        return L
    d = np.hypot(*(L - L[0]).T)
    k = int(np.argmax(d))
    keep = np.zeros(n, bool)
    keep[0] = keep[k] = True
    stack = [(0, k), (k, n)]
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        pa, pb = L[a], L[b % n]
        seg = pb - pa
        ln = float(np.hypot(*seg))
        idx = np.arange(a + 1, b)
        P = L[idx % n] - pa
        if ln < 1e-12:
            dist = np.hypot(P[:, 0], P[:, 1])
        else:
            dist = np.abs(P[:, 0] * seg[1] - P[:, 1] * seg[0]) / ln
        m = int(np.argmax(dist))
        if dist[m] > tol:
            c = int(idx[m])
            keep[c % n] = True
            stack.append((a, c))
            stack.append((c, b))
    return L[keep]


def resample_loop(L, smax):
    out = []
    n = len(L)
    for k in range(n):
        a, b = L[k], L[(k + 1) % n]
        m = max(1, int(math.ceil(float(np.hypot(*(b - a))) / smax)))
        for t in range(m):
            out.append(a + (b - a) * (t / m))
    return np.array(out)


class UF:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, x):
        p = self.p
        while p[x] != x:
            p[x] = p[p[x]]
            x = p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


# ---------------- the model ----------------
class Model:
    def __init__(self, name, path=None, g=None):
        self.name = name
        self.path = path or files()[name]
        m = B.parse(self.path)
        self.m = m
        self.shape = m.shape
        lod = X.visual_lod(X.read_model(m.shape))
        V, T = VH.triangles(lod)
        self.glass_t = np.asarray(getattr(T, 'glass', np.zeros(len(T), bool)), bool)
        self.V = np.asarray(V, dtype=np.float64)
        self.T = np.asarray(T, dtype=np.int64).reshape(-1, 3)
        self.cls, step, self.min_area, self.kind = SC.params(m, self.V)
        self.rough = SC.is_rough(m)
        bn = SC.base_name(m.shape)
        self.skind = 'slick' if SC.SLICK.match(bn) else ('rough' if self.rough else None)
        self.scls = 'any' if self.rough else self.cls
        self.ground = SC.ground_for(self.path, self.V)
        self.size = max(float(np.ptp(self.V[:, 0])), float(np.ptp(self.V[:, 2])), 0.5)
        if g is None:
            g = 0.01 if self.cls == 'wall' else float(np.clip(self.size / 500.0, 0.01, 0.05))
        self.g = g
        self._faces()
        self._raster()
        self._bvh()

    def _faces(self):
        V, T = self.V, self.T
        A, Bv, C = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
        n = np.cross(Bv - A, C - A)
        ln = np.linalg.norm(n, axis=1)
        longest = np.max(np.stack([np.linalg.norm(Bv - A, axis=1), np.linalg.norm(C - Bv, axis=1),
                                   np.linalg.norm(A - C, axis=1)]), 0)
        self.ny_t = np.abs(n[:, 1]) / np.maximum(ln, 1e-12)
        good = ln > 1e-10
        wide = good & (ln / np.maximum(longest, 1e-9) >= 0.025)
        key = np.round(V / 0.001).astype(np.int64)
        _, vid = np.unique(key, axis=0, return_inverse=True)
        vid = vid.ravel()
        TV = vid[T]
        # parts: triangles joined through shared corners
        uf = UF(len(T))
        first = {}
        for t, row in enumerate(TV.tolist()):
            for v in row:
                if v in first:
                    uf.union(t, first[v])
                else:
                    first[v] = t
        roots = np.array([uf.find(t) for t in range(len(T))])
        _, self.part_t = np.unique(roots, return_inverse=True)
        self.part_t = self.part_t.ravel()
        # thin triangles joined by an edge to a wide one belong to a surface; the others are rods and wires
        e = np.concatenate([TV[:, [0, 1]], TV[:, [1, 2]], TV[:, [2, 0]]])
        es = np.sort(e, axis=1)
        _, einv = np.unique(es, axis=0, return_inverse=True)
        einv = einv.ravel()
        fe = einv.reshape(3, -1).T
        by_edge = collections.defaultdict(list)
        for t in range(len(T)):
            for k in range(3):
                by_edge[int(fe[t, k])].append(t)
        sheet = wide.copy()
        todo = [int(t) for t in np.nonzero(wide)[0]]
        while todo:
            t = todo.pop()
            for k in range(3):
                for u in by_edge[int(fe[t, k])]:
                    if not sheet[u] and good[u]:
                        sheet[u] = True
                        todo.append(u)
        self.good_t, self.wide_t, self.occ_t = good, wide, sheet & good

    def _raster(self):
        V, T, g = self.V, self.T, self.g
        pad = 6
        mn, mx = V.min(0), V.max(0)
        self.u0 = math.floor(mn[0] / g) * g - pad * g
        self.v0 = math.floor(mn[2] / g) * g - pad * g
        self.nu = int(math.ceil((mx[0] - self.u0) / g)) + pad + 1
        self.nv = int(math.ceil((mx[2] - self.v0) / g)) + pad + 1
        Z = np.full((self.nv, self.nu), -np.inf)
        TID = np.full((self.nv, self.nu), -1, dtype=np.int64)
        self._fill(Z, TID, self.occ_t)
        # thin strips lying on a surface (a batten, a flashing, the edge of a board) count; rods above do not
        Zt = np.full((self.nv, self.nu), -np.inf)
        Tt = np.full((self.nv, self.nu), -1, dtype=np.int64)
        self._fill(Zt, Tt, self.good_t & ~self.occ_t)
        lying = np.isfinite(Z) & np.isfinite(Zt) & (Zt > Z) & (Zt - Z <= 0.06)
        Z = np.where(lying, Zt, Z)
        TID = np.where(lying, Tt, TID)
        self.valid = np.isfinite(Z) & (TID >= 0)
        self.Z = np.where(self.valid, Z, np.nan)
        self.TID = TID
        self.NYF = np.where(self.valid, self.ny_t[np.maximum(TID, 0)], 0.0)
        self.GLASS = self.valid & self.glass_t[np.maximum(TID, 0)]
        self.PART = np.where(self.valid, self.part_t[np.maximum(TID, 0)], -1)
        # the slope the snow feels: that of the surface over about 12 cm, steps left out
        g = self.g
        Zn = np.where(self.valid, self.Z, 0.0)
        tau = 0.03 + 2.0 * g
        lx = self.valid[:, 1:] & self.valid[:, :-1] & (np.abs(Zn[:, 1:] - Zn[:, :-1]) <= tau)
        lz = self.valid[1:, :] & self.valid[:-1, :] & (np.abs(Zn[1:, :] - Zn[:-1, :]) <= tau)
        gx = np.zeros(Z.shape)
        cx = np.zeros(Z.shape)
        d = np.where(lx, (Zn[:, 1:] - Zn[:, :-1]) / g, 0.0)
        gx[:, :-1] += d
        cx[:, :-1] += lx
        gx[:, 1:] += d
        cx[:, 1:] += lx
        gz = np.zeros(Z.shape)
        cz = np.zeros(Z.shape)
        d = np.where(lz, (Zn[1:, :] - Zn[:-1, :]) / g, 0.0)
        gz[:-1, :] += d
        cz[:-1, :] += lz
        gz[1:, :] += d
        cz[1:, :] += lz
        hx = (cx > 0)
        hz = (cz > 0)
        gx = np.where(hx, gx / np.maximum(cx, 1), 0.0)
        gz = np.where(hz, gz / np.maximum(cz, 1), 0.0)
        # the slope of each cell on its own (a chamfer, a steep strip along an edge): the averaged slope below made it
        # look level beside a flat tread and it was drawn into the tread's blanket
        self.G0 = np.hypot(gx, gz)
        r = max(1, int(round(0.06 / g)))
        gx = np.where(hx, blur(gx, hx, r), 0.0)
        gz = np.where(hz, blur(gz, hz, r), 0.0)
        ny = 1.0 / np.sqrt(1.0 + gx * gx + gz * gz)
        # a cell with no linked neighbour (a lone strip): its face's own slope
        self.NYE = np.where(hx | hz, ny, self.NYF)
        self.lx, self.lz = lx, lz

    def _fill(self, Z, TID, ok):
        V, T, g = self.V, self.T, self.g
        A, Bv, C = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
        xs = np.stack([A[:, 0], Bv[:, 0], C[:, 0]], 1)
        zs = np.stack([A[:, 2], Bv[:, 2], C[:, 2]], 1)
        i0 = np.clip(np.ceil((xs.min(1) - self.u0) / g).astype(int), 0, self.nu)
        i1 = np.clip(np.floor((xs.max(1) - self.u0) / g).astype(int), -1, self.nu - 1)
        j0 = np.clip(np.ceil((zs.min(1) - self.v0) / g).astype(int), 0, self.nv)
        j1 = np.clip(np.floor((zs.max(1) - self.v0) / g).astype(int), -1, self.nv - 1)
        for t in np.nonzero(ok & (i1 >= i0) & (j1 >= j0) & (self.ny_t > 1e-4))[0]:
            a, b, c = A[t], Bv[t], C[t]
            ii = np.arange(i0[t], i1[t] + 1)
            jj = np.arange(j0[t], j1[t] + 1)
            X_, Zg = np.meshgrid(self.u0 + ii * g, self.v0 + jj * g)
            dd = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
            if abs(dd) < 1e-12:
                continue
            l1 = ((b[2] - c[2]) * (X_ - c[0]) + (c[0] - b[0]) * (Zg - c[2])) / dd
            l2 = ((c[2] - a[2]) * (X_ - c[0]) + (a[0] - c[0]) * (Zg - c[2])) / dd
            l3 = 1.0 - l1 - l2
            msk = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
            if not msk.any():
                continue
            y = l1 * a[1] + l2 * b[1] + l3 * c[1]
            sub = Z[j0[t]:j1[t] + 1, i0[t]:i1[t] + 1]
            tsub = TID[j0[t]:j1[t] + 1, i0[t]:i1[t] + 1]
            upd = msk & (y > sub)
            sub[upd] = y[upd]
            tsub[upd] = t

    def _bvh(self):
        from mathutils.bvhtree import BVHTree
        T = self.T[self.occ_t]
        self.bvh = BVHTree.FromPolygons([tuple(p) for p in self.V], [tuple(int(i) for i in t) for t in T],
                                        all_triangles=True, epsilon=0.0)

    # ---------- coordinates ----------
    def xz(self, i, j):
        return self.u0 + np.asarray(i) * self.g, self.v0 + np.asarray(j) * self.g

    def ij(self, x, z):
        return (np.asarray(x) - self.u0) / self.g, (np.asarray(z) - self.v0) / self.g

    def thick(self, variant):
        return SC.THICK[self.kind][variant]

    def parts_table(self):
        """per part: triangles, box (x0 x1, y0 y1, z0 z1) and the area of its top that the snow reaches"""
        rows = []
        for p in range(int(self.part_t.max()) + 1):
            sel = self.T[self.part_t == p]
            pv = self.V[np.unique(sel.ravel())]
            top = float((self.PART == p).sum()) * self.g * self.g
            rows.append((p, len(sel), pv[:, 0].min(), pv[:, 0].max(), pv[:, 1].min(), pv[:, 1].max(), pv[:, 2].min(),
                         pv[:, 2].max(), top))
        return rows

    # ---------- selections ----------
    def tops(self, variant, parts=None, exclude=None, box=None, ny_min=None, slope=True, steep=1.6):
        """the cells a falling snow reaches and that hold it in this depth: flat enough (the slope the snow feels),
        above the terrain's own cover, no pitched glass; limited to some parts, or a box (x0, z0, x1, z1, y0, y1).
        steep: the steepest a cell may be on its own (rise per run; 0.6 keeps the chamfers of furniture and treads
        bare, which hung their snow as curtains)"""
        M = self.valid & (self.Z >= self.ground + 0.25)
        M &= ~(self.GLASS & (self.NYF < 0.8))
        if slope:
            w = SC.slope_w(self.scls, variant, self.NYE, self.skind)
            M &= w > 0.05
            # a face past the slope limit holds nothing even where the surface around it is flatter
            M &= ~((self.NYF < 0.45) & (self.NYE < 0.6))
            M &= self.G0 <= steep
        if ny_min is not None:
            M &= self.NYE >= ny_min
        if parts is not None:
            M &= np.isin(self.PART, list(parts))
        if exclude is not None:
            M &= ~np.isin(self.PART, list(exclude))
        if box is not None:
            x0, z0, x1, z1 = box[:4]
            X_, Zg = self.xz(np.arange(self.nu)[None, :], np.arange(self.nv)[:, None])
            inb = (X_ >= x0) & (X_ <= x1) & (Zg >= z0) & (Zg <= z1)
            if len(box) > 4:
                inb = inb & (self.Z >= box[4]) & (self.Z <= box[5])
            M &= inb
        return M

    def regions(self, M, variant, close=None, tau=None, min_area=None):
        """the separate surfaces of M for this depth: gaps narrower than close bridged (deeper snow bridges more),
        joined where neighbours lie within tau in height; with the height field for each (gaps filled)"""
        g = self.g
        t = self.thick(variant)
        if close is None:
            close = min(0.10, 0.03 + 0.35 * t)
        if tau is None:
            # a step lower than about half the depth is buried (a beam on planks, a tile row, a kerb); a riser stays
            # a step in every depth (merged in the deepest only, a stair turned into a ramp from one stage to the next)
            tau = max(0.03 + 2.0 * g, min(0.06, 0.45 * t))
        if min_area is None:
            min_area = self.min_area
        rc = int(round(close / g))
        Zm = np.where(M, self.Z, -np.inf)
        if rc > 0:
            Mc = erode(dilate(M, rc), rc) | M
            Zc = minf(maxf(Zm, rc), rc)
            new = Mc & ~M
            Mc &= ~new | np.isfinite(Zc)
            Zc = np.where(M, self.Z, Zc)
        else:
            Mc, Zc = M, np.where(M, self.Z, np.nan)
        Zn = np.where(Mc, Zc, 0.0)
        # neighbours join along a slope the snow holds (up to about 60 degrees), and across a buried step only
        # between two level cells (else a chain of such steps walked down the steep side of a well rim)
        slope_tol = 1.8 * g + 0.01
        flat = self.NYE >= 0.85
        dx = np.abs(Zn[:, 1:] - Zn[:, :-1])
        dz = np.abs(Zn[1:, :] - Zn[:-1, :])
        lx = Mc[:, 1:] & Mc[:, :-1] & ((dx <= slope_tol) | ((dx <= tau) & flat[:, 1:] & flat[:, :-1]))
        lz = Mc[1:, :] & Mc[:-1, :] & ((dz <= slope_tol) | ((dz <= tau) & flat[1:, :] & flat[:-1, :]))
        lab, n = label(Mc, lx, lz)
        out = []
        cnt = np.bincount(lab[lab >= 0], minlength=n)
        for k in range(n):
            if cnt[k] * g * g < min_area:
                continue
            out.append((lab == k, np.where(lab == k, Zc, np.nan)))
        return out

    # ---------- the blanket ----------
    def blanket(self, R, Zc, variant, depth=1.0, over=None, rim='round', fill=None, smooth=None, narrow=True,
                spacing=None, opening=0.0, soften=None, holes=0.01, shoulder=0.45):
        """one blanket of snow over the region R (its height field Zc) in this depth: (V, F) or None. depth scales
        the variant's depth, over the overhang of the rounded edge; rim 'round' (a rounded edge) or 'taper' (thins
        out, rough stone); opening takes off strips narrower than about twice it; soften rounds the outline (cells)"""
        from mathutils import Vector
        from mathutils.geometry import delaunay_2d_cdt
        g = self.g
        t = self.thick(variant) * depth
        over_given = over is not None
        if over is None:
            over = SC.overhang_of(self.cls, variant, self.thick(variant))
        if fill is None:
            fill = min(0.12, 0.6 * t)
        js, iis = np.nonzero(R)
        if len(js) == 0:
            return None
        m = 8 + int(math.ceil(0.25 / g))
        ja, jb = max(0, js.min() - m), min(self.nv, js.max() + m + 1)
        ia, ib = max(0, iis.min() - m), min(self.nu, iis.max() + m + 1)
        M = R[ja:jb, ia:ib].copy()
        Z = np.where(M, Zc[ja:jb, ia:ib], np.nan)
        if opening > 0:
            ro = int(round(opening / g))
            M &= dilate(erode(M, ro), ro)
            if not M.any():
                return None
        if holes > 0:
            # pits and slots in the surface (a joint, a nail head, the foot of a post): the snow closes over them
            hm = small_holes(M, int(holes / (g * g)))
            if hm.any():
                Zh, _ = extend(np.where(M, Z, 0.0), M, hm)
                Z = np.where(hm, Zh, Z)
                M = M | hm
        NYE = self.NYE[ja:jb, ia:ib]
        Zf = np.where(M, Z, 0.0)
        # hollows filled (up to fill): the closed surface over about 12 cm
        rf = max(1, int(round(0.12 / g)))
        Zcl = minf(maxf(np.where(M, Zf, -np.inf), rf), rf)
        Zs = np.where(M, np.minimum(np.where(np.isfinite(Zcl), Zcl, Zf), Zf + fill), 0.0)
        # depth: by the slope, and no more than the support is wide
        w = SC.slope_w(self.scls, variant, NYE, self.skind)
        D = t * np.where(M, w, 0.0)
        dist = None
        if narrow:
            dist = distance(M, int(math.ceil(0.15 / g)) + 2) * g
            W = 2.0 * np.where(M, maxf(np.where(M, dist, -np.inf), int(math.ceil(0.12 / g))), 0.0)
            # on a narrow support the snow stands about as high as it is wide (a backrest top, a rail, a plank)
            D = np.minimum(D, 0.8 * W + 0.02)
        if not over_given:
            # the cornice grows where snow creeps over the eave of a wide roof; a tread, a seat or a cover holds a
            # small rounded edge (with the roof's 12 cm every tread end hung over the side of a stair as a bulb)
            dd = distance(M, int(math.ceil(1.0 / g)) + 2) * g
            wide = 2.0 * float(dd.max())
            over *= float(np.clip(wide / 2.0, 0.3, 1.0))
        if rim == 'taper':
            # rough stone: the snow thins out to its edge
            if dist is None:
                dist = distance(M, int(math.ceil(0.15 / g)) + 2) * g
            tw = max(0.03, 1.5 * t)
            x = np.clip(dist / tw, 0.0, 1.0)
            D = D * (x * x * (3 - 2 * x))
        D = np.where(M, blur(D, M, max(1, int(round(0.08 / g)))), 0.0)
        S = Zs + D
        rs = max(1, int(round((smooth if smooth is not None else max(0.04, 0.5 * t)) / g)))
        Sb = blur(S, M, rs)
        # (the hollows are filled in Zs already: the smoothing rounds, it does not pile up; on a slope it would
        # carry the height of the upper part down to the lower edge)
        S = np.where(M, np.clip(Sb, Zs + 0.8 * D, Zs + 1.15 * D + 0.005), 0.0)
        if shoulder and rim == 'round':
            # the rounded shoulder of a snow edge (a radius of about half the depth): the top bends down before an
            # open edge; against a face rising beside it (a riser, a wall) the snow stays full
            Zm_ = self.Z[ja:jb, ia:ib]
            ring_ = dilate(M, 1) & ~M
            Zin = np.where(M, Zs, -np.inf)
            near = maxf(Zin, 1)
            wall0 = ring_ & np.isfinite(Zm_) & (np.nan_to_num(Zm_, nan=-1e9) > near + 0.02)
            rr = float(np.clip(shoulder * t, 0.0, 0.12))
            if rr >= 1.5 * g:
                rc_ = int(math.ceil(rr / g)) + 1
                Wc = dilate(wall0, rc_) & ~M
                do = distance(M | Wc, rc_ + 2) * g
                r_ = np.clip(shoulder * np.maximum(D, 0.0), 0.0, 0.12)
                x_ = np.clip(r_ - do, 0.0, None)
                drop = r_ - np.sqrt(np.maximum(r_ * r_ - x_ * x_, 0.0))
                S = np.where(M, np.maximum(S - drop, Zs + 0.15 * D), S)
        # the fields carried a few cells past the edge (the edge lies between cells)
        Sx, Zx = S.copy(), Zs.copy()
        have = M.copy()
        for _ in range(4):
            nb = dilate(have, 1) & ~have
            if not nb.any():
                break
            Sx = np.where(nb, blur(Sx, have, 1), Sx)
            Zx = np.where(nb, blur(Zx, have, 1), Zx)
            have |= nb
        # the outline: the edge of the region, its corners softened
        if soften is None:
            # deeper snow smooths over smaller features of the outline (plank ends, stone joints)
            soften = max(2, int(round(0.35 * t / g)))
        sr = max(1, int(soften))
        Fm = box(M.astype(np.float64), sr) / float((2 * sr + 1) ** 2)
        loops = contours(Fm, 0.5)
        if not loops:
            return None
        sp = spacing if spacing is not None else float(np.clip(self.size / 40.0, 0.03, 0.3))
        smax = max(2 * g, min(sp, 0.25))
        L2 = []
        for L in loops:
            L = simplify_loop(L, 0.5)
            if len(L) < 3:
                continue
            area = 0.5 * abs(float(np.sum(L[:, 0] * np.roll(L[:, 1], -1) - np.roll(L[:, 0], -1) * L[:, 1]))) * g * g
            if area < 0.25 * self.min_area:
                continue
            L2.append(resample_loop(L, smax / g))
        if not L2:
            return None
        # points inside, away from the outline
        si = max(2.0 * g, sp) / g
        kk = int(math.ceil(0.5 * si)) + 1
        inner = erode(M, kk)
        gi = np.arange(0, M.shape[1], max(1, int(round(si))))
        gj = np.arange(0, M.shape[0], max(1, int(round(si))))
        GI, GJ = np.meshgrid(gi, gj)
        okp = inner[GJ, GI]
        pts = [tuple(p) for L in L2 for p in L] + list(zip(GI[okp].astype(float), GJ[okp].astype(float)))
        edges = []
        k0 = 0
        for L in L2:
            n = len(L)
            edges += [(k0 + k, k0 + (k + 1) % n) for k in range(n)]
            k0 += n
        nb_pts = k0
        res = delaunay_2d_cdt([Vector(p) for p in pts], edges, [], 0, 1e-6, True)
        vco, _, faces, orig_v = res[0], res[1], res[2], res[3]
        P2 = np.array([(v.x, v.y) for v in vco])
        tri = [f for f in faces if len(f) == 3]
        if not tri:
            return None
        Tr = np.array(tri, dtype=np.int64)
        cen = P2[Tr].mean(1)
        inside = inside_loops(cen, L2)
        Tr = Tr[inside]
        if len(Tr) == 0:
            return None
        # which output vertex is on which loop point (for the rims)
        onl = np.full(len(P2), -1, dtype=np.int64)
        for k, ov in enumerate(orig_v):
            for o in ov:
                if o < nb_pts:
                    onl[k] = o
        # heights: the top sampled a little inside at the outline
        topy = bilinear(Sx, P2[:, 0], P2[:, 1])
        supy = bilinear(Zx, P2[:, 0], P2[:, 1])
        X3 = np.column_stack([self.u0 + (P2[:, 0] + ia) * g, topy, self.v0 + (P2[:, 1] + ja) * g])
        nrm = np.cross(X3[Tr[:, 1]] - X3[Tr[:, 0]], X3[Tr[:, 2]] - X3[Tr[:, 0]])
        flip = nrm[:, 1] < 0
        Tr[flip] = Tr[flip][:, [0, 2, 1]]
        Vl = [tuple(p) for p in X3]
        Fl = [tuple(f) for f in Tr.tolist()]
        # the rims, along each loop
        vof = {int(o): k for k, o in enumerate(onl) if o >= 0}
        from mathutils import Vector as Vec
        K = len(DRING)
        k0 = 0
        for L in L2:
            n = len(L)
            ids = [vof.get(k0 + k, -1) for k in range(n)]
            k0 += n
            if min(ids) < 0:
                continue
            W3 = np.array([X3[i] for i in ids])
            tang = np.roll(W3, -1, 0) - np.roll(W3, 1, 0)
            # the region is on the left of the loop: outward is to the right
            nx, nz = tang[:, 2], -tang[:, 0]
            ln = np.maximum(np.hypot(nx, nz), 1e-12)
            nx, nz = nx / ln, nz / ln
            # the outward directions averaged along the outline (on a ragged outline neighbouring rims pointed apart
            # and crossed: a saw of teeth along a deep cornice)
            wts = (1.0, 2.0, 3.0, 2.0, 1.0)
            sx = sum(w_ * np.roll(nx, s) for w_, s in zip(wts, (-2, -1, 0, 1, 2)))
            sz = sum(w_ * np.roll(nz, s) for w_, s in zip(wts, (-2, -1, 0, 1, 2)))
            ln = np.maximum(np.hypot(sx, sz), 1e-12)
            nx, nz = sx / ln, sz / ln
            rings = []
            reach = []
            types = []
            for k in range(n):
                p = W3[k]
                ys = supy[ids[k]]
                h = max(0.0, p[1] - ys)
                typ = OPEN if rim == 'round' else TAPER
                ext = 0.0
                hit = None
                for dy in (0.012, 0.035):
                    o = Vec((p[0] - 0.01 * nx[k], ys + dy, p[2] - 0.01 * nz[k]))
                    loc, _, _, dd = self.bvh.ray_cast(o, Vec((nx[k], 0.0, nz[k])), 0.08)
                    if loc is not None and (hit is None or dd < hit):
                        hit = dd
                if hit is not None:
                    # a wall lower than the snow (a curb beside a tread): the snow rounds off over it
                    q = Vec((p[0] + nx[k] * (hit + 0.005), p[1] + 0.3, p[2] + nz[k] * (hit + 0.005)))
                    wl = self.bvh.ray_cast(q, Vec((0.0, -1.0, 0.0)), 0.6)[0]
                    if wl is not None and wl.y < p[1] - 0.3 * h:
                        typ = OPEN
                    else:
                        typ = WALL
                        ext = min(0.06, max(0.0, hit - 0.01) + 0.02)
                types.append(typ)
                reach.append(min(over, 0.75 * h) if typ == OPEN else ext)
            reach = np.array(reach)
            # the reach the least of its neighbours', then smoothed: no rim reaches out past the ones beside it
            op = np.array([t_ == OPEN for t_ in types])
            rmin = np.minimum.reduce([np.roll(reach, s) for s in (-2, -1, 0, 1, 2)])
            rs_ = sum(w_ * np.roll(rmin, s) for w_, s in zip(wts, (-2, -1, 0, 1, 2))) / sum(wts)
            reach = np.where(op, np.minimum(reach, rs_), reach)
            # in a hollow bend the outward reaches converge: cut back so the rims do not cross
            for _ in range(4):
                for k in range(n):
                    k2 = (k + 1) % n
                    e = W3[k2] - W3[k]
                    L2e = e[0] * e[0] + e[2] * e[2]
                    if L2e < 1e-10 or types[k] == WALL or types[k2] == WALL:
                        continue
                    dd = (nx[k2] * reach[k2] - nx[k] * reach[k]) * e[0] + (nz[k2] * reach[k2] - nz[k] * reach[k]) * e[2]
                    if dd < -0.6 * L2e:
                        s = 0.6 * L2e / -dd
                        reach[k] *= s
                        reach[k2] *= s
            for k in range(n):
                p = W3[k]
                ys = supy[ids[k]]
                h = max(0.0, p[1] - ys)
                ring = [ids[k]]
                for fr, fu in DRING[1:]:
                    if types[k] == OPEN:
                        o = reach[k] * fr
                        y = ys - SKIRT if fu is None else ys + h * fu
                    elif types[k] == WALL:
                        o = reach[k]
                        y = ys - SKIRT if fu is None else p[1]
                    else:
                        o = 0.0
                        y = ys - SKIRT if fu is None else p[1]
                    Vl.append((p[0] + nx[k] * o, y, p[2] + nz[k] * o))
                    ring.append(len(Vl) - 1)
                rings.append(ring)
            for k in range(n):
                ra, rb = rings[k], rings[(k + 1) % n]
                for j in range(K - 1):
                    # outward (the loop runs with the region on its left)
                    Fl.append((ra[j], rb[j + 1], ra[j + 1]))
                    Fl.append((ra[j], rb[j], rb[j + 1]))
        Va = np.array(Vl, dtype=np.float64)
        Fa = np.array(Fl, dtype=np.int64)
        ar = np.linalg.norm(np.cross(Va[Fa[:, 1]] - Va[Fa[:, 0]], Va[Fa[:, 2]] - Va[Fa[:, 0]]), axis=1)
        Fa = Fa[ar > 1e-10]
        return Va, Fa


def join(meshes):
    Vs, Fs, k = [], [], 0
    for msh in meshes:
        if msh is None:
            continue
        V, F = msh
        Vs.append(np.asarray(V))
        Fs.append(np.asarray(F) + k)
        k += len(V)
    if not Vs:
        return None
    return np.vstack(Vs), np.vstack(Fs)


def auto(m, variant, **style):
    """the plain recipe: every surface the snow reaches, each region its blanket"""
    out = []
    for R, Zc in m.regions(m.tops(variant), variant):
        out.append(m.blanket(R, Zc, variant, **style))
    return join(out)


def recipe(name):
    p = os.path.join(HAND, name + '.py')
    if not os.path.exists(p):
        return None
    spec = importlib.util.spec_from_file_location('hand_' + name, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build(m, variant):
    """the snow of a model in one depth: its recipe's, or auto"""
    r = recipe(m.name)
    if r is not None:
        return r.build(m, variant)
    return auto(m, variant)

def inside_loops(P, loops):
    """even-odd test of the points P (n, 2) against the closed loops"""
    inside = np.zeros(len(P), bool)
    x, y = P[:, 0], P[:, 1]
    for L in loops:
        A = L
        Bn = np.roll(L, -1, 0)
        for (ax, ay), (bx, by) in zip(A, Bn):
            if ay == by:
                continue
            c = ((ay > y) != (by > y))
            xi = ax + (y - ay) * (bx - ax) / (by - ay)
            inside ^= c & (x < xi)
    return inside


