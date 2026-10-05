"""Snow baked per model: turns the roof snow sampled in game for every map model (DSTest "bake", files in the client
profile's szbake folder) into one model per snow variant and the script index of them.

Every piece the game would draw (its corners on the roof, its normal, the stages it loses, how much lower it lies)
becomes part of one mesh: the top raised straight up by the slab thickness of the variant (so neighbouring roof planes
stay joined at ridges and hips, as the pieces do), a skirt down to the roof along the normal only where the snow ends
(the pieces draw one under every edge). Rocks are drawn from their height grid instead: a cap over the faces flat
enough to hold snow, thinning out towards its edge so it ends in the rock rather than as a plate standing on it.

    python bake_snow.py <szbake folder> [--only name,name]
"""
import math, os, re, sys, collections, struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'source', 'SeasonZ')
OUT = os.path.join(SRC, 'data', 'baked')
INDEX = os.path.join(SRC, 'scripts', '4_World', 'SeasonZ', 'SZ_BakedIndex.c')
PREFIX = 'SeasonZ'

# variant -> snow stage (texture). 1-3: the stages of the roof snow; 4-7: the closed cover growing deeper. The script
# picks the variant from the snow depth on the object (SZ_RoofSnow.BakedVariant)
VARIANTS = {1: 1, 2: 2, 3: 3, 4: 4, 5: 4, 6: 4, 7: 4}
# slab thickness (m) on flat faces. Buildings and rocks: at least the 5 cm offset of the roof snow, 8-11 cm once the
# cover is closed (it hides roofs whose drawn surface rises above their geometry), growing to 23 cm. Walls, fences and
# wrecks: the thin strip
THICK = {0: {1: 0.05, 2: 0.05, 3: 0.09, 4: 0.11, 5: 0.15, 6: 0.19, 7: 0.23},
         1: {1: 0.015, 2: 0.018, 3: 0.025, 4: 0.035, 5: 0.045, 6: 0.055, 7: 0.065}}
MIN_THICK = {0: {1: 0.05, 2: 0.05, 3: 0.08, 4: 0.08, 5: 0.09, 6: 0.10, 7: 0.11},
             1: {1: 0.015, 2: 0.018, 3: 0.025, 4: 0.035, 5: 0.045, 6: 0.055, 7: 0.065}}
# how far the rounded edge of the snow bulges out over the edge of a roof (m); walls: a share of their strip
OVERHANG = {1: 0.0, 2: 0.01, 3: 0.03, 4: 0.05, 5: 0.075, 6: 0.1, 7: 0.12}
WALL_OVERHANG = 0.45
# the skirt reaches this far below the roof, so the lift the script adds with the distance never opens a gap
SKIRT_EXTRA = 0.015
# texture period on roofs: the closed cover like the roof snow before (a fine grid cell of 7.5 m / 8 covers a quarter of
# the texture); the open stages finer, so a light cover breaks up in small patches instead of metre wide blotches
PERIOD = 3.75
PERIOD_OPEN = 1.6
CUR = {'period': PERIOD}
# narrow gaps the snow bridges (a ridge cap, a valley gutter): another piece this far beyond an edge (mm) at about the
# same height; the bridge reaches this far onto it
GAP_PROBES = (150, 250, 350)
GAP_DY = 350
GAP_OVERLAP = 40
# an edge is inside the snow (a seam or a small step between pieces) when another piece lies just beyond it, at about
# the same height: probes this far out, and pieces within this height
PROBE_OUT = 60
PROBE_DY = 250
# skirts and straight edges are set off the top by this much (m): see build_pieces
DETACH = 0.0006
# a corner where faces meet at more than about 10 degrees (a crease) gets this much more snow (at most 30% of the slab)
CREASE_COS = 0.985
CREASE_EXTRA = 0.04

def slope_factor(ny):
    """snow lies thinner on steep faces: the full slab up to about 25 degrees, under half from 47"""
    return min(1.0, max(0.45, 0.45 + (ny - 0.68) / (0.9 - 0.68) * 0.55))


def tex_path(stage):
    if stage < 4:
        return '%s\\data\\snow\\sz_roofsnow_s%d_ca.paa' % (PREFIX, stage)
    return '%s\\data\\snow\\sz_snow_s%d_ca.paa' % (PREFIX, stage)

def mat_path(stage):
    if stage < 4:
        return '%s\\data\\snow\\sz_roofsnow_s%d.rvmat' % (PREFIX, stage)
    return '%s\\data\\snow\\sz_snow_s%d.rvmat' % (PREFIX, stage)

# ---------------- reading ----------------
class Piece:
    __slots__ = ('kind', 'drop', 'lower', 'n', 'pts', 'support')

class Model:
    def __init__(self):
        self.shape = ''
        self.kind = 0
        self.small = False
        self.wall = False
        self.rock = False
        self.pieces = []
        self.grid = None

def parse(path):
    m = Model()
    rows = []
    gridHead = None
    with open(path, encoding='latin-1') as fh:
        for line in fh:
            parts = line.split()
            if not parts:
                continue
            tag = parts[0]
            if tag == 'model':
                kv = dict(zip(parts[2::2], parts[3::2]))
                m.shape = parts[1]
                m.kind = int(kv['kind'])
                m.small = kv['small'] in ('1', 'true')
                m.wall = kv['wall'] in ('1', 'true')
                m.rock = kv['rock'] in ('1', 'true')
            elif tag == 't':
                p = Piece()
                p.kind = parts[1]
                p.drop = int(float(parts[2]))
                p.lower = int(float(parts[3])) / 1000.0
                n = [float(parts[4]) / 1000.0, float(parts[5]) / 1000.0, float(parts[6]) / 1000.0]
                ln = math.sqrt(sum(c * c for c in n)) or 1.0
                p.n = tuple(c / ln for c in n)
                nc = int(parts[7])
                vals = [int(float(v)) for v in parts[8:8 + 3 * nc]]
                p.pts = [tuple(vals[3 * k:3 * k + 3]) for k in range(nc)]
                rest = parts[8 + 3 * nc:]
                p.support = int(rest[1]) if len(rest) >= 2 and rest[0] == 's' else 5
                m.pieces.append(p)
            elif tag == 'grid':
                gridHead = [int(float(v)) for v in parts[1:6]]
            elif tag == 'r':
                rows.append([None if v == 'x' else int(v) / 1000.0 for v in parts[1:]])
    if gridHead:
        nu, nv, step, u0, v0 = gridHead
        m.grid = (nu, nv, step / 1000.0, u0 / 1000.0, v0 / 1000.0, rows)
    return m

# ---------------- mesh ----------------
class Mesh:
    def __init__(self):
        self.pts = []
        self.pindex = {}
        self.normals = []
        self.nindex = {}
        self.faces = []

    def point(self, p):
        key = (round(p[0], 4), round(p[1], 4), round(p[2], 4))
        i = self.pindex.get(key)
        if i is None:
            i = len(self.pts)
            self.pts.append(key)
            self.pindex[key] = i
        return i

    def normal(self, n):
        key = (round(n[0], 3), round(n[1], 3), round(n[2], 3))
        i = self.nindex.get(key)
        if i is None:
            i = len(self.normals)
            self.normals.append(key)
            self.nindex[key] = i
        return i

    def face(self, verts, stage):
        # verts: (point, normal, u, v)
        self.faces.append(([(self.point(p), self.normal(n), u, v) for (p, n, u, v) in verts], stage))

def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])

def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

def uv_top(p):
    return (p[0] / CUR['period'], -p[2] / CUR['period'])

def add_skirt(mesh, at, bt, ab, bb, n, depth, stage, out):
    ua, va = uv_top(at)
    ub, vb = uv_top(bt)
    dv = depth / CUR['period']
    A = (at, n, ua + 8.0, va)
    B = (bt, n, ub + 8.0, vb)
    Ab = (ab, n, ua + 8.0, va + dv)
    Bb = (bb, n, ub + 8.0, vb + dv)
    # one side, facing out of the snow (inside it lies the roof); lit like the snow surface. The engine's front side
    # is the one the corners run clockwise on (left handed space)
    if dot(cross(sub(bt, at), sub(bb, at)), out) > 0:
        mesh.face([B, A, Ab], stage)
        mesh.face([B, Ab, Bb], stage)
    else:
        mesh.face([A, B, Bb], stage)
        mesh.face([A, Bb, Ab], stage)

def point_in(x, z, pts):
    inside = False
    n = len(pts)
    for i in range(n):
        x1, _, z1 = pts[i]
        x2, _, z2 = pts[(i + 1) % n]
        if (z1 > z) != (z2 > z):
            xc = x1 + (z - z1) * (x2 - x1) / (z2 - z1)
            if xc > x:
                inside = not inside
    return inside

def plane_y(p, x, z):
    x0, y0, z0 = p.pts[0]
    nx, ny, nz = p.n
    if ny < 0.05:
        return y0
    return y0 - (nx * (x - x0) + nz * (z - z0)) / ny

# corners of neighbouring pieces closer than this (mm) are one corner; a corner this close to the edge of a neighbour
# splits that edge (the pieces then join without the hairline cracks of separate pieces)
SNAP_XZ = 15
SNAP_Y = 60
SNAP_CELL = 30
TJ_XZ = 12

def weld(act):
    """the corners of the pieces snapped together and the T-junctions split: per piece its polygon (mm points)"""
    reps = collections.defaultdict(list)
    def snap(c, layer):
        cx, cz = c[0] // SNAP_CELL, c[2] // SNAP_CELL
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for r in reps.get((layer, cx + dx, cz + dz), ()):
                    if abs(r[0] - c[0]) <= SNAP_XZ and abs(r[2] - c[2]) <= SNAP_XZ and abs(r[1] - c[1]) <= SNAP_Y:
                        return r
        reps[(layer, cx, cz)].append(c)
        return c
    polys = []
    for p in act:
        poly = []
        for c in p.pts:
            s = snap(c, p.lower)
            if not poly or poly[-1] != s:
                poly.append(s)
        if len(poly) > 1 and poly[0] == poly[-1]:
            poly.pop()
        polys.append(poly)
    vcells = collections.defaultdict(set)
    for p, poly in zip(act, polys):
        for c in poly:
            vcells[(p.lower, c[0] // 1000, c[2] // 1000)].add(c)
    count = collections.Counter()
    for p, poly in zip(act, polys):
        for k in range(len(poly)):
            a, b = poly[k], poly[(k + 1) % len(poly)]
            count[(p.lower, min(a, b), max(a, b))] += 1
    out = []
    for p, poly in zip(act, polys):
        res = []
        n = len(poly)
        for k in range(n):
            a, b = poly[k], poly[(k + 1) % n]
            res.append(a)
            if count[(p.lower, min(a, b), max(a, b))] >= 2:
                continue
            ex, ey, ez = b[0] - a[0], b[1] - a[1], b[2] - a[2]
            l2 = ex * ex + ez * ez
            if l2 < 900:
                continue
            cand = []
            for cx in range(min(a[0], b[0]) // 1000, max(a[0], b[0]) // 1000 + 1):
                for cz in range(min(a[2], b[2]) // 1000, max(a[2], b[2]) // 1000 + 1):
                    for c in vcells.get((p.lower, cx, cz), ()):
                        if c == a or c == b:
                            continue
                        t = ((c[0] - a[0]) * ex + (c[2] - a[2]) * ez) / l2
                        if t <= 0.01 or t >= 0.99:
                            continue
                        if (c[0] - a[0] - ex * t) ** 2 + (c[2] - a[2] - ez * t) ** 2 > TJ_XZ * TJ_XZ:
                            continue
                        if abs(a[1] + ey * t - c[1]) > SNAP_Y:
                            continue
                        cand.append((t, c))
            for t, c in sorted(cand):
                if c != res[-1]:
                    res.append(c)
        out.append(res)
    return out

# a gap piece (lower > 0) hanging this far (mm) under the roof plane next to it follows something lower (a frame under
# a chamfered corner): it would stand as a flap
HANG_TOL = 60
# pieces resting on the structure at fewer of their five points than this are left out (see build_pieces)
MIN_SUPPORT = 2
# opposite edges of the snow this close (m) and at about this height difference are bridged (ridge caps, hips, valley
# gutters); the bridge bulges up a little in its middle
BRIDGE_MAX = 0.30
BRIDGE_DY = 0.06
BRIDGE_RAISE = 0.05

def poly_dist(x, z, pts):
    if point_in(x, z, pts):
        return 0.0
    best = 1e18
    n = len(pts)
    for i in range(n):
        x1, _, z1 = pts[i]
        x2, _, z2 = pts[(i + 1) % n]
        ex, ez = x2 - x1, z2 - z1
        l2 = ex * ex + ez * ez
        t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((x - x1) * ex + (z - z1) * ez) / l2))
        dx, dz = x1 + ex * t - x, z1 + ez * t - z
        best = min(best, dx * dx + dz * dz)
    return math.sqrt(best)

def drop_hanging(act):
    mains = [p for p in act if p.lower == 0]
    cells = collections.defaultdict(list)
    for q in mains:
        xs = [c[0] for c in q.pts]
        zs = [c[2] for c in q.pts]
        for cx in range((min(xs) - 600) // 1000, (max(xs) + 600) // 1000 + 1):
            for cz in range((min(zs) - 600) // 1000, (max(zs) + 600) // 1000 + 1):
                cells[(cx, cz)].append(q)
    out = []
    for p in act:
        if p.lower == 0:
            out.append(p)
            continue
        hanging = False
        for c in p.pts:
            near = None
            nd = 600.0
            for q in cells.get((c[0] // 1000, c[2] // 1000), ()):
                d = poly_dist(c[0], c[2], q.pts)
                if d < nd:
                    nd, near = d, q
            if near is not None and c[1] < plane_y(near, c[0], c[2]) - HANG_TOL:
                hanging = True
                break
        if not hanging:
            out.append(p)
    return out

def add_bridges(mesh, edges_out, stage_of):
    """bridges between opposite edges of the snow (see BRIDGE_MAX); returns per edge key the share of it bridged"""
    share = collections.defaultdict(float)
    cells = collections.defaultdict(list)
    for i, e in enumerate(edges_out):
        mx = (e['a'][0] + e['b'][0]) * 0.5
        mz = (e['a'][2] + e['b'][2]) * 0.5
        cells[(int(math.floor(mx / 0.5)), int(math.floor(mz / 0.5)))].append(i)
    for i, e in enumerate(edges_out):
        a, b, o = e['a'], e['b'], e['o']
        ux, uz = b[0] - a[0], b[2] - a[2]
        le = math.hypot(ux, uz)
        if le < 0.02:
            continue
        ux, uz = ux / le, uz / le
        mx = (a[0] + b[0]) * 0.5
        mz = (a[2] + b[2]) * 0.5
        cx, cz = int(math.floor(mx / 0.5)), int(math.floor(mz / 0.5))
        for dx in (-2, -1, 0, 1, 2):
            for dz in (-2, -1, 0, 1, 2):
                for j in cells.get((cx + dx, cz + dz), ()):
                    if j <= i:
                        continue
                    f = edges_out[j]
                    if f['idx'] == e['idx']:
                        continue
                    if o[0] * f['o'][0] + o[2] * f['o'][2] > -0.7:
                        continue
                    fa, fb = f['a'], f['b']
                    fm = ((fa[0] + fb[0]) * 0.5, (fa[1] + fb[1]) * 0.5, (fa[2] + fb[2]) * 0.5)
                    d = (fm[0] - mx) * o[0] + (fm[2] - mz) * o[2]
                    if d <= 0.005 or d > BRIDGE_MAX:
                        continue
                    if abs(fm[1] - (a[1] + b[1]) * 0.5) > BRIDGE_DY:
                        continue
                    s0 = (fa[0] - a[0]) * ux + (fa[2] - a[2]) * uz
                    s1 = (fb[0] - a[0]) * ux + (fb[2] - a[2]) * uz
                    lo, hi = max(0.0, min(s0, s1)), min(le, max(s0, s1))
                    lf = math.hypot(fb[0] - fa[0], fb[2] - fa[2])
                    if hi - lo < 0.3 * min(le, lf) or hi - lo < 0.02:
                        continue
                    def on_e(s):
                        t = s / le
                        return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)
                    def on_f(p):
                        t = ((p[0] - fa[0]) * (fb[0] - fa[0]) + (p[2] - fa[2]) * (fb[2] - fa[2])) / max(1e-9, lf * lf)
                        t = max(0.0, min(1.0, t))
                        return (fa[0] + (fb[0] - fa[0]) * t, fa[1] + (fb[1] - fa[1]) * t, fa[2] + (fb[2] - fa[2]) * t)
                    e0, e1 = on_e(lo), on_e(hi)
                    f0, f1 = on_f(e0), on_f(e1)
                    raise_ = min(BRIDGE_RAISE, 0.25 * d)
                    m0 = ((e0[0] + f0[0]) * 0.5, max(e0[1], f0[1]) + raise_, (e0[2] + f0[2]) * 0.5)
                    m1 = ((e1[0] + f1[0]) * 0.5, max(e1[1], f1[1]) + raise_, (e1[2] + f1[2]) * 0.5)
                    st = min(stage_of[e['idx']], stage_of[f['idx']])
                    for quad in ((e0, e1, m1, m0), (m0, m1, f1, f0)):
                        for tri in ((0, 1, 2), (0, 2, 3)):
                            pts = [quad[t] for t in tri]
                            fn = cross(sub(pts[1], pts[0]), sub(pts[2], pts[0]))
                            if dot(fn, fn) < 1e-12:
                                continue
                            if fn[1] > 0:
                                pts = [pts[0], pts[2], pts[1]]
                            mesh.face([(pt, (0.0, 1.0, 0.0), *uv_top(pt)) for pt in pts], st)
                    share[e['key']] += (hi - lo) / le
                    share[f['key']] += (hi - lo) / max(lf, 1e-6)
    return share


def build_pieces(model, variant):
    stage = VARIANTS[variant]
    wall = model.kind == 1
    kind = 1 if wall else 0
    thick = THICK[kind][variant]
    tmin = MIN_THICK[kind][variant]
    # pieces resting on the structure at under two of their five points lie over air (a plane carried on past a cab
    # roof or over a flight of open stairs): left out
    act = drop_hanging([p for p in model.pieces if stage - p.drop >= 1 and p.support >= MIN_SUPPORT])
    if not act:
        return None
    polys = weld(act)
    # thickness at every corner: thinner on steep faces; where faces meet at an angle (ridges, hips, valleys) the
    # thickest of them and a little more, so the snow covers the ridge tiles that stand above the geometry the rays
    # found, and fills the valleys
    vt = {}
    vn = collections.defaultdict(list)
    for p, poly in zip(act, polys):
        tp = thick if wall else max(tmin, thick * slope_factor(p.n[1]))
        for c in poly:
            k = (c, p.lower)
            vt[k] = max(vt.get(k, 0.0), tp)
            vn[k].append(p.n)
    if not wall:
        for k, ns in vn.items():
            if len(ns) > 1 and min(dot(a, b) for a in ns for b in ns) < CREASE_COS:
                vt[k] += min(CREASE_EXTRA, 0.3 * thick)
    edges = collections.Counter()
    for p, poly in zip(act, polys):
        nc = len(poly)
        for k in range(nc):
            a, b = poly[k], poly[(k + 1) % nc]
            edges[(p.lower, min(a, b), max(a, b))] += 1
    cells = collections.defaultdict(list)
    for idx, p in enumerate(act):
        xs = [c[0] for c in p.pts]
        zs = [c[2] for c in p.pts]
        for cx in range(min(xs) // 1000, max(xs) // 1000 + 1):
            for cz in range(min(zs) // 1000, max(zs) // 1000 + 1):
                cells[(cx, cz)].append(idx)
    def covering(x, z, y, me):
        for idx in cells.get((int(x // 1000), int(z // 1000)), ()):
            if idx == me:
                continue
            q = act[idx]
            if point_in(x, z, q.pts) and abs(plane_y(q, x, z) - y) < PROBE_DY:
                return idx
        return -1
    tops = []
    for p, poly in zip(act, polys):
        tops.append([(c[0] / 1000.0, c[1] / 1000.0 + vt[(c, p.lower)] - p.lower, c[2] / 1000.0) for c in poly])
    # every edge of the snow that no other piece shares: inside the snow (a seam or a small step under another piece: a
    # short skirt) or where the snow ends (bridged to the snow across a narrow gap, or a rounded edge)
    kinds = {}
    outer_list = []
    vout = collections.defaultdict(list)
    for idx, (p, poly) in enumerate(zip(act, polys)):
        nc = len(poly)
        gx = sum(c[0] for c in poly) / nc
        gz = sum(c[2] for c in poly) / nc
        for k in range(nc):
            a, b = poly[k], poly[(k + 1) % nc]
            if edges[(p.lower, min(a, b), max(a, b))] >= 2:
                continue
            ex, ez = b[0] - a[0], b[2] - a[2]
            ln = math.hypot(ex, ez)
            if ln < 1:
                continue
            ox, oz = ez / ln, -ex / ln
            if ox * ((a[0] + b[0]) * 0.5 - gx) + oz * ((a[2] + b[2]) * 0.5 - gz) < 0:
                ox, oz = -ox, -oz
            hits = 0
            for f in (0.25, 0.5, 0.75):
                if covering(a[0] + ex * f + ox * PROBE_OUT, a[2] + ez * f + oz * PROBE_OUT, a[1] + (b[1] - a[1]) * f, idx) >= 0:
                    hits += 1
            if hits >= 2:
                kinds[(idx, k)] = ('inner', (ox, 0.0, oz))
                continue
            kinds[(idx, k)] = ('outer', (ox, 0.0, oz))
            outer_list.append({'key': (idx, k), 'idx': idx, 'a': tops[idx][k], 'b': tops[idx][(k + 1) % nc], 'o': (ox, 0.0, oz)})
    mesh = Mesh()
    stage_of = [stage - p.drop for p in act]
    share = add_bridges(mesh, outer_list, stage_of) if True else {}
    for e in outer_list:
        if share.get(e['key'], 0.0) >= 0.7:
            kinds[e['key']] = ('bridged', e['o'])
            continue
        idx, k = e['key']
        poly = polys[idx]
        pa, pb = poly[k], poly[(k + 1) % len(poly)]
        vout[(pa, act[idx].lower)].append((e['o'][0], e['o'][2], pb[0] - pa[0], pb[2] - pa[2]))
        vout[(pb, act[idx].lower)].append((e['o'][0], e['o'][2], pa[0] - pb[0], pa[2] - pb[2]))
    def out_dir(c, lower, own):
        lst = vout.get((c, lower), [])
        if len(lst) == 2:
            # an inner corner (each edge runs on to the outer side of the other): both bulges keep their own direction,
            # a mitred one would fold over the other
            for e1, e2 in ((lst[0], lst[1]), (lst[1], lst[0])):
                if e1[0] * e2[2] + e1[1] * e2[3] > 0.05 * math.hypot(e2[2], e2[3]):
                    return own
            sx = lst[0][0] + lst[1][0]
            sz = lst[0][1] + lst[1][1]
            ln = math.hypot(sx, sz)
            if ln > 0.2:
                ux, uz = sx / ln, sz / ln
                cosh = max(0.5, ux * own[0] + uz * own[2])
                return (ux / cosh, 0.0, uz / cosh)
        return own
    for idx, (p, poly) in enumerate(zip(act, polys)):
        st = stage_of[idx]
        n = p.n
        roof = [(c[0] / 1000.0, c[1] / 1000.0, c[2] / 1000.0) for c in poly]
        ts = [vt[(c, p.lower)] for c in poly]
        top = tops[idx]
        nc = len(top)
        # the top as a fan (front faces up: in the engine's left handed space the corners run clockwise from above)
        for t in range(1, nc - 1):
            tri = [0, t, t + 1]
            f = cross(sub(top[tri[1]], top[0]), sub(top[tri[2]], top[0]))
            if dot(f, f) < 1e-10:
                continue
            if dot(f, n) > 0:
                tri = [0, t + 1, t]
            mesh.face([(top[i], n, *uv_top(top[i])) for i in tri], st)
        for k in range(nc):
            info = kinds.get((idx, k))
            if not info or info[0] == 'bridged':
                continue
            kind_e, o = info
            k2 = (k + 1) % nc
            if kind_e == 'inner':
                # a short skirt, set off the top by a fraction of a millimetre: the engine computes the normals from the
                # faces, and a vertical face sharing the top's corners would darken the whole top next to it
                down = [ts[k] * max(n[1], 0.2) + SKIRT_EXTRA, ts[k2] * max(n[1], 0.2) + SKIRT_EXTRA]
                ta = (top[k][0] + o[0] * DETACH, top[k][1] - DETACH, top[k][2] + o[2] * DETACH)
                tb = (top[k2][0] + o[0] * DETACH, top[k2][1] - DETACH, top[k2][2] + o[2] * DETACH)
                bot = [(ta[0] - n[0] * down[0], ta[1] - n[1] * down[0], ta[2] - n[2] * down[0]),
                       (tb[0] - n[0] * down[1], tb[1] - n[1] * down[1], tb[2] - n[2] * down[1])]
                add_skirt(mesh, ta, tb, bot[0], bot[1], n, max(down), st, o)
                continue
            rings = []
            for j in (k, k2):
                w = out_dir(poly[j], p.lower, o)
                rings.append(edge_ring(roof[j], ts[j] - p.lower, ts[j], w, n, wall, variant))
            add_profile(mesh, rings[0], rings[1], o, st)
    return mesh


# the rounded edge: (outward share of the bulge, share of the height above the roof, angle of the normal from up to out)
RING = ((0.0, 1.0, 12), (0.42, 0.97, 35), (0.78, 0.87, 58), (0.97, 0.68, 80), (1.0, 0.47, 98), (0.86, 0.26, 118),
        (0.55, 0.1, 138), (0.2, None, 155))

def edge_ring(roof, h, t, w, n, wall, variant):
    """the rounded edge of the snow at a corner: from the top (h above the roof) out over the edge and down to just
    under the roof. w: the outward direction (horizontal, longer at a corner so both edges meet).
    Returns [(point, normal, arc)]"""
    r = t * WALL_OVERHANG if wall and variant > 1 else (0.0 if wall else OVERHANG[variant])
    r = min(r, 0.75 * t)
    def nrm(deg):
        a = math.radians(deg)
        ca, sa = math.cos(a), math.sin(a)
        v = (n[0] * ca + w[0] * sa, n[1] * ca + w[1] * sa, n[2] * ca + w[2] * sa)
        ln = math.sqrt(dot(v, v)) or 1.0
        return (v[0] / ln, v[1] / ln, v[2] / ln)
    if r < 0.004:
        pts = [((roof[0] + w[0] * DETACH, roof[1] + h - DETACH, roof[2] + w[2] * DETACH), nrm(30)),
               ((roof[0], roof[1] - SKIRT_EXTRA, roof[2]), nrm(80))]
    else:
        pts = []
        for fr, fu, deg in RING:
            y = roof[1] - SKIRT_EXTRA if fu is None else roof[1] + h * fu
            pts.append(((roof[0] + w[0] * r * fr, y, roof[2] + w[2] * r * fr), nrm(deg)))
    out = []
    arc = 0.0
    for i, (pt, nn) in enumerate(pts):
        if i:
            arc += math.sqrt(dot(sub(pt, pts[i - 1][0]), sub(pt, pts[i - 1][0])))
        out.append((pt, nn, arc))
    return out

def add_profile(mesh, ra, rb, out, stage):
    ua, va = uv_top(ra[0][0])
    ub, vb = uv_top(rb[0][0])
    for s in range(len(ra) - 1):
        A0 = (ra[s][0], ra[s][1], ua, va + ra[s][2] / CUR['period'])
        A1 = (ra[s + 1][0], ra[s + 1][1], ua, va + ra[s + 1][2] / CUR['period'])
        B0 = (rb[s][0], rb[s][1], ub, vb + rb[s][2] / CUR['period'])
        B1 = (rb[s + 1][0], rb[s + 1][1], ub, vb + rb[s + 1][2] / CUR['period'])
        f = cross(sub(B0[0], A0[0]), sub(B1[0], A0[0]))
        if dot(f, out) > 0:
            mesh.face([B0, A0, A1], stage)
            mesh.face([B0, A1, B1], stage)
        else:
            mesh.face([A0, B0, B1], stage)
            mesh.face([A0, B1, A1], stage)


# rocks: the snow lies on faces up to about 40 degrees (it thins out from 33), on cells whose corners all hit the rock
ROCK_FULL_NY = 0.84
ROCK_ZERO_NY = 0.76
ROCK_SINK = 0.06
# the whole cap lies this much lower than the rock the rays found: the drawn rock is a little smaller than that, and
# rock showing through the snow looks natural where a floating edge would not
ROCK_BIAS = 0.02
# the cap ends where the weight of the face falls below ROCK_EDGE and is at full thickness from ROCK_THICK_AT
ROCK_EDGE = 0.3
ROCK_THICK_AT = 0.6
# the cap reaches its full thickness this many thicknesses in from its edge
ROCK_TAPER = 3.0
ROCK_MIN_AREA = 0.25

def build_rock(model, variant):
    if not model.grid:
        return None
    stage = VARIANTS[variant]
    thick = THICK[0][variant]
    nu, nv, step0, u0, v0, rows = model.grid
    if len(rows) != nv:
        return None
    # work grid: about 48 cells across the rock at most, 20 cm at least
    size = max(nu, nv) * step0
    k = max(2, int(math.ceil(size / 48.0 / step0)))
    step = step0 * k
    wu = (nu - 1) // k + 1
    wv = (nv - 1) // k + 1
    H = [[rows[min(j * k, nv - 1)][min(i * k, nu - 1)] for i in range(wu)] for j in range(wv)]
    # a missing sample with rock all around it (a ray through a crack of the geometry) takes their mean
    for j in range(1, wv - 1):
        for i in range(1, wu - 1):
            if H[j][i] is None:
                ns = [H[j + dj][i + di] for dj in (-1, 0, 1) for di in (-1, 0, 1) if (di or dj) and H[j + dj][i + di] is not None]
                if len(ns) >= 6:
                    H[j][i] = sum(ns) / len(ns)
    def hv(i, j):
        if 0 <= i < wu and 0 <= j < wv:
            return H[j][i]
        return None
    # how flat the rock is at each point (the steeper side counts: the lip of a ledge holds no snow)
    W = [[0.0] * wu for _ in range(wv)]
    G = [[(0.0, 1.0, 0.0)] * wu for _ in range(wv)]
    for j in range(wv):
        for i in range(wu):
            h = H[j][i]
            if h is None:
                continue
            gx = [(h - hv(i - 1, j)) / step] if hv(i - 1, j) is not None else []
            if hv(i + 1, j) is not None:
                gx.append((hv(i + 1, j) - h) / step)
            gz = [(h - hv(i, j - 1)) / step] if hv(i, j - 1) is not None else []
            if hv(i, j + 1) is not None:
                gz.append((hv(i, j + 1) - h) / step)
            if not gx or not gz:
                continue
            sx = max(gx, key=abs)
            sz = max(gz, key=abs)
            ny = 1.0 / math.sqrt(1.0 + sx * sx + sz * sz)
            W[j][i] = min(1.0, max(0.0, (ny - ROCK_ZERO_NY) / (ROCK_FULL_NY - ROCK_ZERO_NY)))
            ax = sum(gx) / len(gx)
            az = sum(gz) / len(gz)
            ln = math.sqrt(ax * ax + 1.0 + az * az)
            G[j][i] = (-ax / ln, 1.0 / ln, -az / ln)
    # softened twice, so the edge of the cap runs smoothly instead of following single samples
    S = W
    for _ in range(2):
        T = [[0.0] * wu for _ in range(wv)]
        for j in range(wv):
            for i in range(wu):
                if H[j][i] is None:
                    continue
                tot = wsum = 0.0
                for dj in (-1, 0, 1):
                    for di in (-1, 0, 1):
                        if hv(i + di, j + dj) is not None:
                            f = 2.0 if dj == 0 and di == 0 else 1.0
                            tot += S[j + dj][i + di] * f
                            wsum += f
                T[j][i] = tot / wsum
        S = T
    def inside(i, j):
        return H[j][i] is not None and S[j][i] > ROCK_EDGE
    # the cells the cap touches; a cell over a cliff (its corners far apart in height) holds none
    cells = set()
    for j in range(wv - 1):
        for i in range(wu - 1):
            cs = ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))
            if not any(inside(a, b) for a, b in cs):
                continue
            hs = [H[b][a] for a, b in cs if H[b][a] is not None]
            if max(hs) - min(hs) > step * 1.3:
                continue
            cells.add((i, j))
    # without the small islands
    seen = set()
    keep = set()
    for c in cells:
        if c in seen:
            continue
        comp = []
        stack = [c]
        seen.add(c)
        while stack:
            x = stack.pop()
            comp.append(x)
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                y = (x[0] + d[0], x[1] + d[1])
                if y in cells and y not in seen:
                    seen.add(y)
                    stack.append(y)
        if len(comp) * step * step >= ROCK_MIN_AREA:
            keep.update(comp)
    if not keep:
        return None
    # distance from every point of the cap to its edge: the cap thins out towards it like a pile of snow, so it ends in
    # the rock instead of as a slab standing on it
    dist = [[1e9] * wu for _ in range(wv)]
    queue = collections.deque()
    for j in range(wv):
        for i in range(wu):
            if not inside(i, j):
                dist[j][i] = 0.0
                queue.append((i, j))
    while queue:
        i, j = queue.popleft()
        for di, dj, dd in ((1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)):
            ni, nj = i + di, j + dj
            if 0 <= ni < wu and 0 <= nj < wv and dist[nj][ni] > dist[j][i] + dd * step + 1e-9:
                dist[nj][ni] = dist[j][i] + dd * step
                queue.append((ni, nj))
    taper = max(0.25, ROCK_TAPER * thick)
    def lift(w, d):
        f = min(1.0, max(0.0, (w - ROCK_EDGE) / (ROCK_THICK_AT - ROCK_EDGE)))
        g = min(1.0, max(0.0, d - step) / taper)
        f = f * f * (3.0 - 2.0 * f) * g * g * (3.0 - 2.0 * g)
        return thick * f - ROCK_SINK * (1.0 - f) - ROCK_BIAS
    def corner(i, j):
        return ((u0 + i * step, H[j][i] + lift(S[j][i], dist[j][i]), v0 + j * step), G[j][i])
    def edge(a, b):
        # a inside, b outside: where the weight crosses the edge of the cap (the snow ends there, sunk into the rock)
        ia, ja = a
        ib, jb = b
        if H[jb][ib] is None:
            t = 0.3
            h = H[ja][ia]
        else:
            sa, sb = S[ja][ia], S[jb][ib]
            t = min(0.5, max(0.0, (sa - ROCK_EDGE) / max(1e-6, sa - sb)))
            h = H[ja][ia] + (H[jb][ib] - H[ja][ia]) * t
        x = u0 + (ia + (ib - ia) * t) * step
        z = v0 + (ja + (jb - ja) * t) * step
        return ((x, h - ROCK_SINK, z), G[ja][ia])
    mesh = Mesh()
    for (i, j) in sorted(keep):
        cs = ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))
        poly = []
        for q in range(4):
            a, b = cs[q], cs[(q + 1) % 4]
            ina, inb = inside(*a), inside(*b)
            if ina:
                poly.append(corner(*a))
            if ina != inb:
                poly.append(edge(a, b) if ina else edge(b, a))
        if len(poly) < 3:
            continue
        for t in range(1, len(poly) - 1):
            tri = [poly[0], poly[t], poly[t + 1]]
            pts = [v[0] for v in tri]
            fn = cross(sub(pts[1], pts[0]), sub(pts[2], pts[0]))
            if abs(fn[1]) < 1e-9:
                continue
            order = [0, 1, 2] if fn[1] < 0 else [0, 2, 1]
            mesh.face([(tri[o][0], tri[o][1], *uv_top(tri[o][0])) for o in order], stage)
    return mesh


# ---------------- MLOD writing ----------------
def asciiz(s):
    return s.encode('ascii') + b'\x00'

def mlod_bytes(mesh):
    out = bytearray(b'P3DM')
    out += struct.pack('<IIIIII', 0x1C, 0x100, len(mesh.pts), len(mesh.normals), len(mesh.faces), 0)
    for (x, y, z) in mesh.pts:
        out += struct.pack('<fffI', x, y, z, 0)
    for (x, y, z) in mesh.normals:
        out += struct.pack('<fff', x, y, z)
    for verts, stage in mesh.faces:
        out += struct.pack('<I', len(verts))
        for i in range(4):
            if i < len(verts):
                p, n, u, v = verts[i]
            else:
                p, n, u, v = 0, 0, 0.0, 0.0
            out += struct.pack('<IIff', p, n, u, v)
        out += struct.pack('<I', 0)
        out += asciiz(tex_path(stage)) + asciiz(mat_path(stage))
    out += b'TAGG'
    def tag(name, data):
        out.extend(b'\x01' + asciiz(name) + struct.pack('<I', len(data)) + data)
    tag('#Property#', b'lodnoshadow'.ljust(64, b'\x00') + b'1'.ljust(64, b'\x00'))
    uv = struct.pack('<I', 0)
    for verts, stage in mesh.faces:
        for (p, n, u, v) in verts:
            uv += struct.pack('<ff', u, v)
    tag('#UVSet#', uv)
    tag('#EndOfFile#', b'')
    out += struct.pack('<f', 1.0)
    return bytes(b'MLOD' + struct.pack('<II', 257, 1) + out)

# ---------------- main ----------------
def short_name(shape, used):
    base = os.path.basename(shape)[:-4] if shape.endswith('.p3d') else os.path.basename(shape)
    name = re.sub(r'[^a-z0-9_]', '_', base.lower())
    if name in used and used[name] != shape:
        parent = os.path.basename(os.path.dirname(shape))
        name = re.sub(r'[^a-z0-9_]', '_', (parent + '_' + base).lower())
        k = 2
        while name in used and used[name] != shape:
            name = '%s_%d' % (name, k)
            k += 1
    used[name] = shape
    return name

def main():
    src = sys.argv[1]
    only = None
    if '--only' in sys.argv:
        only = set(sys.argv[sys.argv.index('--only') + 1].split(','))
    os.makedirs(OUT, exist_ok=True)
    if only is None:
        for fn in os.listdir(OUT):
            if fn.endswith('.p3d'):
                os.remove(os.path.join(OUT, fn))
    used = {}
    index = []
    stats = []
    for fn in sorted(os.listdir(src)):
        if not fn.endswith('.txt'):
            continue
        m = parse(os.path.join(src, fn))
        if not m.shape:
            continue
        name = short_name(m.shape, used)
        if only is not None and name not in only:
            continue
        made = 0
        faces = []
        for variant in VARIANTS:
            CUR['period'] = PERIOD_OPEN if VARIANTS[variant] < 4 else PERIOD
            mesh = build_rock(m, variant) if m.rock else build_pieces(m, variant)
            if mesh is None or not mesh.faces:
                break
            data = mlod_bytes(mesh)
            with open(os.path.join(OUT, '%s_v%d.p3d' % (name, variant)), 'wb') as fh:
                fh.write(data)
            made += 1
            faces.append(len(mesh.faces))
        if made == len(VARIANTS):
            index.append((m.shape, name))
            stats.append((name, len(m.pieces), faces))
        else:
            for variant in VARIANTS:
                p = os.path.join(OUT, '%s_v%d.p3d' % (name, variant))
                if os.path.exists(p):
                    os.remove(p)
            # sampled at full detail and found to carry no snow: the game skips it ("-"). Rocks without a flat face
            # stay sampled, a tilted one can have one
            if not m.rock and not m.pieces:
                index.append((m.shape, '-'))
    if only is None:
        lines = ['//! generated by tools/bake_snow.py: the map models with baked snow (shape -> name of the models in data/baked)',
                 'class SZ_BakedIndex', '{', '\tstatic void Fill(map<string, string> m)', '\t{']
        for shape, name in sorted(index):
            lines.append('\t\tm.Insert("%s", "%s");' % (shape.replace('\\', '\\\\'), name))
        lines += ['\t}', '}', '']
        with open(INDEX, 'w', newline='\r\n') as fh:
            fh.write('\n'.join(lines))
    total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT) if f.endswith('.p3d'))
    print('baked models', len(index), 'files', len(index) * len(VARIANTS), 'MLOD bytes', total)
    for s in stats[:40]:
        print(' ', s)

if __name__ == '__main__':
    main()

