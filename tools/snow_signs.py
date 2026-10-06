"""SeasonZ snow on road signs and other thin plates on posts (Opus, 6 Oct 2026).

The volumetric cap (snow_addon) and the raster blankets cannot see a sign: its plate is 4 mm thick, far under their 1 cm
lattice, and its posts' sawn tops (6 cm) were dropped as tips. Every sign stayed bare in all seven depths (review r10).

Real snow on a sign: a narrow rounded ridge along the plate's level top edge, a little wider than the plate and rolling
just past both faces, rounding off where the edge ends or turns down (a chamfered corner, a triangle's flank); a small cap
on each post's sawn top. The plate's faces, its clamps and the decals hold none.

edge_ridges: built on the model's own faces, not the raster: the level top strips (faces looking up within 32 degrees,
narrower than 2.5 cm, at least three times as long) of the thin parts, swept station by station across the strip's
actual width; the height grows with the depth (about 1.8 cm at the first, 4.5 cm at the last on a 4 mm plate; cohesive
snow stacks on a thin edge as a loaf about twice as tall as wide).
top_caps: the posts are rods to the raster (thin side faces), so their sawn tops get a dome built on their own top faces:
the outline of the top, seated just below its edge, bulging a little past it and rising to a rounded crown."""
import math
import numpy as np
import snow_hand as H


def _pca(P):
    c = P.mean(0)
    _, _, Vt = np.linalg.svd(P - c, full_matrices=False)
    return c, Vt, np.ptp((P - c) @ Vt.T, axis=0)


def _hull(Q):
    """convex hull of 2D points (monotone chain), counter-clockwise"""
    pts = sorted(set(map(tuple, np.round(Q, 6).tolist())))
    if len(pts) < 3:
        return None
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    h = lo[:-1] + hi[:-1]
    return np.array(h) if len(h) >= 3 else None


def plate_parts(m, thin=0.02, wide=0.10):
    """parts thinner than thin one way and wider than wide another: sign plates, sheet edges"""
    out = []
    for p in range(int(m.part_t.max()) + 1):
        P = m._part_verts(p)
        if len(P) < 4:
            continue
        _, _, ext = _pca(P)
        if ext[-1] < thin and ext[1] > wide:
            out.append(p)
    return out


def post_parts(m, min_len=0.3, max_w=0.15):
    """upright posts: long, narrow both ways, within about 25 degrees of the vertical"""
    out = []
    for p in range(int(m.part_t.max()) + 1):
        P = m._part_verts(p)
        if len(P) < 6:
            continue
        _, Vt, ext = _pca(P)
        if ext[0] > min_len and ext[1] < max_w and abs(Vt[0][1]) > 0.9:
            out.append(p)
    return out


def _clusters(m, tt, gap=0.01):
    """the faces tt split where their mean heights part by more than gap"""
    if not len(tt):
        return []
    y = m.V[m.T[tt]][:, :, 1].mean(1)
    o = np.argsort(y)
    cuts = np.nonzero(np.diff(y[o]) > gap)[0] + 1
    return [tt[o[a:b]] for a, b in zip(np.r_[0, cuts], np.r_[cuts, len(o)])]


def _cross(T3, c, u, w, s):
    """where the line across the strip at station s meets its faces: (a, b, y) or None"""
    pu = (T3[:, :, [0, 2]] - c) @ u
    pw = (T3[:, :, [0, 2]] - c) @ w
    lo, hi, ys = [], [], []
    for k in range(len(T3)):
        if pu[k].min() - 1e-9 > s or pu[k].max() + 1e-9 < s:
            continue
        pts = []
        for i, j in ((0, 1), (1, 2), (2, 0)):
            a_, b_ = pu[k, i] - s, pu[k, j] - s
            if a_ == b_:
                if abs(a_) < 1e-9:
                    pts += [(pw[k, i], T3[k, i, 1]), (pw[k, j], T3[k, j, 1])]
                continue
            if a_ * b_ <= 0:
                t = a_ / (a_ - b_)
                pts.append((pw[k, i] + t * (pw[k, j] - pw[k, i]), T3[k, i, 1] + t * (T3[k, j, 1] - T3[k, i, 1])))
        if pts:
            q = np.array(pts)
            lo.append(q[:, 0].min()); hi.append(q[:, 0].max()); ys.append(q[:, 1].max())
    if not lo:
        return None
    return min(lo), max(hi), max(ys)


def _ridge(m, T3, v, ny_min):
    """one ridge along the strip of faces T3 (n, 3, 3), or None"""
    from mathutils import Vector as Vec
    P2 = T3[:, :, [0, 2]].reshape(-1, 2)
    c, Vt, ext = _pca(P2)
    u, w = Vt[0], Vt[1]
    L, W = ext[0], ext[1]
    t = m.thick(v)
    Hf = min(t, 0.01 + 1.1 * W + 0.15 * t)
    of = 0.005 + 0.04 * t
    pu = ((P2 - c) @ u)
    s0, s1 = float(pu.min()), float(pu.max())
    re = min(1.2 * Hf + of, 0.3 * L)
    th = np.array([0.35, 0.7, 1.05, 1.4, math.pi / 2])
    ends = re * (1 - np.cos(th))
    inner = np.linspace(s0 + re, s1 - re, max(2, int(math.ceil((L - 2 * re) / 0.03)) + 1)) if L > 2 * re else np.array([])
    S = np.r_[s0 + ends, inner, (s1 - ends)[::-1]]
    F_ = np.r_[np.sin(th), np.ones(len(inner)), np.sin(th)[::-1]]
    order = np.argsort(S, kind='stable')
    S, F_ = S[order], F_[order]
    keep = np.r_[True, np.diff(S) > 1e-4]
    S, F_ = S[keep], F_[keep]
    phi = np.linspace(math.pi, 0, 9)
    up = Vec((0.0, 1.0, 0.0))
    rings, refs = [], []
    for s, f in zip(S, F_):
        cr = _cross(T3, c, u, w, float(np.clip(s, s0 + 1e-5, s1 - 1e-5)))
        if cr is None:
            rings.append(None); refs.append(None)
            continue
        a, b, y0 = cr
        cw, hw = 0.5 * (a + b), 0.5 * (b - a)
        Hs, o = f * Hf, f * of
        # shelter: something over the edge within a metre cuts the ridge down (nothing over a sign's plate)
        p0 = c + u * s + w * cw
        hit = m.bvh_all.ray_cast(Vec((float(p0[0]), float(y0) + 0.003, float(p0[1]))), up, 1.0)
        if hit[0] is not None:
            Hs *= float(np.clip((hit[3] - 0.1) / 0.9, 0, 1))
            o *= float(np.clip((hit[3] - 0.1) / 0.9, 0, 1))
        prof = [(a - 0.0006, y0 - 0.003)]
        prof += [(cw + (hw + o) * math.cos(q), y0 + 0.3 * Hs + 0.7 * Hs * math.sin(q)) for q in phi]
        prof += [(b + 0.0006, y0 - 0.003)]
        ring = np.array([(c[0] + u[0] * s + w[0] * pw_, yy, c[1] + u[1] * s + w[1] * pw_) for pw_, yy in prof])
        rings.append(ring)
        refs.append(np.array((c[0] + u[0] * s + w[0] * cw, y0 + 0.25 * Hs, c[1] + u[1] * s + w[1] * cw)))
    # runs of stations with a cross-section; each run its own ridge with a tip at both ends
    Vs, Fs, Rf = [], [], []
    run = []
    for i in range(len(S) + 1):
        if i < len(S) and rings[i] is not None:
            run.append(i)
            continue
        if len(run) >= 2:
            base = sum(len(x) for x in Vs)
            k = len(rings[run[0]])
            V = np.vstack([rings[j] for j in run])
            n = len(run)
            def tip(j, dirn):
                r = rings[j]; mid = r[1:-1].mean(0)
                return np.array((mid[0] + u[0] * 0.002 * dirn, refs[j][1], mid[2] + u[1] * 0.002 * dirn))
            V = np.vstack([V, tip(run[0], -1), tip(run[-1], 1)])
            ta, tb = n * k, n * k + 1
            F = []
            for i2 in range(n - 1):
                for j in range(k - 1):
                    a0, a1 = i2 * k + j, i2 * k + j + 1
                    b0, b1 = (i2 + 1) * k + j, (i2 + 1) * k + j + 1
                    F += [(a0, b0, b1), (a0, b1, a1)]
            for j in range(k - 1):
                F += [(ta, j, j + 1), (tb, (n - 1) * k + j, (n - 1) * k + j + 1)]
            F = np.array(F, np.int64)
            # outward: every face turned away from the ridge's axis under it
            ref = np.vstack([refs[j] for j in run] + [refs[run[0]], refs[run[-1]]])
            vref = np.repeat(np.arange(n), k)
            vref = np.r_[vref, n, n + 1]
            C = V[F].mean(1)
            N = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
            R_ = ref[np.minimum(vref[F[:, 0]], len(ref) - 1)]
            flip = (N * (C - R_)).sum(1) < 0
            F[flip] = F[flip][:, [0, 2, 1]]
            Vs.append(V); Fs.append(F + base)
        run = []
    if not Vs:
        return None
    return np.vstack(Vs), np.vstack(Fs)


def edge_ridges(m, v, parts, ny_min=0.85, max_w=0.025):
    """ridges along the level top strips of the given (thin) parts"""
    out = []
    for p in parts:
        tt = np.nonzero((m.part_t == p) & (m.n_t[:, 1] >= ny_min))[0]
        for cl in _clusters(m, tt):
            T3 = m.V[m.T[cl]]
            P2 = T3[:, :, [0, 2]].reshape(-1, 2)
            if len(P2) < 3:
                continue
            _, _, ext = _pca(P2)
            if ext[1] > max_w or ext[0] < max(3 * ext[1], 0.05):
                continue
            out.append(_ridge(m, T3, v, ny_min))
    return out


def top_cap(m, part, v, ny_min=0.85, max_w=0.2):
    """a dome on the flat sawn top of a post (part), from its own top faces; None if it has none, it is wider than max_w
    or something lies over it within a metre"""
    from mathutils import Vector as Vec
    tt = np.nonzero((m.part_t == part) & (m.n_t[:, 1] >= ny_min))[0]
    if not len(tt):
        return None
    y = m.V[m.T[tt]][:, :, 1].mean(1)
    tt = tt[y >= y.max() - 0.01]
    P = m.V[m.T[tt]].reshape(-1, 3)
    y0 = float(P[:, 1].max())
    Q = P[:, [0, 2]]
    hull = _hull(Q)
    if hull is None:
        return None
    c = hull.mean(0)
    # an even outline: 24 directions, each the hull's distance from the centre
    ang = np.linspace(0, 2 * math.pi, 24, endpoint=False)
    rad = np.zeros(24)
    for k, a in enumerate(ang):
        d = np.array((math.cos(a), math.sin(a)))
        best = 0.0
        for i in range(len(hull)):
            p0, p1 = hull[i] - c, hull[(i + 1) % len(hull)] - c
            M_ = np.array([d, p0 - p1]).T
            if abs(np.linalg.det(M_)) < 1e-12:
                continue
            s, w = np.linalg.solve(M_, p0)
            if s > 0 and -1e-6 <= w <= 1 + 1e-6:
                best = max(best, s)
        rad[k] = best
    width = 2 * float(rad.min())
    if width <= 0.01 or width > max_w:
        return None
    hit = m.bvh_all.ray_cast(Vec((float(c[0]), y0 + 0.004, float(c[1]))), Vec((0.0, 1.0, 0.0)), 1.0)
    if hit[0] is not None:
        return None
    t = m.thick(v)
    Hc = min(t, 0.75 * width + 0.005)
    o = 0.003 + 0.03 * t
    # profile (radial offset past the edge, height): seated 2 mm under the edge, bulging o past it at a quarter of the
    # height, then a quarter ellipse to the crown
    prof = [(0.001, -0.002), (o, 0.25 * Hc)]
    # (the last ring stops short of the crown: a ring shrunk to a point left degenerate faces, a dark dot on top)
    for q in np.linspace(0.25, 0.9, 6)[1:]:
        th = q * math.pi / 2
        prof.append((None, th))
    V = []
    rings = []
    for kk, pr in enumerate(prof):
        ring = []
        for k, a in enumerate(ang):
            d = np.array((math.cos(a), math.sin(a)))
            r = rad[k]
            if pr[0] is not None:
                rr, hh = r + pr[0], pr[1]
            else:
                th = pr[1]
                rr = (r + o) * math.cos(th)
                hh = 0.25 * Hc + 0.75 * Hc * math.sin(th)
            p = c + d * rr
            ring.append(len(V))
            V.append((p[0], y0 + hh, p[1]))
        rings.append(ring)
    top = len(V)
    V.append((c[0], y0 + Hc, c[1]))
    F = []
    for a_, b_ in zip(rings[:-1], rings[1:]):
        for k in range(24):
            k2 = (k + 1) % 24
            F += [(a_[k], b_[k], b_[k2]), (a_[k], b_[k2], a_[k2])]
    for k in range(24):
        F.append((rings[-1][k], top, rings[-1][(k + 1) % 24]))
    V = np.array(V)
    F = np.array(F, np.int64)
    n = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    C = V[F].mean(1)
    flip = (n * (C - np.array((c[0], y0, c[1])))).sum(1) < 0
    F[flip] = F[flip][:, [0, 2, 1]]
    return V, F


def top_caps(m, v, posts):
    return [top_cap(m, p, v) for p in posts]


def build(m, v):
    """a sign: ridges along its plates' top edges, caps on its posts"""
    if m.g > 0.005:
        m.__init__(m.name, path=m.path, g=0.005)
    plates = plate_parts(m)
    posts = [p for p in post_parts(m) if p not in plates]
    return H.join(edge_ridges(m, v, plates) + top_caps(m, v, posts))


def _top_area(m, p, ny_min=0.7):
    sel = np.nonzero((m.part_t == p) & (m.n_t[:, 1] > ny_min))[0]
    if not len(sel):
        return 0.0
    t = m.V[m.T[sel]]
    return float(np.abs(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])[:, 1]).sum() * .5)


def _leaning_rod(m, p, max_w=0.12, min_len=0.3, tilt=0.5):
    """a strut: long and thin, its axis more than 30 degrees from the horizontal (sin > tilt). (Opus, 6 Oct) the
    diagonal struts behind the roof letters got a fat sausage of snow down their whole length; a strut that steep keeps
    at most a thin line, which the game's distance hides: none"""
    P = m._part_verts(p)
    if len(P) < 6:
        return False
    _, Vt, ext = _pca(P)
    return ext[0] > min_len and ext[1] < max_w and abs(Vt[0][1]) > tilt


def build_auto(m, v, min_top=0.01):
    """the default for road signs without a recipe of their own: plates and posts as in build(); any other part with a
    real top (a small roof, a frame's top board: over min_top m2 seen from above) its addonfine pillow (snow_addon)"""
    if not hasattr(m, '_sz_sign'):
        if m.g > 0.005:
            m.__init__(m.name, path=m.path, g=0.005)
        plates = plate_parts(m)
        posts = [p for p in post_parts(m) if p not in plates]
        rest = [p for p in range(int(m.part_t.max()) + 1) if p not in plates and p not in posts and _top_area(m, p) >= min_top
                and not _leaning_rod(m, p)]
        m._sz_sign = (plates, posts, rest)
    plates, posts, rest = m._sz_sign
    out = edge_ridges(m, v, plates) + top_caps(m, v, posts)
    if rest:
        m._sz_rails = ([], [])
        m._sz_parts = tuple(rest)
        out.append(H.hybrid(m, v))
    return H.join(out)

