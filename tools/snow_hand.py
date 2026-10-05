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
        # the higher side on the left: probes left of every segment, the majority decides (one probe beside a
        # saddle or on a strip a cell or two wide could fall on the wrong side, turning every normal of the loop)
        dv = np.roll(L, -1, 0) - L
        ln_ = np.hypot(dv[:, 0], dv[:, 1])
        okv = ln_ > 1e-6
        if not okv.any():
            continue
        p = (L + np.roll(L, -1, 0))[okv] / 2.0
        t = dv[okv] / ln_[okv, None]
        q = p + 0.2 * np.column_stack([-t[:, 1], t[:, 0]])
        hi_ = bilinear(Fv, q[:, 0] + 1.0, q[:, 1] + 1.0) > level
        if float(np.sum(ln_[okv] * hi_)) < 0.5 * float(np.sum(ln_[okv])):
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


def resample_corners(L, smax, cmin, turn=0.6):
    """a closed loop resampled at most smax apart, with points cmin and 2 cmin either side of each sharp turn (so
    the rims fan round a corner)"""
    n = len(L)
    a = L - np.roll(L, 1, 0)
    b = np.roll(L, -1, 0) - L
    ang = np.abs(np.arctan2(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0], (a * b).sum(1)))
    sharp = ang > turn
    out = []
    for k in range(n):
        p, q = L[k], L[(k + 1) % n]
        ln = float(np.hypot(*(q - p)))
        if ln < 1e-9:
            continue
        m = max(1, int(math.ceil(ln / smax)))
        ts = set((np.arange(m) / m).tolist())
        for c in (cmin, 2 * cmin):
            if sharp[k] and c / ln < 0.4:
                ts.add(c / ln)
            if sharp[(k + 1) % n] and c / ln < 0.4:
                ts.add(1.0 - c / ln)
        ts = sorted(ts)
        keep = [ts[0]]
        for tt in ts[1:]:
            if (tt - keep[-1]) * ln > 0.45 * cmin:
                keep.append(tt)
        for tt in keep:
            out.append(p + (q - p) * tt)
    return np.array(out)


def loop_dist(P, loops):
    """the distance from each point of P (n, 2) to the nearest segment of the closed loops"""
    A = np.vstack(loops)
    Bn = np.vstack([np.roll(L, -1, 0) for L in loops])
    AB = Bn - A
    ab2 = np.maximum((AB * AB).sum(1), 1e-12)
    d = np.full(len(P), np.inf)
    for k in range(0, len(P), 1500):
        p = P[k:k + 1500, None, :]
        AP = p - A[None]
        tt = np.clip((AP * AB[None]).sum(-1) / ab2[None], 0.0, 1.0)
        Q = A[None] + tt[..., None] * AB[None]
        d[k:k + 1500] = np.sqrt(((p - Q) ** 2).sum(-1)).min(1)
    return d


def gauss3(A, r):
    """three box blurs of radius r (cells): about a gaussian of sigma sqrt(r (r + 1))"""
    n = float((2 * r + 1) ** 2)
    for _ in range(3):
        A = box(A, r) / n
    return A


def nearest_along(A, dj, di, r):
    """for each cell: the first finite value of A looking along (dj, di) within r cells, and its distance (cells)"""
    h = np.full(A.shape, np.nan)
    d = np.zeros(A.shape)
    for s in range(1, int(r) + 1):
        v = sh(A, -s * dj, -s * di, np.nan)
        new = np.isnan(h) & np.isfinite(v)
        h = np.where(new, v, h)
        d = np.where(new, s, d)
    return h, d


_ETAB = {}


def edge_table(r):
    """gauss3 of radius r over a straight edge: its value (rising) and the distance inside the edge (cells)"""
    if r not in _ETAB:
        x = np.arange(-6 * r - 6, 6 * r + 7)
        a = (x < 0).astype(np.float64)
        kk = np.ones(2 * r + 1) / (2 * r + 1)
        for _ in range(3):
            a = np.convolve(a, kk, mode='same')
        s = np.abs(x + 0.5) <= 3 * r + 1.5
        av, dv = a[s][::-1], (-0.5 - x[s])[::-1].astype(np.float64)
        # up to where it is full (beyond, the measure says nothing more)
        full = np.nonzero(av >= 1.0 - 1e-9)[0]
        if len(full):
            av, dv = av[:full[0] + 1], dv[:full[0] + 1]
        av = np.maximum.accumulate(av) + np.arange(len(av)) * 1e-12
        _ETAB[r] = (av, dv)
    return _ETAB[r]


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
        self.reset()

    def reset(self):
        """before a build: the blankets made (for the checks), the cells they cover, the cells regions claimed"""
        self._caps = []
        self._sel = np.zeros((self.nv, self.nu), bool)
        self._claimed = np.zeros((self.nv, self.nu), bool)

    def _faces(self):
        V, T = self.V, self.T
        A, Bv, C = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
        n = np.cross(Bv - A, C - A)
        ln = np.linalg.norm(n, axis=1)
        longest = np.max(np.stack([np.linalg.norm(Bv - A, axis=1), np.linalg.norm(C - Bv, axis=1),
                                   np.linalg.norm(A - C, axis=1)]), 0)
        self.ny_t = np.abs(n[:, 1]) / np.maximum(ln, 1e-12)
        self.n_t = n / np.maximum(ln, 1e-12)[:, None]
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
        Za = np.fmax(Z, Zt)
        self.Zall = np.where(np.isfinite(Za), Za, np.nan)
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
        self._all_t = np.nonzero(self.good_t)[0]
        T = self.T[self._all_t]
        self.bvh_all = BVHTree.FromPolygons([tuple(p) for p in self.V], [tuple(int(i) for i in t) for t in T],
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
        Mc, Zc = M.copy(), np.where(M, self.Z, np.nan)
        if rc > 0:
            # a gap is bridged where the surface lies on both sides of it along x or z within close, at about the
            # same height (a joint between planks, a slot in a deck; not the space between a seat and its back)
            cand = erode(dilate(M, rc), rc) & ~M
            if cand.any():
                Zmn = np.where(M, self.Z, np.nan)
                acc = np.zeros(M.shape)
                wsum = np.zeros(M.shape)
                for dj, di in ((0, 1), (1, 0)):
                    hp, dp = nearest_along(Zmn, dj, di, rc)
                    hn, dn = nearest_along(Zmn, -dj, -di, rc)
                    ok = cand & np.isfinite(hp) & np.isfinite(hn)
                    hp0, hn0 = np.nan_to_num(hp), np.nan_to_num(hn)
                    ok &= np.abs(hp0 - hn0) <= tau + 0.6 * (dp + dn) * g
                    zi = (hp0 * dn + hn0 * dp) / np.maximum(dp + dn, 1)
                    acc += np.where(ok, zi, 0.0)
                    wsum += ok
                br = wsum > 0
                Mc = M | br
                Zc = np.where(br, acc / np.maximum(wsum, 1), Zc)
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
        for Rm, _ in out:
            self._claimed |= Rm
        return out

    # ---------- the blanket ----------
    def blanket(self, R, Zc, variant, depth=1.0, over=None, rim='round', fill=None, smooth=None, narrow=True,
                spacing=None, opening=0.0, soften=1, holes=0.01, shoulder=0.45, bury=True):
        """one blanket of snow over the region R (its height field Zc) in this depth: (V, F) or None.
        depth scales the variant's depth, over the bulge of the rounded edge past the support; rim 'round' (the edge
        rounds over, bulges a little past the side and runs into the support under its edge) or 'taper' (thins out to
        the edge: rough stone); opening takes off strips narrower than about twice it; soften rounds the outline
        (cells; 1 follows the support to about a centimetre); bury runs the top on level over the steep faces that
        rise from its edge below it (the curve of a bench into its back) until the model comes out of the snow"""
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
        m = 8 + int(math.ceil((0.7 if bury else 0.25) / g))
        ja, jb = max(0, js.min() - m), min(self.nv, js.max() + m + 1)
        ia, ib = max(0, iis.min() - m), min(self.nu, iis.max() + m + 1)
        sl = (slice(ja, jb), slice(ia, ib))
        M = R[sl].copy()
        Z = np.where(M, Zc[sl], np.nan)
        Zm = self.Z[sl]
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
                # a pit fills; a bump standing up out of the snow (a pyramid cap, a bolt head) stays out of it
                Zmh = np.where(np.isfinite(Zm), Zm, -1e9)
                hm &= Zmh < Zh + 0.3 * t
                Z = np.where(hm, Zh, Z)
                M = M | hm
        NYE = self.NYE[sl]
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
            # a cornice grows where snow creeps over the eave of a wide roof; a tread, a seat or a cover holds a small
            # rounded edge
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
        S = np.where(M, np.clip(Sb, Zs + 0.8 * D, Zs + 1.15 * D + 0.005), 0.0)
        if rim == 'round':
            # the bevels and rounded edges of its own parts (left out as too steep to hold snow of their own): the
            # snow runs over them to the support's true edge, its top on level (else a cap stopped 2 cm short of a
            # slat's bevelled end)
            Pc = self.PART[sl]
            own = np.isin(Pc, np.unique(Pc[M & (Pc >= 0)])) & np.isfinite(Zm) & ~(self._claimed[sl] & ~R[sl])
            Zmv0 = np.nan_to_num(Zm, nan=-1e9)
            for _ in range(int(round(0.025 / g))):
                nb = dilate(M, 1) & own & ~M
                zn = maxf(np.where(M, Zs, -np.inf), 1)
                sn = maxf(np.where(M, S, -np.inf), 1)
                nb &= (Zmv0 > zn - 0.03) & (Zmv0 < sn - 0.005)
                if not nb.any():
                    break
                Zs = np.where(nb, Zmv0, Zs)
                S = np.where(nb, sn, S)
                M = M | nb
        if bury and rim != 'taper':
            # steep faces rising from the edge below the snow's top, not held by a region of their own: buried, the
            # top running on level over them (a seat's snow fills the curve into the back instead of pushing a rim
            # through its lower slats)
            NYc, G0c = self.NYE[sl], self.G0[sl]
            Zv = np.where(np.isfinite(Zm), Zm, -np.inf)
            free = ~self._claimed[sl] & ((NYc < 0.92) | (G0c > 0.3)) & np.isfinite(Zm)
            lvl = np.where(M, S, -np.inf)
            sup = np.where(M, Zs, -np.inf)
            zfloor = float(np.min(np.where(M, Zs, np.inf))) - 0.05
            G = np.zeros_like(M)
            for _ in range(int(round(0.6 / g))):
                ln_ = maxf(lvl, 1)
                zn = maxf(sup, 1)
                # down a joint or a rounded slat edge by up to 3 cm a step, up the face beyond
                add = ~(M | G) & free & (Zv > zn - 0.03) & (Zv > zfloor) & (Zv < ln_ - 0.015)
                if not add.any():
                    break
                G |= add
                lvl = np.where(add, ln_, lvl)
                sup = np.where(add, Zv, sup)
            if G.any():
                # only what leads to the model coming out of the snow (a face rising beyond), never what runs on
                # over an edge falling away
                lv = maxf(np.where(M | G, lvl, -np.inf), 1)
                emerge = ~(M | G) & np.isfinite(Zm) & (Zv >= lv - 0.015) & np.isfinite(lv)
                lab, nlab = label(G, G[:, 1:] & G[:, :-1], G[1:, :] & G[:-1, :])
                keep = np.zeros(nlab + 1, bool)
                touch = dilate(emerge, 1) & G
                keep[np.unique(lab[touch])] = True
                G &= keep[np.where(lab >= 0, lab, nlab)]
                lvl = np.where(G | M, lvl, -np.inf)
            if G.any():
                M2 = M | G
                Mcl = erode(dilate(M2, 2), 2) | M2
                new = Mcl & ~M2
                Sf = np.where(M, S, np.where(G, lvl, 0.0))
                Zf2 = np.where(M, Zs, np.where(G, sup, 0.0))
                if new.any():
                    Se, _ = extend(Sf, M2, new)
                    Ze, _ = extend(Zf2, M2, new)
                    Sf = np.where(new, Se, Sf)
                    Zf2 = np.where(new, Ze, Zf2)
                M, S, Zs = Mcl, np.where(Mcl, Sf, 0.0), np.where(Mcl, Zf2, 0.0)
        if rim == 'round':
            # deeper snow smooths the hollows of its outline (the notches between slat ends, the step where a slat
            # ends short): over a void or what lies lower than its top, never over another region or a face above it
            crr = int(round(min(0.12, 0.4 * t) / g))
            if crr >= 2:
                notch = erode(dilate(M, crr), crr) & ~M
                n0 = int(notch.sum())
                if notch.any():
                    near = maxf(np.where(M, S, -np.inf), crr)
                    Zmv_ = np.nan_to_num(Zm, nan=-1e9)
                    if os.environ.get('SZ_DEBUG'):
                        print('  notch cand %d lower %d unclaimed %d' % (n0, int((notch & (Zmv_ < near - 0.01)).sum()),
                              int((notch & ~(self._claimed[sl] & ~R[sl])).sum())), flush=True)
                    notch &= (Zmv_ < near - 0.01) & ~(self._claimed[sl] & ~R[sl])
                    if notch.any():
                        Se, _ = extend(np.where(M, S, 0.0), M, notch)
                        Ze, _ = extend(np.where(M, Zs, 0.0), M, notch)
                        S = np.where(notch, Se, S)
                        Zs = np.where(notch, np.maximum(Ze, np.where(np.isfinite(Zm), Zmv_, -1e9)), Zs)
                        S = np.maximum(S, Zs)
                        M = M | notch
        Hf = np.where(M, np.maximum(S - Zs, 0.0), 0.0)
        if not M.any():
            return None
        taper = rim == 'taper'
        Vec = Vector
        # ---------- around the snow: walls (the model rising out of it beside it) ----------
        Zmv = np.nan_to_num(Zm, nan=-1e9)
        band = dilate(M, 3) & ~M
        Sn = maxf(np.where(M, S, -np.inf), 2)
        Zn_ = maxf(np.where(M, Zs, -np.inf), 2)
        Wm = band & np.isfinite(Sn) & (Zmv > Zn_ + 0.7 * (Sn - Zn_))
        kw = int(math.ceil(0.25 / g)) + 3
        Wd = (distance(~Wm, kw) - 0.5) * g if Wm.any() else np.full(M.shape, 10.0)
        # ---------- the smooth measure of inside (gaussian; a wall counts as inside: full snow against it) ----------
        if taper:
            rh_ref = float(np.clip(0.45 * t, 1.5 * g, 0.12))
        else:
            rh_ref = float(np.clip(shoulder * t, 1.5 * g, 0.12))
        sig = 0.35 * rh_ref / g
        rb = max(1, int(round(math.sqrt(sig * sig + 0.25) - 0.5)))
        Wb = dilate(Wm, 3 * rb + 2) & ~M
        Bm = gauss3((M | Wb).astype(np.float64), rb)
        tb, td = edge_table(rb)
        DE = np.interp(Bm, tb, td) * g
        # the measure is full this far inside (the inside of a wide support); narrower than that a crest
        dfull = min(1.2 * rh_ref, 0.9 * float(td[-1]) * g)
        # ---------- the fields carried past the edge (over the overhang) ----------
        o_lo = max(0.008, 0.6 * g + 0.25 * rh_ref + 0.004) if not taper else 0.0
        o_hi = max(o_lo, float(over))
        Sx, Zx = S.copy(), Zs.copy()
        have = M.copy()
        for _ in range(int(math.ceil((o_hi + 0.02) / g)) + 4):
            nb = dilate(have, 1) & ~have
            if not nb.any():
                break
            Sx = np.where(nb, blur(Sx, have, 1), Sx)
            Zx = np.where(nb, blur(Zx, have, 1), Zx)
            have |= nb
        Hx = np.where(have, np.maximum(Sx - Zx, 0.0), 0.0)
        Ox = np.clip(np.minimum(over, 0.6 * Hx), o_lo, None) if not taper else np.zeros(M.shape)
        # the bulge: the least of the neighbourhood's (no tip out past the ones beside it)
        if not taper:
            Ox = blur(minf(Ox, max(1, int(round(0.03 / g)))), np.ones(M.shape, bool), max(1, int(round(0.03 / g))))
            Ox = np.maximum(Ox, o_lo)
        # ---------- the domain: out to the tip of the bulge, in to a wall ----------
        if taper:
            Fm = box(M.astype(np.float64), 1) / 9.0
            F = (Fm - 0.5) * g * 2.0
        else:
            F = DE + Ox
        F = np.minimum(F, Wd)
        # no further from the support than the bulge reaches (behind a wall the measure is high again)
        dout = distance(~M, int(math.ceil((o_hi + 0.03) / g)) + 3) * g
        F = np.minimum(F, (o_hi + g) - np.where(M, 0.0, dout))
        F = np.where(have | M, F, -1.0)
        loops = contours(F, 0.0)
        if not loops:
            return None
        sp = spacing if spacing is not None else float(np.clip(self.size / 40.0, 0.03, 0.3))
        if os.environ.get('SZ_SPACING'):
            sp = float(os.environ['SZ_SPACING'])
        spe = float(np.clip(sp, 1.5 * g, 0.2))
        # along a straight edge or ring points no further apart than this (its bends keep their own points)
        slong = float(np.clip(2.5 * spe, 3.0 * g, 0.3))
        cmin = max(0.75, min(0.4 * spe, 0.5 * o_hi + 0.004) / g)
        L2 = []
        for L in loops:
            L = simplify_loop(L, 0.25)
            if len(L) < 3:
                continue
            area = 0.5 * abs(float(np.sum(L[:, 0] * np.roll(L[:, 1], -1) - np.roll(L[:, 0], -1) * L[:, 1]))) * g * g
            if area < 0.25 * self.min_area:
                continue
            L2.append(resample_corners(L, slong / g, cmin))
        if not L2:
            return None
        nb_pts = sum(len(L) for L in L2)
        Pb = np.vstack(L2)
        # each boundary point: at a wall or the open tip (taper: rough stone's thin edge); its outward direction
        wts = (1.0, 2.0, 3.0, 2.0, 1.0)
        Bwall = np.zeros(nb_pts, bool)
        NX, NZ = np.zeros(nb_pts), np.zeros(nb_pts)
        k0 = 0
        for L in L2:
            n = len(L)
            tang = np.roll(L, -1, 0) - np.roll(L, 1, 0)
            nx, nz = tang[:, 1], -tang[:, 0]
            ln = np.maximum(np.hypot(nx, nz), 1e-12)
            nx, nz = nx / ln, nz / ln
            sx = sum(w_ * np.roll(nx, s) for w_, s in zip(wts, (-2, -1, 0, 1, 2)))
            sz = sum(w_ * np.roll(nz, s) for w_, s in zip(wts, (-2, -1, 0, 1, 2)))
            ln = np.maximum(np.hypot(sx, sz), 1e-12)
            NX[k0:k0 + n], NZ[k0:k0 + n] = sx / ln, sz / ln
            wd_ = bilinear(Wd, L[:, 0], L[:, 1])
            fo_ = bilinear(DE + Ox, L[:, 0], L[:, 1]) if not taper else np.full(n, 1.0)
            Bwall[k0:k0 + n] = wd_ < fo_ - 0.25 * g
            k0 += n
        # ---------- points: rings of the rounded edge and the bulge, a grid inside ----------
        def ring_pts(field, levels, where_, corners=False):
            out = []
            Fd = np.where(where_, field, np.nanmin(field[np.isfinite(field)]) - 1.0)
            amin = max(6.0, 0.003 * float((F > 0).sum()))
            for lv in levels:
                for Lc in contours(Fd, lv):
                    Lc = simplify_loop(Lc, 0.25)
                    # (no specks: a level near the plateau of a measure rings every ripple of it)
                    ar_ = 0.5 * abs(float(np.sum(Lc[:, 0] * np.roll(Lc[:, 1], -1) - np.roll(Lc[:, 0], -1) * Lc[:, 1])))
                    if len(Lc) >= 3 and ar_ >= amin:
                        out.append(resample_corners(Lc, slong / g, cmin) if corners else resample_loop(Lc, slong / g))
            return out

        inD = F > 0
        cand_t = []
        Rc = np.zeros((0, 2))
        tin = 0.012
        if not taper:
            rhx = np.minimum(np.clip(shoulder * Hx, 0.0, 0.12), rh_ref)
            rr = float(np.median(rhx[M])) if M.any() else rh_ref
            oo = float(np.median(Ox[M])) if M.any() else o_lo
            # the rounded edge in even steps of its arc, from the tip (90 degrees) to the plateau (0), all rings
            # levels of the one measure (0 at the tip, 1 where the top runs level): parallel rings, a clean strip
            # round every edge and corner (rings of different measures crossed at the corners); no two rings closer
            # than about half a cell
            ext = rr + oo
            ulev, last = [], 0.0
            for th in (72.0, 54.0, 38.0, 24.0, 11.0, 0.0):
                u_ = 1.0 - math.sin(math.radians(th))
                if (u_ * ext - last) >= 0.6 * g and u_ * ext >= 0.6 * g:
                    ulev.append(u_)
                    last = u_ * ext
            # each ring the boundary's own points stepped in along their normals (point for point: the strip
            # between two rings is a row of quads, no fan of slivers ribbing the rounded edge); at a wall only the
            # plateau's ring; a point past the middle of the domain (closer to another stretch of the rim than its
            # step) or crowding the last one kept round a corner is left out
            ext_b = (bilinear(Ox, Pb[:, 0], Pb[:, 1]) + bilinear(rhx, Pb[:, 0], Pb[:, 1])) / g
            k0 = 0
            for L in L2:
                n = len(L)
                e_ = ext_b[k0:k0 + n]
                ext_b[k0:k0 + n] = sum(w_ * np.roll(e_, s) for w_, s in zip(wts, (-2, -1, 0, 1, 2))) / sum(wts)
                k0 += n
            ring_c, ring_t = [], []
            for u_ in ulev:
                k0 = 0
                for L in L2:
                    n = len(L)
                    s_ = slice(k0, k0 + n)
                    k0 += n
                    tt = u_ * ext_b[s_]
                    P = L - np.column_stack([NX[s_], NZ[s_]]) * tt[:, None]
                    ok = (~Bwall[s_]) | (u_ > 0.99)
                    ring_c.append(P[ok])
                    ring_t.append(tt[ok])
            Rc = np.vstack(ring_c) if ring_c else np.zeros((0, 2))
            Rt_ = np.concatenate(ring_t) if ring_t else np.zeros(0)
            if len(Rc):
                okr = inside_loops(Rc, L2) & (loop_dist(Rc, L2) >= 0.9 * Rt_)
                if os.environ.get('SZ_DEBUG'):
                    print('  rings: levels %s ext %.4f g %.4f cand %d inside %d medial-ok %d' % (
                        [round(u_, 3) for u_ in ulev], ext, g, len(Rc), int(inside_loops(Rc, L2).sum()), int(okr.sum())), flush=True)
                Rc = Rc[okr]
                keep_r = np.ones(len(Rc), bool)
                lastk = 0
                for k in range(1, len(Rc)):
                    if np.hypot(*(Rc[k] - Rc[lastk])) < 0.45 * cmin:
                        keep_r[k] = False
                    else:
                        lastk = k
                Rc = Rc[keep_r]
                cand_t.append(Rc)
        else:
            cand_t += ring_pts(DE, [f * rh_ref for f in (0.2, 0.7)], inD)
        si = max(2.0 * g, sp) / g

        def clear_of_rings(P, dmin):
            # (no point of the grid or the crest crowding a ring's: no slivers against the strip)
            if not len(Rc) or not len(P):
                return P
            d = np.full(len(P), np.inf)
            for k in range(0, len(P), 1000):
                d[k:k + 1000] = np.sqrt(((P[k:k + 1000, None, :] - Rc[None]) ** 2).sum(-1)).min(1)
            return P[d >= dmin]

        gi = np.arange(0, M.shape[1], max(1, int(round(si))))
        gj = np.arange(0, M.shape[0], max(1, int(round(si))))
        GI, GJ = np.meshgrid(gi, gj)
        okp = inD[GJ, GI] & (DE[GJ, GI] > dfull)
        cand_t.append(clear_of_rings(np.column_stack([GI[okp], GJ[okp]]).astype(np.float64), 0.5 * si))
        # the middle line of the domain (its narrowest parts too have points inside: a wall top's crest)
        DEd = np.where(inD, DE, -np.inf)
        ridge = inD & (DEd >= maxf(DEd, 2) - 1e-9) & (DEd > 0) & (DEd < dfull)
        if ridge.any():
            rj, ri = np.nonzero(ridge)
            st_ = max(1, int(round(0.5 * spe / g)))
            # on the crest itself (a Newton step across it: the cells' centres stepped up and down a diagonal crest)
            J_, I_ = DE.shape
            jm, jp = np.clip(rj - 1, 0, J_ - 1), np.clip(rj + 1, 0, J_ - 1)
            im_, ip_ = np.clip(ri - 1, 0, I_ - 1), np.clip(ri + 1, 0, I_ - 1)
            c0 = DE[rj, ri]
            gx_, gy_ = 0.5 * (DE[rj, ip_] - DE[rj, im_]), 0.5 * (DE[jp, ri] - DE[jm, ri])
            hxx = DE[rj, ip_] - 2.0 * c0 + DE[rj, im_]
            hyy = DE[jp, ri] - 2.0 * c0 + DE[jm, ri]
            hxy = 0.25 * (DE[jp, ip_] - DE[jp, im_] - DE[jm, ip_] + DE[jm, im_])
            Hm = np.stack([np.stack([hxx, hxy], -1), np.stack([hxy, hyy], -1)], -2)
            ev, evec = np.linalg.eigh(Hm)
            lam, nvec = ev[:, 0], evec[:, :, 0]
            stp = np.where(lam < -1e-12, -(gx_ * nvec[:, 0] + gy_ * nvec[:, 1]) / np.where(lam < -1e-12, lam, -1.0), 0.0)
            stp = np.clip(stp, -0.7, 0.7)
            Rp = np.column_stack([ri + stp * nvec[:, 0], rj + stp * nvec[:, 1]])
            _, ui = np.unique((Rp // st_).astype(np.int64), axis=0, return_index=True)
            cand_t.append(clear_of_rings(Rp[np.sort(ui)], max(0.6, 0.3 * spe / g)))

        def tri(cand, emin):
            C = np.vstack([c for c in cand if len(c)]) if any(len(c) for c in cand) else np.zeros((0, 2))
            if len(C):
                C = C[inside_loops(C, L2)]
            if len(C):
                C = C[loop_dist(C, L2) >= emin]
            if len(C):
                q = 0.6
                _, ui = np.unique(np.round(C / q).astype(np.int64), axis=0, return_index=True)
                C = C[np.sort(ui)]
            pts = [tuple(p) for p in Pb] + [tuple(p) for p in C]
            edges = []
            k0 = 0
            for L in L2:
                n = len(L)
                edges += [(k0 + k, k0 + (k + 1) % n) for k in range(n)]
                k0 += n
            res = delaunay_2d_cdt([Vector(p) for p in pts], edges, [], 0, 1e-6, True)
            P2 = np.array([(v.x, v.y) for v in res[0]])
            Tr = np.array([f for f in res[2] if len(f) == 3], dtype=np.int64).reshape(-1, 3)
            if len(Tr):
                # inside by parity: the rim's edges crossed on the way in from beyond the hull (exact: a centroid
                # test can put a sliver at a concave corner either side of the rim)
                nv = len(P2)
                con = set()
                for k, (ea, eb) in enumerate(res[1]):
                    if len(res[4][k]):
                        con.add(min(ea, eb) * nv + max(ea, eb))
                ek = {}
                for t, f in enumerate(Tr.tolist()):
                    for a_, b_ in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
                        ek.setdefault(min(a_, b_) * nv + max(a_, b_), []).append(t)
                par = np.full(len(Tr), -1, dtype=np.int64)
                dq = collections.deque()
                for k, ts in ek.items():
                    if len(ts) == 1 and par[ts[0]] < 0:
                        par[ts[0]] = 1 if k in con else 0
                        dq.append(ts[0])
                while dq:
                    t = dq.popleft()
                    f = Tr[t]
                    for a_, b_ in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
                        k = min(a_, b_) * nv + max(a_, b_)
                        for u in ek[k]:
                            if par[u] < 0:
                                par[u] = par[t] ^ (1 if k in con else 0)
                                dq.append(u)
                Tr = Tr[par == 1]
                if os.environ.get('SZ_DEBUG'):
                    a_t = 0.5 * np.abs(np.cross(P2[Tr[:, 1]] - P2[Tr[:, 0]], P2[Tr[:, 2]] - P2[Tr[:, 0]])).sum()
                    a_l = sum(0.5 * abs(float(np.sum(L[:, 0] * np.roll(L[:, 1], -1) - np.roll(L[:, 0], -1) * L[:, 1]))) for L in L2)
                    print('  tri: kept %d of %d, unvisited %d, area %.1f loops %.1f (n loops %d)' % (
                        len(Tr), len(par), int((par < 0).sum()), a_t, a_l, len(L2)), flush=True)
            onl = np.full(len(P2), -1, dtype=np.int64)
            for k, ov in enumerate(res[3]):
                for o in ov:
                    if o < nb_pts:
                        onl[k] = o
            # boundary points the triangulation dropped: the nearest vertex
            bmap = np.full(nb_pts, -1, dtype=np.int64)
            for k, o in enumerate(onl):
                if o >= 0:
                    bmap[o] = k
            if (bmap < 0).any() and len(Tr):
                used_v = np.unique(Tr.ravel())
                for o in np.nonzero(bmap < 0)[0]:
                    bmap[o] = int(used_v[int(np.argmin(np.hypot(*(P2[used_v] - Pb[o]).T)))])
            return P2, Tr, bmap

        emin = max(0.3, 0.12 * rh_ref / g)
        if os.environ.get('SZ_DEBUG'):
            print('  points %s boundary %d dfull %.3f rh %.3f rb %d' % (
                [len(c) for c in cand_t], nb_pts, dfull, rh_ref, rb), flush=True)
        P2t, Trt, bmt = tri(cand_t, emin)
        if len(Trt) == 0:
            return None
        # ---------- heights ----------
        def fields(P2):
            return (bilinear(Zx, P2[:, 0], P2[:, 1]), bilinear(Hx, P2[:, 0], P2[:, 1]),
                    bilinear(DE, P2[:, 0], P2[:, 1]), bilinear(Ox, P2[:, 0], P2[:, 1]), bilinear(Sx, P2[:, 0], P2[:, 1]))

        def ytop(zs, H, de, o, sxv):
            if taper:
                return np.maximum(sxv, zs)
            rv = np.clip(shoulder * H, 0.0, 0.12)
            rh = np.minimum(rv, rh_ref)
            s = np.clip((rh - de) / np.maximum(rh + o, 1e-6), 0.0, 1.0)
            return zs + H - rv + rv * np.sqrt(1.0 - s * s)

        def ybot(zs, H, de, o, foot):
            if taper:
                return zs - foot
            rv = np.clip(shoulder * H, 0.0, 0.12)
            y1 = H - rv
            u = np.clip((tin - de) / np.maximum(tin + o, 1e-6), 0.0, 1.0)
            return zs - foot + (y1 + foot) * (1.0 - np.sqrt(1.0 - u * u))

        # the top on the grid, smoothed once over the domain (a rounded crest where the snow on an inclined board
        # meets its rounded edge); never below the underside nor under a third of the snow on the support
        inR = (F > 0) | M
        Yr = ytop(Zx, Hx, DE, Ox, Sx)
        Ybr = ybot(Zx, Hx, DE, Ox, 0.004)
        if not taper:
            rs2 = max(1, int(round(0.5 * rh_ref / g)))
            Wr = inR.astype(np.float64)
            Ys = gauss3(np.where(inR, Yr, 0.0), rs2) / np.maximum(gauss3(Wr, rs2), 1e-9)
            Ys = np.where(M, np.maximum(Ys, Zx + 0.3 * Hx), Ys)
            Ys = np.maximum(Ys, Ybr + 0.002)
            Yr = np.where(inR, Ys, Yr)
        zt, Ht, det, ot, st_ = fields(P2t)
        Yt = bilinear(Yr, P2t[:, 0], P2t[:, 1])
        Xw = lambda P2: (self.u0 + (P2[:, 0] + ia) * g, self.v0 + (P2[:, 1] + ja) * g)
        xt, zzt = Xw(P2t)
        # the underside: under the bulge and a little way in (further in the snow rests on the support, an underside
        # would only lie hidden in it), on the top's own points so that its facets keep under the top's
        isbd = np.zeros(len(P2t), bool)
        isbd[bmt] = True
        # the underside's faces: every face touching the rim or reaching in under the bulge (a corner less than the
        # bulge's tuck in); the faces it leaves out have every corner further in, so its inner edge lies wholly where
        # the underside rests in the support
        near = (det < tin) | isbd
        tsel = np.any(near[Trt], axis=1) | np.all(det[Trt] < tin + 0.012, axis=1)
        if taper:
            tsel[:] = False
        twin = isbd.copy()
        twin[np.unique(Trt[tsel].ravel())] = True
        tq = np.nonzero(twin)[0]
        foot = np.full(len(P2t), 0.002)
        for q in tq:
            loc, nr, _, dd = self.bvh.ray_cast(Vec((xt[q], zt[q] - 0.002, zzt[q])), Vec((0.0, -1.0, 0.0)), 0.1)
            thq = dd + 0.002 if (loc is not None and nr.y < -0.3) else 0.004
            foot[q] = float(np.clip(0.5 * thq, 0.002, 0.006))
        Yb = np.full(len(P2t), np.nan)
        Yb[tq] = np.minimum(ybot(zt[tq], Ht[tq], det[tq], ot[tq], foot[tq]), Yt[tq] - 0.002)

        # beyond the support's edge nothing goes into what lies under it: the underside rests on it, the top keeps
        # above it (on a log, a pipe, a roof's steeper fall the bulge drapes over the surface going on below)
        def floor_at(x, z, ytop_):
            loc = self.bvh_all.ray_cast(Vec((x, ytop_ + 0.002, z)), Vec((0.0, -1.0, 0.0)), 0.6)[0]
            return -1e9 if loc is None else loc.y + 0.004

        for q in np.nonzero(det < -0.002)[0]:
            fl = floor_at(xt[q], zzt[q], float(Yt[q]))
            if fl > -1e8:
                Yt[q] = max(Yt[q], fl + 0.002)
                if twin[q]:
                    Yb[q] = max(Yb[q], fl)
        Yb[tq] = np.minimum(Yb[tq], Yt[tq] - 0.002)
        # ---------- the shell ----------
        Vl, Fl, role, anchor = [], [], [], []
        for q in range(len(P2t)):
            Vl.append((xt[q], Yt[q], zzt[q]))
            role.append(0)
            anchor.append(-1)
        Tt = Trt.copy()
        nrm = np.cross(np.array(Vl)[Tt[:, 1]] - np.array(Vl)[Tt[:, 0]], np.array(Vl)[Tt[:, 2]] - np.array(Vl)[Tt[:, 0]])
        flip = nrm[:, 1] < 0
        Tt[flip] = Tt[flip][:, [0, 2, 1]]
        Fl += [tuple(f) for f in Tt.tolist()]
        # the underside's points: the open tips shared with the top
        ib = np.full(len(P2t), -1, dtype=np.int64)
        for o in range(nb_pts):
            if not Bwall[o] and not taper:
                ib[bmt[o]] = bmt[o]
        for q in tq:
            if ib[q] < 0:
                Vl.append((xt[q], Yb[q], zzt[q]))
                role.append(2)
                anchor.append(-1)
                ib[q] = len(Vl) - 1
        footv = set()
        if not taper:
            tb_ = Tt[tsel]
            if len(tb_):
                Fl += [tuple(f) for f in ib[tb_][:, [0, 2, 1]].tolist()]
                # its inner edge (once in the underside, twice in the top): hidden in the support
                def ekeys(T_):
                    E_ = np.sort(np.concatenate([T_[:, [0, 1]], T_[:, [1, 2]], T_[:, [2, 0]]]), axis=1)
                    return E_[:, 0] * (len(P2t) + 1) + E_[:, 1]
                ku, cu = np.unique(ekeys(tb_), return_counts=True)
                ka, ca = np.unique(ekeys(Tt), return_counts=True)
                inner = ku[(cu == 1) & np.isin(ku, ka[ca == 2])]
                for e_ in inner.tolist():
                    for q in (e_ // (len(P2t) + 1), e_ % (len(P2t) + 1)):
                        if ib[q] != q:
                            role[ib[q]] = 3
        bmb = bmt

        # the open tips held to the model (a tip pushed into a part beside the edge comes back out of it)
        bva = self.bvh_all

        def resolve(A, P):
            A = np.asarray(A, np.float64)
            P = np.asarray(P, np.float64)
            d = P - A
            Ld = float(np.linalg.norm(d))
            if Ld < 1e-5:
                return P
            dv = d / Ld
            o = Vec(tuple(A))
            dvv = Vec(tuple(dv))
            trav, hits = 0.0, []
            while trav < Ld and len(hits) < 3:
                loc, _, _, dd = bva.ray_cast(o, dvv, Ld - trav)
                if loc is None:
                    break
                trav += dd
                hits.append(trav)
                o = loc + dvv * 1e-4
                trav += 1e-4
            if not hits or (len(hits) == 1 and Ld - hits[0] <= 0.025):
                return P
            if len(hits) == 1:
                return A + dv * (hits[0] + 0.006)
            return A + dv * min(hits[0] + 0.006, 0.5 * (hits[0] + hits[1]))

        # ---------- the curtain down a wall (and rough stone's thin edge) ----------
        FRS = (0.66, 0.33)
        k0 = 0
        for L in L2:
            n = len(L)
            idx = np.arange(k0, k0 + n)
            k0 += n
            cur = {}
            for o in idx:
                vt, vb = int(bmt[o]), int(ib[bmb[o]])
                if vt == vb:
                    continue
                pt = np.array(Vl[vt])
                pb = np.array(Vl[vb])
                nx_, nz_ = NX[o], NZ[o]
                rows = [vt]
                if Bwall[o]:
                    # each height its own ray from above the support into the wall, tucked 5 mm (short of a face
                    # looking down); never further out than the row above; the top no further than a face leaning
                    # back at 30 degrees
                    ys = float(pb[1])
                    hgt = max(0.0, float(pt[1]) - ys)
                    xs = []
                    xcap = None
                    for fr in (1.0,) + FRS + (0.0,):
                        yy = ys + max(0.003, hgt * fr - (0.003 if fr == 1.0 else 0.0))
                        loc, nrw, _, dd = self.bvh.ray_cast(Vec((pt[0] - 0.01 * nx_, yy, pt[2] - 0.01 * nz_)),
                                                            Vec((nx_, 0.0, nz_)), 0.1)
                        x = float(np.clip(dd - 0.01 + (0.005 if nrw.y > -0.3 else -0.003), 0.0, 0.08)) if loc is not None \
                            else (xs[-1] if xs else 0.006)
                        x = min(x, 0.025 + 0.6 * hgt) if xcap is None else min(x, xcap + 0.003)
                        xcap = x
                        xs.append(x)
                    Vl[vt] = (pt[0] + nx_ * xs[0], pt[1], pt[2] + nz_ * xs[0])
                    for fr, x in zip(FRS, xs[1:3]):
                        q_ = resolve(Vl[vt], (pt[0] + nx_ * x, ys + hgt * fr, pt[2] + nz_ * x))
                        Vl.append(tuple(q_))
                        role.append(4)
                        anchor.append(vt)
                        rows.append(len(Vl) - 1)
                    Vl[vb] = tuple(resolve(Vl[vt], (pb[0] + nx_ * xs[3], pb[1], pb[2] + nz_ * xs[3])))
                    role[vb] = 4
                    anchor[vb] = vt
                rows.append(vb)
                cur[o] = rows
            for a_ in idx:
                b_ = idx[0] if a_ == idx[-1] else a_ + 1
                ra, rb2 = cur.get(a_), cur.get(b_)
                if ra is None and rb2 is None:
                    continue
                # a curtain ending at an open tip: the tip stands for every row there (a fan); a wall's four rows
                # beside rough stone's two: the two spread over four
                if ra is None:
                    ra = [int(bmt[a_])] * len(rb2)
                if rb2 is None:
                    rb2 = [int(bmt[b_])] * len(ra)
                if len(ra) < len(rb2):
                    ra = [ra[0]] * (len(rb2) - len(ra) + 1) + ra[1:]
                if len(rb2) < len(ra):
                    rb2 = [rb2[0]] * (len(ra) - len(rb2) + 1) + rb2[1:]
                for j in range(len(ra) - 1):
                    Fl.append((ra[j], rb2[j + 1], ra[j + 1]))
                    Fl.append((ra[j], rb2[j], rb2[j + 1]))
        # the open tips (top and underside meet there)
        for o in range(nb_pts):
            vt = int(bmt[o])
            if not Bwall[o] and not taper and role[vt] == 0:
                role[vt] = 1
            if taper:
                # rough stone: the curtain's foot rests on the stone
                footv.add(int(ib[bmb[o]]))

        Va = np.array(Vl, dtype=np.float64)
        Fa = np.array(Fl, dtype=np.int64)
        # points the model held to the same place: one point (the faces between them fall away, the rest closes)
        key = np.round(Va / 1e-5).astype(np.int64)
        _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
        inv = inv.ravel()
        Fa = first[inv[Fa]]
        Fa = Fa[(Fa[:, 0] != Fa[:, 1]) & (Fa[:, 1] != Fa[:, 2]) & (Fa[:, 0] != Fa[:, 2])]
        # (a closed shell: no edge of it is open)
        role_a = np.array(role)
        anch_a = np.array(anchor)
        # (the hidden inner edge of the underside, in the support, is its only open edge)
        foot_a = role_a == 3
        if footv:
            foot_a[list(footv)] = True
        ar = np.linalg.norm(np.cross(Va[Fa[:, 1]] - Va[Fa[:, 0]], Va[Fa[:, 2]] - Va[Fa[:, 0]]), axis=1)
        Fa = Fa[ar > 1e-10]
        if os.environ.get('SZ_DEBUG'):
            print('  blanket v%d cells %d added %d loops %d boundary %d walls %d' % (
                variant, int(R.sum()), int((M & ~R[sl]).sum()), len(L2), nb_pts, int(Bwall.sum())), flush=True)

        self._caps.append({'V': Va, 'F': Fa, 'role': role_a, 'anchor': anch_a, 'foot': foot_a})
        self._sel[sl] |= M
        return Va, Fa

    # ---------- the checks ----------
    def check(self, V, F):
        """the precision checks of this model's snow in one depth (V, F: all of it; the blankets of the last build
        give the rims): {name: (count, up to four places)}. Every count but tall pokes and shaded ought to be 0:
        uncovered  cells meant to hold snow without snow over them (more than about a centimetre from any)
        poke_thin  the model just through the snow's top (under 5 cm): a speck, an edge, a chamfer showing
        poke_tall  the model standing out of the snow (a post, a rail): to be judged
        under      snow touching or inside the model above it
        shaded     snow with the model above it at a distance (a bulge under an overhang): to be judged
        through    a rim running through the model (in and out of a part, or deep into it)
        underside  snow coming out of a face that looks down (the underside of a board, a cover, a beam)
        floating   a piece of snow touching nothing
        crease     a fold in the snow's top (neighbouring top faces more than 25 degrees apart)"""
        from mathutils.bvhtree import BVHTree
        from mathutils import Vector as Vec
        g = self.g
        res = collections.OrderedDict()
        V = np.asarray(V, np.float64)
        F = np.asarray(F, np.int64).reshape(-1, 3)
        if len(F) == 0:
            return res

        def put(key, P):
            P = np.asarray(P, np.float64).reshape(-1, 3)
            st = max(1, len(P) // 4)
            res[key] = (len(P), [tuple(round(float(c), 3) for c in p) for p in P[::st][:4]])

        sb = BVHTree.FromPolygons([tuple(p) for p in V], [tuple(int(i) for i in f) for f in F], all_triangles=True,
                                  epsilon=0.0)
        # the snow's top: the faces of the blankets' tops and the upper part of their rounded edges
        Vt, Ft, k0 = [], [], 0
        for cap in self._caps:
            ft = cap['F'][np.all(cap['role'][cap['F']] <= 1, axis=1)]
            Vt.append(cap['V'])
            Ft.append(ft + k0)
            k0 += len(cap['V'])
        st = None
        if Ft and sum(len(f) for f in Ft):
            Vt, Ft = np.vstack(Vt), np.vstack(Ft)
            st = BVHTree.FromPolygons([tuple(p) for p in Vt], [tuple(int(i) for i in f) for f in Ft],
                                      all_triangles=True, epsilon=0.0)
        mb = self.bvh_all
        lo, hi = V.min(0), V.max(0)
        i0, i1 = max(0, int((lo[0] - self.u0) / g) - 2), min(self.nu, int((hi[0] - self.u0) / g) + 3)
        j0, j1 = max(0, int((lo[2] - self.v0) / g) - 2), min(self.nv, int((hi[2] - self.v0) / g) + 3)
        ys = np.full((self.nv, self.nu), np.nan)
        yt = np.full((self.nv, self.nu), np.nan)
        inv_ = np.zeros((self.nv, self.nu), bool)
        top = float(max(hi[1], np.nanmax(self.Zall)) + 1.0)
        down = Vec((0.0, -1.0, 0.0))
        for j in range(j0, j1):
            z = self.v0 + j * g
            for i in range(i0, i1):
                o = Vec((self.u0 + i * g, top, z))
                loc, nor_, _, _ = sb.ray_cast(o, down, 1e4)
                if loc is not None:
                    ys[j, i] = loc.y
                    inv_[j, i] = nor_.y < 0.0
                    if st is not None:
                        loc = st.ray_cast(o, down, 1e4)[0]
                        if loc is not None:
                            yt[j, i] = loc.y
        snow = np.isfinite(ys)
        Za = np.nan_to_num(self.Zall, nan=-1e9)
        ysv = np.nan_to_num(ys, nan=1e9)
        above = snow & (Za > ysv + 0.002)
        cov = snow & ~above
        k = max(1, int(round(0.012 / g)))
        far = self._sel & ~dilate(cov, k)

        def cells(Mk, Y):
            jj, ii = np.nonzero(Mk)
            return np.column_stack([self.u0 + ii * g, np.nan_to_num(Y[jj, ii]), self.v0 + jj * g])

        put('uncovered', cells(far, self.Z))
        # the first snow seen from above looks down: the underside through the top, or a top face turned over
        put('inverted', cells(inv_, ys))
        # the top of the parts the snow lies on, near it, left without snow (a cap short of the end of its support)
        heldp = np.unique(self.PART[self._sel & (self.PART >= 0)])
        kk = max(1, int(round(0.03 / g)))
        nearsel = dilate(self._sel, kk) & ~self._sel & np.isin(self.PART, heldp)
        zsel = maxf(np.where(self._sel, np.nan_to_num(self.Z, nan=-1e9), -np.inf), kk)
        ytn = maxf(np.where(np.isfinite(yt), yt, -np.inf), kk)
        Zz = np.nan_to_num(self.Z, nan=-1e9)
        # (lower than the snow beside it: a part rising out of the snow is no short cap)
        short = nearsel & (Zz > zsel - 0.03) & (Zz < ytn - 0.02) & ~dilate(cov, k)
        put('short', cells(short, self.Z))
        tops_ = np.isfinite(yt)
        ytv = np.nan_to_num(yt, nan=1e9)
        # (inside the top: at its edge the model rising out of the snow is no poke)
        pk = erode(tops_, 3) & (Za > ytv + 0.002)
        # (only islands of the model in the snow's top: what joins the edge is the model coming out of the snow)
        if pk.any():
            labp, nlp = label(pk, pk[:, 1:] & pk[:, :-1], pk[1:, :] & pk[:-1, :])
            edge_ = dilate(~tops_, 4) & pk
            badl = np.zeros(nlp + 1, bool)
            badl[np.unique(labp[edge_])] = True
            pk &= ~badl[np.where(labp >= 0, labp, nlp)]
        thin = pk & (Za < ytv + 0.05)
        put('poke_thin', cells(thin, self.Zall))
        put('poke_tall', cells(pk & ~thin, self.Zall))
        und, shd, thr, flo = [], [], [], []
        up = Vec((0.0, 1.0, 0.0))
        ytm = maxf(np.where(np.isfinite(yt), yt, -np.inf), 3)

        def hangs(c, tri):
            """the part of the model triangle tri hangs over the snow at c: where it shows from above within 4 cm of
            c none of it goes into the snow (a beam above; not the low end of a slat that the snow buries)"""
            p_ = int(self.part_t[tri])
            ii_, jj_ = int(round((c[0] - self.u0) / g)), int(round((c[2] - self.v0) / g))
            r_ = max(1, int(round(0.04 / g)))
            j0_, j1_ = max(0, jj_ - r_), min(self.nv, jj_ + r_ + 1)
            i0_, i1_ = max(0, ii_ - r_), min(self.nu, ii_ + r_ + 1)
            if j1_ <= j0_ or i1_ <= i0_:
                return True
            ytw = yt[j0_:j1_, i0_:i1_]
            top_ = float(np.nanmax(ytw)) if np.isfinite(ytw).any() else float(c[1])
            mine = self.PART[j0_:j1_, i0_:i1_] == p_
            if not mine.any():
                return False
            return not (np.nan_to_num(self.Z[j0_:j1_, i0_:i1_], nan=1e9)[mine].min() < top_ - 0.005)

        for cap in self._caps:
            Vc, rl, an = cap['V'], cap['role'], cap['anchor']
            for q in np.nonzero(rl <= 1)[0]:
                p = Vc[q]
                loc, nr_, idx_, dd = mb.ray_cast(Vec((p[0], p[1] + 0.002, p[2])), up, 3.0)
                if loc is not None and nr_.y < -0.85 and hangs(p, self._all_t[idx_]):
                    (und if dd < 0.01 else shd).append(p)
            for q in np.nonzero(((rl == 1) | (rl == 2) | (rl == 4)) & (an >= 0))[0]:
                a, p = Vc[an[q]], Vc[q]
                if rl[q] == 4 and p[1] < Vc[an[q]][1] - 1.0:
                    continue
                d = p - a
                Ld = float(np.linalg.norm(d))
                if Ld < 1e-4:
                    continue
                dv = Vec(tuple(d / Ld))
                o = Vec(tuple(a))
                ncr, first, trav = 0, None, 0.0
                while trav < Ld and ncr < 4:
                    loc, _, _, dd = mb.ray_cast(o, dv, Ld - trav)
                    if loc is None:
                        break
                    ncr += 1
                    trav += dd + 1e-4
                    if first is None:
                        first = trav
                    o = loc + dv * 1e-4
                if ncr >= 2 or (ncr == 1 and Ld - first > 0.03):
                    thr.append(p)
            sel_ = np.nonzero(rl >= 3)[0]
            if len(sel_) == 0:
                sel_ = np.arange(len(Vc))
            if not any(mb.find_nearest(Vec(tuple(Vc[q])), 0.02)[0] is not None for q in sel_[::max(1, len(sel_) // 300)]):
                flo.append(Vc.mean(0))
        put('under', und)
        put('shaded', shd)
        put('through', thr)
        uds = []
        # (only where the model covers the snow from above: a buried low end of a slat meets it with a face looking
        # down and is fine)
        for si_, mi in sb.overlap(mb):
            t_ = self._all_t[mi]
            if self.n_t[t_, 1] < -0.85:
                c_ = V[F[si_]].mean(0)
                if hangs(c_, t_):
                    uds.append(c_)
        put('underside', uds)
        put('floating', flo)
        # folds in the top
        A_, B_, C_ = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
        fn = np.cross(B_ - A_, C_ - A_)
        fn /= np.maximum(np.linalg.norm(fn, axis=1), 1e-15)[:, None]
        E = np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), axis=1)
        fid = np.tile(np.arange(len(F)), 3)
        o_ = np.lexsort((E[:, 1], E[:, 0]))
        E, fid = E[o_], fid[o_]
        same = np.all(E[1:] == E[:-1], axis=1)
        fa, fb = fid[:-1][same], fid[1:][same]
        Es = E[:-1][same]
        cosang = np.sum(fn[fa] * fn[fb], axis=1)
        # the vertex of face b off the shared edge: above face a's plane is a valley
        opp = F[fb].sum(1) - Es.sum(1)
        valley = np.sum(fn[fa] * (V[opp] - V[Es[:, 0]]), axis=1) > 1e-6
        # (on the top proper: the round of a nose or a rim turns sharply by design)
        upf = (fn[fa, 1] > 0.75) & (fn[fb, 1] > 0.75)
        cr = upf & (((cosang < math.cos(math.radians(35)))) | (valley & (cosang < math.cos(math.radians(25)))))
        ci = np.nonzero(cr)[0]
        ci = ci[np.argsort(cosang[ci])]
        put('crease', (V[Es[ci, 0]] + V[Es[ci, 1]]) / 2.0)
        if len(ci):
            # the worst first, with its angle and whether a valley
            res['crease'] = (len(ci), [tuple(round(float(c), 3) for c in (V[Es[q, 0]] + V[Es[q, 1]]) / 2.0) +
                                       (int(round(math.degrees(math.acos(max(-1.0, min(1.0, float(cosang[q]))))))),
                                        'v' if valley[q] else 'r') for q in ci[:4]])
        # open edges: a boundary anywhere but at the foot of a rim
        ft_all = np.concatenate([c['foot'] for c in self._caps]) if self._caps else np.zeros(len(V), bool)
        if len(ft_all) == len(V):
            dup = np.zeros(len(E), bool)
            dup[:-1] |= same
            dup[1:] |= same
            bd = E[~dup]
            op_ = ~(ft_all[bd[:, 0]] & ft_all[bd[:, 1]])
            put('open_edge', (V[bd[op_, 0]] + V[bd[op_, 1]]) / 2.0)
            rl_all = np.concatenate([c['role'] for c in self._caps])
            if op_.any():
                pr_ = collections.Counter(tuple(sorted((int(rl_all[a_]), int(rl_all[b_])))) for a_, b_ in bd[op_])
                res['open_roles'] = (0, [tuple(k_) + (v_,) for k_, v_ in pr_.most_common(4)])
        if len(cosang):
            res['max_angle'] = (int(round(math.degrees(math.acos(max(-1.0, min(1.0, float(cosang[upf].min()))))))) if upf.any() else 0, [])
        return res

    def _part_verts(self, p):
        if not hasattr(self, '_pv_cache'):
            self._pv_cache = {}
        if p not in self._pv_cache:
            self._pv_cache[p] = self.V[np.unique(self.T[self.part_t == p].ravel())]
        return self._pv_cache[p]



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
    m.reset()
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


