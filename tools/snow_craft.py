"""Snow crafted on the real models: for every map model the snow generator reads its visual LOD straight from the game
(odol_extract), finds the top a falling snow reaches (the highest visual surface over a fine grid), lays a blanket on
it for each of the seven snow variants and lets Blender (headless) merge and thin the mesh into three LODs.

The blanket: snow lies where the top is flat enough (thinner on steep faces, none past about 55 degrees), follows the
surface, fills small hollows and covers ridge tiles and small details with a rounded crest, ends with a rounded edge
(a cornice in deep snow) where the surface ends (found to a few millimetres on the model) and tucks under a surface
rising above it. Rocks: the cap thins out into the rock and grows over steeper faces as the snow deepens.

    blender -b --factory-startup --python snow_craft.py -- <szbake dir> <out dir> [--only a,b] [--slice k/n]
"""
import os, sys, math, re, collections, struct, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bake_snow as B
import odol_extract as X
import vis_height as VH

VARIANTS = B.VARIANTS
THICK = B.THICK
OVERHANG = B.OVERHANG
EDGE = 0.4
FULL = 0.75
# the profile of the rounded edge (out, up as shares of its reach and depth). Its first step runs level: the points
# where the top meets the edge keep the normal of the top. Tilted, the game's smoothed normals tilted every long
# triangle of a flat roof that reaches the edge, and the roof showed dark lines along them
RING = ((0.0, 1.0), (0.35, 1.0), (0.72, 0.9), (0.95, 0.72), (1.0, 0.5), (0.88, 0.27), (0.58, 0.1), (0.2, None))
if os.environ.get('SZ_OLDRING'):
    RING = ((0.0, 1.0), (0.42, 0.97), (0.78, 0.87), (0.97, 0.68), (1.0, 0.47), (0.86, 0.26), (0.55, 0.1), (0.2, None))
SKIRT = 0.02
LOD_RES = (1.0, 2.0, 3.0)
CLIMB = os.environ.get('SZ_NOCLIMB') is None
OFF = set(os.environ.get('SZ_OFF', '').split(','))
SPLIT_STEP = float(os.environ.get('SZ_SPLIT', '0.3'))
# ragged models (heaps, sandbags, nets, rubble, mounds): their snow thins out into them like on a rock, no rounded edge
# (a cornice along every sandbag or body would hang as rows of teeth)
ROUGH = re.compile(r'^(dead_pile|dead_massgrave|garbage_pile|misc_bagfence|roadblock_bags|hbarrier|'
                   r'misc_tirepile|mil_camonet|craterlong|rubble_|ruin_rubble|'
                   r'misc_haybale_decayed|mil_reinforcedtank|mil_blastcover\d_grass|mil_fortified_nest_small|'
                   r'mil_artillery_nest)')
# stacks of boards, logs and timbers: each board or log gets its own cap on the fine grid of a fence, with its
# rounded ends, and the snow bridges the narrow gaps between them (as one blanket or a heap it tore into flaps
# and tents over the gaps)
# (Opus, 6 Oct: pallets and woodpiles are no longer 'wall' (1.5-6.5 cm): a pallet deck or a log pile holds the full
# depth like any prop, its logs a crescent as deep as they are wide; only timbers keep the fence table)
BOARDS = re.compile(r'^(misc_timbers)')
# small stacks with a fine structure (bricks on a pallet): the normal cover on a fine grid
FINE = re.compile(r'^(cihly)')
# smooth sheets the snow slides off sooner than off a roof (tent canvas, foil, nets, the smooth concrete face of a
# dam): no snow past about 47 degrees. At the roof limit (55) a sheet of snow stood on the sides of tents and on the
# dam face and ended in torn flaps where the slope crossed the limit
SLICK = re.compile(r'^(medical_tent|mil_tent|misc_polytunnel|mil_camonet|dam_concrete)')
# earth mounds (the berm of a bunker, a blast cover, a crater rim, a dirt pile): their snow line follows the shape of
# the mound over about a metre, not every lump of its earth (a fringe of hanging tongues along the dome of a bunker)
MOUND = re.compile(r'^(mil_reinforcedtank|mil_blastcover|craterlong|rubble_dirtpile)')
# models that get no snow, with the reason
SKIP = {
    'farm_manurepile': 'a manure heap is warm: snow melts on it',
    'dead_pile1': 'a heap of bodies: a cap would bridge the gaps between limbs as a sheet; the ground snow lies around',
    'dead_pile2': 'a heap of bodies: a cap would bridge the gaps between limbs as a sheet; the ground snow lies around',
    'dead_pile3': 'a heap of bodies: a cap would bridge the gaps between limbs as a sheet; the ground snow lies around',
    'dead_pile4': 'a heap of bodies: a cap would bridge the gaps between limbs as a sheet; the ground snow lies around',
    'dead_massgrave': 'a heap of bodies: a cap would bridge the gaps between limbs as a sheet; the ground snow lies around',
    'misc_tirepile': 'stacked tyres: a cap would lie as a sheet over the holes of the tyres',
    'misc_tirepile_group': 'stacked tyres: a cap would lie as a sheet over the holes of the tyres',
    'misc_tirepile_large': 'stacked tyres: a cap would lie as a sheet over the holes of the tyres',
    'mil_reinforcedtank1_grass': 'only tufts of grass standing on the bunker (which has its own cap): snow on blades would be shards',
    'mil_reinforcedtank2_grass_top': 'only tufts of grass standing on the bunker (which has its own cap): snow on blades would be shards',
    'mil_blastcover2_grass': 'only tufts of grass standing on the blast cover (which has its own cap): snow on blades would be shards',
    'patient_monitor': 'a medical monitor that stands in hospital rooms: no snow reaches it',
}

def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)

class Model:
    pass

def slope_w(cls, variant, ny, kind=None):
    if kind == 'slick':
        ny0, ny1 = 0.68, 0.80
    elif kind == 'rough':
        # a loose heap: its steep sides (the flanks of bags, boards and boxes) shed the snow from about 50 degrees
        ny0, ny1 = 0.63, 0.75
    elif cls == 'rock':
        # rough stone holds snow on steeper faces than a smooth roof as the cover grows
        ny1 = 0.86 - 0.022 * (variant - 1)
        ny0 = ny1 - 0.1
    elif cls == 'wall':
        ny0, ny1 = 0.6, 0.72
    else:
        # the same faces in every variant (up to about 55 degrees): light snow is a dusting through its patchy
        # texture, so a slope near the limit does not break up into tongues in one variant only. (A limit of 53
        # degrees cuts the lower part of mansard roofs into tongues; a thin even layer reads better there.)
        ny0, ny1 = 0.55, 0.66
    return smoothstep((ny - ny0) / (ny1 - ny0))

def slope_factor(ny):
    # thinner on steep faces: a 50 degree roof holds a thin layer, a flat one the full depth
    return np.clip(0.3 + (ny - 0.6) / (0.9 - 0.6) * 0.7, 0.3, 1.0)

def shifted(A, di, dj, fill):
    out = np.full_like(A, fill)
    nv, nu = A.shape
    ys = slice(max(0, dj), nv + min(0, dj))
    yd = slice(max(0, -dj), nv + min(0, -dj))
    xs = slice(max(0, di), nu + min(0, di))
    xd = slice(max(0, -di), nu + min(0, -di))
    out[yd, xd] = A[ys, xs]
    return out

def closing(Z, valid, r):
    """the surface with its narrow hollows filled (grooves of corrugated sheet, the gap between tiles, a valley
    gutter): the snow bridges what is narrower than about 2 r cells"""
    if r < 1:
        return np.where(valid, Z, np.nan)
    offs = [(di, dj) for di in range(-r, r + 1) for dj in range(-r, r + 1) if di * di + dj * dj <= r * r + r]
    A = np.where(valid, Z, -np.inf)
    D = A.copy()
    for di, dj in offs:
        D = np.maximum(D, shifted(A, di, dj, -np.inf))
    E = np.where(valid, D, np.inf)
    O = E.copy()
    for di, dj in offs:
        O = np.minimum(O, shifted(E, di, dj, np.inf))
    return np.where(valid, np.maximum(O, Z), np.nan)

def mend(Z, N, g, stairs=True):
    """slits of one sample: the reader leaves out triangles under 2.5 cm wide (rods, wires), and so a sliver in a roof
    or the joint between two panels; there the grid finds nothing, falls through to a beam below or into the joint.
    Where both neighbours across (left and right, or front and back) lie on one surface the slit takes their height:
    otherwise light snow shows a dotted line of pits along every joint"""
    thr = 2.0 * (1.8 * g + 0.02)
    Zf, Nf = Z.copy(), N.copy()
    with np.errstate(invalid='ignore'):
        for di, dj in ((1, 0), (0, 1)):
            a = shifted(Z, di, dj, np.nan)
            b = shifted(Z, -di, -dj, np.nan)
            ok = ~np.isnan(a) & ~np.isnan(b) & (np.abs(a - b) <= thr)
            mid = 0.5 * (a + b)
            # (the last sample of a stair tread lies level with the tread below a riser that goes on as the next
            # tread: no joint. Lifted to the middle it put a false step halfway up every riser. Beside a narrow
            # seam or batten (the higher side drops again right after) the lift stays: it rounds the seam)
            if stairs and os.environ.get('SZ_OLDMEND') is None:
                a2 = shifted(Z, 2 * di, 2 * dj, np.nan)
                b2 = shifted(Z, -2 * di, -2 * dj, np.nan)
                hi_goes_on = np.where(a > b, np.abs(a2 - a) < 0.025, np.abs(b2 - b) < 0.025)
                # a stair: the tread is level and the higher side never comes back down to it within 40 cm (a rib,
                # a batten or the overlap of two roof panels does; there the lift rounds it)
                back = np.zeros(Z.shape, dtype=bool)
                nxt = np.zeros(Z.shape, dtype=bool)
                prev_lo = np.where(a > b, b, a)
                for k in range(2, max(3, int(round(0.4 / g)) + 2)):
                    ak = shifted(Z, k * di, k * dj, np.nan)
                    bk = shifted(Z, -k * di, -k * dj, np.nan)
                    back |= np.where(a > b, np.abs(ak - Z) < 0.025, np.abs(bk - Z) < 0.025)
                    # the tread below ends in the next riser: an abrupt drop on the low side within 40 cm (the
                    # curved shoulder of a tank or a dome falls away gradually and is no stair)
                    lk = np.where(a > b, bk, ak)
                    nxt |= (prev_lo - lk > 0.05) & (np.abs(prev_lo - Z) < 0.025)
                    prev_lo = np.where(np.isnan(lk), prev_lo, lk)
                step = ((np.abs(a - b) > 0.05) & hi_goes_on & ~back & (N >= 0.95)
                        & (np.abs(Z - np.minimum(a, b)) < 0.025) & nxt)
                hole = ok & (np.isnan(Zf) | ((Zf < mid - 0.025) & ~step))
            else:
                hole = ok & (np.isnan(Zf) | (Zf < mid - 0.025))
            Zf = np.where(hole, mid, Zf)
            Nf = np.where(hole, 0.5 * (shifted(N, di, dj, 0.0) + shifted(N, -di, -dj, 0.0)), Nf)
    return Zf, Nf

def box_mean(A, valid, r):
    """(see slope_wide)"""
    return _box_mean(A, valid, r)

def bridge(Z, N, g, width):
    """gaps between boards, planks and slabs up to width metres wide (the slot between two planks of a well lid, the
    joint between two slabs): snow bridges them. A run of samples that finds nothing or something lower than both
    sides, between two sides at about one height, takes the height of the line between the sides. One sample wide
    is mend's job; this takes runs of two and more"""
    m = max(2, int(round(width / g)))
    thr = 2.0 * (1.8 * g + 0.02)
    Zf, Nf = Z.copy(), N.copy()
    with np.errstate(invalid='ignore'):
        for di, dj in ((1, 0), (0, 1)):
            for k in range(1, m + 1):
                for l in range(1, m + 2 - k):
                    if k + l - 1 < 2:
                        continue
                    a = shifted(Z, k * di, k * dj, np.nan)
                    b = shifted(Z, -l * di, -l * dj, np.nan)
                    ok = ~np.isnan(a) & ~np.isnan(b) & (np.abs(a - b) <= thr)
                    lo = np.minimum(a, b) - 0.025
                    low = np.isnan(Z) | (Z < lo)
                    for q in range(1, k):
                        s = shifted(Z, q * di, q * dj, np.nan)
                        low &= np.isnan(s) | (s < lo)
                    for q in range(1, l):
                        s = shifted(Z, -q * di, -q * dj, np.nan)
                        low &= np.isnan(s) | (s < lo)
                    fillm = ok & low & (np.isnan(Zf) | (Zf < lo))
                    y = a + (b - a) * (k / float(k + l))
                    Zf = np.where(fillm, y, Zf)
                    Nf = np.where(fillm, 0.5 * (shifted(N, k * di, k * dj, 0.0) + shifted(N, -l * di, -l * dj, 0.0)), Nf)
    return Zf, Nf

def _box_mean(A, valid, r):
    """the mean of A over the valid samples of a square of 2 r + 1 samples (summed areas)"""
    W = valid.astype(np.float64)
    S = np.where(valid, A, 0.0)
    def box(X):
        P = np.pad(X, ((r + 1, r), (r + 1, r)))
        C = P.cumsum(0).cumsum(1)
        return C[2 * r + 1:, 2 * r + 1:] - C[:-2 * r - 1, 2 * r + 1:] - C[2 * r + 1:, :-2 * r - 1] + C[:-2 * r - 1, :-2 * r - 1]
    n = box(W)
    return np.where(n > 0, box(S) / np.maximum(n, 1e-9), np.nan)

def slope_wide(Z, g, radius):
    """normal y of the surface Z (nan where none) averaged over a square of about 2 radius"""
    valid = ~np.isnan(Z)
    r = max(1, int(round(radius / g)))
    M = box_mean(Z, valid, r)
    with np.errstate(invalid='ignore'):
        gx = (shifted(M, -1, 0, np.nan) - shifted(M, 1, 0, np.nan)) / (2 * g)
        gz = (shifted(M, 0, -1, np.nan) - shifted(M, 0, 1, np.nan)) / (2 * g)
    gx = np.nan_to_num(gx)
    gz = np.nan_to_num(gz)
    return 1.0 / np.sqrt(1.0 + gx ** 2 + gz ** 2)

class Top:
    """the top of one model on a grid"""
    def __init__(self, V, T, ground, step, pad=2, thin_rise=0.06, skip_vertical=False, stairs=True):
        self.V, self.T = V, T
        mn = V.min(0)
        mx = V.max(0)
        self.g = step
        self.u0 = math.floor(mn[0] / step) * step - pad * step
        self.v0 = math.floor(mn[2] / step) * step - pad * step
        self.nu = int(math.ceil((mx[0] - self.u0) / step)) + pad + 1
        self.nv = int(math.ceil((mx[2] - self.v0) / step)) + pad + 1
        Z, N = VH.zbuffer(V, T, self.u0, self.v0, step, self.nu, self.nv, thin_rise, skip_vertical)
        G = getattr(VH.zbuffer, 'glass', None)
        self.glass = G if G is not None else np.zeros(Z.shape, dtype=bool)
        # the terrain cover handles what lies just over the ground (porches, slabs, foundations)
        Z[Z < ground + 0.25] = np.nan
        Z, N = mend(Z, N, step, stairs)
        # (ordinary models: fences and walls keep the gaps between their pickets and boards, heaps their holes)
        if stairs and 'bridge2' not in OFF:
            Z, N = bridge(Z, N, step, float(os.environ.get('SZ_BRIDGEW', '0.10')))
        self.Z = Z
        self.NY = N
        self.valid = ~np.isnan(Z)
        # triangles by cell of half a metre, for exact queries
        self.cell = 0.5
        A, Bv, C = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
        self.A, self.B, self.C = A, Bv, C
        xs = np.stack([A[:, 0], Bv[:, 0], C[:, 0]], 1)
        zs = np.stack([A[:, 2], Bv[:, 2], C[:, 2]], 1)
        self.buckets = collections.defaultdict(list)
        ci0 = np.floor(xs.min(1) / self.cell).astype(int)
        ci1 = np.floor(xs.max(1) / self.cell).astype(int)
        cj0 = np.floor(zs.min(1) / self.cell).astype(int)
        cj1 = np.floor(zs.max(1) / self.cell).astype(int)
        for t in range(len(T)):
            if (ci1[t] - ci0[t] + 1) * (cj1[t] - cj0[t] + 1) > 4000:
                continue
            for ci in range(ci0[t], ci1[t] + 1):
                for cj in range(cj0[t], cj1[t] + 1):
                    self.buckets[(ci, cj)].append(t)
        self.bk = {k: np.array(v) for k, v in self.buckets.items()}
        self.ground = ground

    def query(self, x, z):
        ts = self.bk.get((int(math.floor(x / self.cell)), int(math.floor(z / self.cell))))
        if ts is None:
            return float('nan')
        a, b, c = self.A[ts], self.B[ts], self.C[ts]
        d = (b[:, 2] - c[:, 2]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 2] - c[:, 2])
        ok = np.abs(d) > 1e-12
        d = np.where(ok, d, 1.0)
        l1 = ((b[:, 2] - c[:, 2]) * (x - c[:, 0]) + (c[:, 0] - b[:, 0]) * (z - c[:, 2])) / d
        l2 = ((c[:, 2] - a[:, 2]) * (x - c[:, 0]) + (a[:, 0] - c[:, 0]) * (z - c[:, 2])) / d
        l3 = 1.0 - l1 - l2
        m = ok & (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
        if not m.any():
            return float('nan')
        y = (l1 * a[:, 1] + l2 * b[:, 1] + l3 * c[:, 1])[m].max()
        if y < self.ground + 0.25:
            return float('nan')
        return float(y)

class Blanket:
    def __init__(self, top, cls, rough=False, kind=None):
        self.top = top
        self.cls = cls
        # 'slick' (canvas, foil, a dam face) or 'rough' (a heap): their own slope limit
        self.kind = kind if kind else ('rough' if rough and 'roughslope' not in OFF else None)
        # a heap, sandbags, a net: thins out like a rock, but the snow bridges the gaps between its parts
        self.rough = rough
        Z = top.Z
        g = top.g
        self.g = g
        self.nv, self.nu = Z.shape
        self.valid = top.valid
        thr = 1.8 * g + 0.02
        # canvas: the folds and pillows of a sheet are one surface (cut at every fold, the snow line along a quilted
        # tent wall ended in a rounded edge at each pillow: a row of hanging teeth)
        if self.kind == 'slick' and 'slicklink' not in OFF:
            thr = max(thr, 0.3)
        Zn = np.where(self.valid, Z, -1e6)
        self.Zn = Zn
        self.lx = self.valid[:, 1:] & self.valid[:, :-1] & (np.abs(Zn[:, 1:] - Zn[:, :-1]) <= thr)
        self.lz = self.valid[1:, :] & self.valid[:-1, :] & (np.abs(Zn[1:, :] - Zn[:-1, :]) <= thr)
        # a step between two level surfaces (a deck and the rim beside it, a ledge) is no slope: the snow ends at
        # the upper one and tucks under it at the lower one. Linked, a sheet of snow stood up the step as a white
        # curtain. Two samples count as one sloping surface when the faces there are pitched enough to rise by the
        # step between them; steps under 10 cm stay linked (the snow bridges them)
        NYt = np.clip(top.NY, 0.05, 1.0)
        tan = np.sqrt(np.maximum(0.0, 1.0 - NYt ** 2)) / NYt
        small = max(0.5 * g + 0.02, 0.10)
        dx = np.abs(Zn[:, 1:] - Zn[:, :-1])
        rise = np.maximum(tan[:, 1:], tan[:, :-1]) * g
        # (not on rocks and heaps: their snow thins out into the stone, a cut there left a bare slit along a ledge)
        if 'stepcut' not in OFF and cls != 'rock' and self.kind != 'slick':
            self.lx &= (dx <= small) | (rise >= 0.6 * dx)
        dz = np.abs(Zn[1:, :] - Zn[:-1, :])
        rise = np.maximum(tan[1:, :], tan[:-1, :]) * g
        if 'stepcut' not in OFF and cls != 'rock' and self.kind != 'slick':
            self.lz &= (dz <= small) | (rise >= 0.6 * dz)
        # a sample on a tall near vertical face (the side of a fuselage, a chimney, a tank, a tall step): the grid
        # meets the face at a different height in every row, so linked it carried the snow part way up the face in
        # some rows and not in others (a row of teeth along the foot of the face and notches in the cover above).
        # It is cut loose: the snow above ends at the bend, found on the model, and the snow below tucks under it
        if 'vface' not in OFF and cls == 'any' and self.kind != 'slick':
            Zv = np.where(self.valid, Z, np.nan)
            span = np.zeros(Z.shape)
            with np.errstate(invalid='ignore'):
                for di, dj in ((1, 0), (0, 1)):
                    a = shifted(Zv, di, dj, np.nan)
                    b = shifted(Zv, -di, -dj, np.nan)
                    span = np.maximum(span, np.nan_to_num(np.abs(np.where(np.isnan(a), Zv, a) - np.where(np.isnan(b), Zv, b))))
            vface = self.valid & (top.NY < 0.45) & (span > max(0.12, 4.4 * g))
            self.lx &= ~vface[:, 1:] & ~vface[:, :-1]
            self.lz &= ~vface[1:, :] & ~vface[:-1, :]
        else:
            vface = np.zeros(Z.shape, dtype=bool)
        self.vface = vface
        cx = np.zeros(Z.shape)
        cz = np.zeros(Z.shape)
        dx = np.zeros(Z.shape)
        dz = np.zeros(Z.shape)
        d = np.where(self.lx, Zn[:, 1:] - Zn[:, :-1], 0.0)
        dx[:, :-1] += d; cx[:, :-1] += self.lx; dx[:, 1:] += d; cx[:, 1:] += self.lx
        d = np.where(self.lz, Zn[1:, :] - Zn[:-1, :], 0.0)
        dz[:-1, :] += d; cz[:-1, :] += self.lz; dz[1:, :] += d; cz[1:, :] += self.lz
        self.gx = np.where(cx > 0, dx / np.maximum(cx, 1) / g, 0.0)
        self.gz = np.where(cz > 0, dz / np.maximum(cz, 1) / g, 0.0)
        if cls == 'wall':
            self.lone = (cx == 0) & (cz == 0)
        else:
            self.lone = (cx == 0) | (cz == 0)
            # a level strip one sample wide that runs on along the other direction (the top of a parapet round a
            # flat roof, a kerb, a beam on a coarse grid) is a surface: it gets its strip of snow (left bare, the
            # parapets of every large flat roofed block stood out dark)
            # (straight on along the grid, level: a slanted or diagonal beam of a lattice holds no such strip. Only
            # on a grid of 6 cm and coarser: on a finer grid a strip one sample wide is a thin edge (the top of a
            # sign board, a railing), which stays bare as before)
            if 'strip' not in OFF and g >= 0.06:
                self.lone &= ~(((cx >= 2) | (cz >= 2)) & (top.NY >= 0.95))
        # the surface the snow lies on: narrow hollows filled; its large scale shape for the crest of ridges
        self.Zc_cache = {}
        self.Zc = np.minimum(self.closed(0.12 if cls == 'any' else 0.06), Z + 0.12)
        Zs = self.soften(np.where(self.valid, self.Zc, 0.0), self.valid, max(2, int(round(0.15 / g))))
        # the slope the snow feels: that of the filled and softened surface (the faces of corrugated sheet, tiles and
        # dents do not count, a roof plane does)
        sx = np.zeros(Z.shape)
        sz = np.zeros(Z.shape)
        d = np.where(self.lx, Zs[:, 1:] - Zs[:, :-1], 0.0)
        sx[:, :-1] += d; sx[:, 1:] += d
        d = np.where(self.lz, Zs[1:, :] - Zs[:-1, :], 0.0)
        sz[:-1, :] += d; sz[1:, :] += d
        sgx = np.where(cx > 0, sx / np.maximum(cx, 1) / g, 0.0)
        sgz = np.where(cz > 0, sz / np.maximum(cz, 1) / g, 0.0)
        self.ny = 1.0 / np.sqrt(1.0 + sgx ** 2 + sgz ** 2)
        if self.kind == 'slick' and 'slickwide' not in OFF:
            # crumpled canvas, quilted tent skins and nets: the snow line follows the shape of the whole sheet, not
            # its creases, pockets and quilting (each pillow of a quilted tent wall has a flatter top: the line ran
            # as a row of teeth along them, and a pocket in a steep net wall held a loose blob). The slope is that
            # of the surface averaged over about a metre (all samples, linked or not)
            wide = slope_wide(np.where(self.valid, Z, np.nan), g, float(os.environ.get('SZ_SLICKR', '0.5')))
            self.ny = wide if os.environ.get('SZ_WIDEONLY', '1') == '1' else np.minimum(self.ny, wide)
        Zn = np.where(self.valid, Zs, -1e6)
        conv = np.zeros(Z.shape)
        both = self.lx[:, :-1] & self.lx[:, 1:]
        c = np.where(both, 2 * Zn[:, 1:-1] - Zn[:, :-2] - Zn[:, 2:], 0.0)
        conv[:, 1:-1] = np.maximum(conv[:, 1:-1], c)
        both = self.lz[:-1, :] & self.lz[1:, :]
        c = np.where(both, 2 * Zn[1:-1, :] - Zn[:-2, :] - Zn[2:, :], 0.0)
        conv[1:-1, :] = np.maximum(conv[1:-1, :], c)
        self.conv = self.soften(np.maximum(conv, 0.0), self.valid, 1) * (g / 0.05)
        # the highest joined surface around each sample: board edges, nail rows and tile lips rise a few centimetres
        # between the samples; the snow must clear them, not only the samples themselves
        Zr = np.where(self.valid, Z, -1e6)
        Zd = Zr.copy()
        Zd[:, :-1] = np.where(self.lx, np.maximum(Zd[:, :-1], Zr[:, 1:]), Zd[:, :-1])
        Zd[:, 1:] = np.where(self.lx, np.maximum(Zd[:, 1:], Zr[:, :-1]), Zd[:, 1:])
        Zd2 = Zd.copy()
        Zd2[:-1, :] = np.where(self.lz, np.maximum(Zd2[:-1, :], Zd[1:, :]), Zd2[:-1, :])
        Zd2[1:, :] = np.where(self.lz, np.maximum(Zd2[1:, :], Zd[:-1, :]), Zd2[1:, :])
        # a few centimetres: a neighbour much higher is the face of a wall rising beside a ledge, not a board edge
        self.Zd = np.where(self.valid, np.minimum(Zd2, Z + 0.04), 0.0)
        self.refined = {}
        self.extra_soft = set()
        self.flat_samples = set()

    def closed(self, radius):
        r = int(round(radius / self.g))
        if r not in self.Zc_cache:
            self.Zc_cache[r] = closing(self.top.Z, self.valid, r)
        return self.Zc_cache[r]

    def soften(self, A, mask, passes, lx=None, lz=None):
        lx = self.lx if lx is None else lx
        lz = self.lz if lz is None else lz
        A = np.where(mask, A, 0.0)
        for _ in range(passes):
            tot = A * 2.0 * mask
            cnt = mask * 2.0
            m = lx & mask[:, 1:] & mask[:, :-1]
            tot[:, :-1] += np.where(m, A[:, 1:], 0.0); cnt[:, :-1] += m
            tot[:, 1:] += np.where(m, A[:, :-1], 0.0); cnt[:, 1:] += m
            m = lz & mask[1:, :] & mask[:-1, :]
            tot[:-1, :] += np.where(m, A[1:, :], 0.0); cnt[:-1, :] += m
            tot[1:, :] += np.where(m, A[:-1, :], 0.0); cnt[1:, :] += m
            A = np.where(cnt > 0, tot / np.maximum(cnt, 1e-9), A)
        return A

    def edge_slope(self, i, j, du, dv):
        """the slope of the surface towards (du, dv) at a sample, from the sample behind it: the gradient through both
        neighbours took in the face below an edge and carried the snow down it at every step of a slanted edge"""
        a, b = i - du, j - dv
        if not (0 <= a < self.nu and 0 <= b < self.nv) or not self.valid[b, a] or not self.linked(i, j, a, b):
            return 0.0
        d = self.top.Z[j, i] - self.top.Z[b, a]
        if abs(d) > 0.7 * self.g + 0.01:
            return 0.0
        return float(np.clip(d / self.g, -1.5, 1.5))

    def linked(self, i, j, a, b):
        if b == j:
            return bool(self.lx[j, min(i, a)])
        return bool(self.lz[min(j, b), i])

    def neighbours(self, i, j):
        if i + 1 < self.nu and self.lx[j, i]:
            yield i + 1, j
        if i > 0 and self.lx[j, i - 1]:
            yield i - 1, j
        if j + 1 < self.nv and self.lz[j, i]:
            yield i, j + 1
        if j > 0 and self.lz[j - 1, i]:
            yield i, j - 1

    def field(self, variant, thick, min_area, rock):
        # heaps and mounds: the same faces in every depth, like a roof (the growing rock rule left light snow as a ring
        # of torn wedges on the earth mound of a tank)
        w = slope_w('any' if self.rough else self.cls, variant, self.ny, self.kind)
        w = np.where(self.valid & ~self.lone, w, 0.0)
        # one plane, one cover: a roof pitched near the slope limit (about 53 degrees) is all covered or all bare.
        # The felt slope differs by a hair from sample to sample there and the cover broke up in steps and tabs
        # across the plane. The cover is averaged over each plane (samples linked on faces of the same pitch)
        if not rock:
            NY = self.top.NY
            px = self.lx & (np.abs(NY[:, 1:] - NY[:, :-1]) < 0.02)
            pz = self.lz & (np.abs(NY[1:, :] - NY[:-1, :]) < 0.02)
            near = self.valid & ~self.lone & (w > 0.05) & (w < 0.95)
            pr = float(os.environ.get('SZ_PLANER', '1.5'))
            ws = self.soften(w, self.valid & ~self.lone, int(min(500, max(4, (pr / self.g) ** 2))), px, pz)
            w = np.where(near, ws, w)
            # and over each whole plane (a roof plane of one pitch, its samples linked on faces within 0.02 of the
            # same slope and the plane within 0.05 overall): the local average reached about a metre, so a large
            # plane right at the limit kept ragged patches of snow here and there
            if 'planemean' not in OFF and self.kind != 'slick':
                mask = self.valid & ~self.lone
                lab = np.full(w.shape, -1, dtype=np.int64)
                cur = 0
                for j0, i0 in zip(*np.nonzero(mask & (w > 0.02) & (w < 0.98))):
                    if lab[j0, i0] >= 0:
                        continue
                    comp = [(i0, j0)]
                    lab[j0, i0] = cur
                    q = 0
                    while q < len(comp):
                        i, j = comp[q]
                        q += 1
                        for a, b, ok in ((i + 1, j, i + 1 < self.nu and px[j, i]), (i - 1, j, i > 0 and px[j, i - 1]),
                                         (i, j + 1, j + 1 < self.nv and pz[j, i]), (i, j - 1, j > 0 and pz[j - 1, i])):
                            if ok and mask[b, a] and lab[b, a] < 0:
                                lab[b, a] = cur
                                comp.append((a, b))
                    cur += 1
                    if len(comp) * self.g * self.g < 1.0:
                        continue
                    ii = np.array(comp)
                    nys = NY[ii[:, 1], ii[:, 0]]
                    if nys.max() - nys.min() > 0.05:
                        continue
                    w[ii[:, 1], ii[:, 0]] = float(w[ii[:, 1], ii[:, 0]].mean())
        # a face falling away below an edge (the chamfer of a ledge, a wall under an eave) does not thin the snow at
        # the edge: the snow ends there with its full depth and a rounded edge
        # (canvas and nets: the snow line across the sheet is always a soft end, thinned out; with a rounded edge
        # at every fold of a quilted wall it hung as a row of teeth)
        if rock or self.kind == 'slick':
            w = self.soften(w, self.valid, 3)
        else:
            Zn = self.Zn
            dg = 0.7 * self.g + 0.01
            dx = Zn[:, 1:] - Zn[:, :-1]
            dz = Zn[1:, :] - Zn[:-1, :]
            fx = self.lx & (((dx > dg) & (w[:, :-1] < EDGE)) | ((dx < -dg) & (w[:, 1:] < EDGE)))
            fz = self.lz & (((dz > dg) & (w[:-1, :] < EDGE)) | ((dz < -dg) & (w[1:, :] < EDGE)))
            w = self.soften(w, self.valid, 3, self.lx & ~fx, self.lz & ~fz)
        # a face past the slope limit holds nothing, also where the softening above carried some cover onto it from
        # the flatter plane beside it (ragged patches along the foot of a steep mansard or hip). Only where the face
        # itself is that steep: the level tread of a stair feels the slope of the whole stair
        if self.cls == 'any' and not rock and self.kind is None and 'hardlimit' not in OFF:
            w = np.where((self.ny < 0.6) & (self.top.NY < 0.58), 0.0, w)
        # pitched glass sheds its snow (the slanted window band of a control tower, skylights); level glass keeps it
        if 'glass' not in OFF:
            w = np.where(self.top.glass & (self.top.NY < 0.8), 0.0, w)
        inside = self.valid & (w > EDGE)
        by_slope = inside.copy()
        # strips narrower than a hand (a band along a rock ledge, the edge of a beam) hold no snow that reads as such:
        # an opening of the mask removes them
        ro = int(round((0.06 if self.rough else (0.10 if rock else (0.03 if self.cls == 'any' else 0.0))) / self.g))
        if ro >= 1:
            offs = [(di, dj) for di in range(-ro, ro + 1) for dj in range(-ro, ro + 1) if di * di + dj * dj <= ro * ro + ro]
            er = inside.copy()
            for di, dj in offs:
                er &= shifted(inside, di, dj, False)
            op = er.copy()
            for di, dj in offs:
                op |= shifted(er, di, dj, False)
            inside &= op
        # tongues one sample wide running down a steep face (the chamfer of a ledge, a curved eave): the grid steps
        # across the face and they hang as a row of teeth. Flat tops keep every sample (a picket is one or two wide)
        if not rock:
            steep = inside & (self.ny < 0.8)
            if steep.any() and not os.environ.get('SZ_NORISE'):
                er = inside.copy()
                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    er &= shifted(inside, di, dj, False)
                op = er.copy()
                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    op |= shifted(er, di, dj, False)
                inside &= ~steep | op
        # a heap or mound: the snow bridges a narrow steeper band between two covered faces (the crease where the
        # dome of a bunker meets its berm, a ledge in a rubble heap). Left bare it showed as a row of slits or a
        # strip of snow cut off by a dark line. Bridged samples get the full cover, else the snow lay on the surface
        # there and the slit stayed
        if self.rough and 'bridge' not in OFF:
            rb = max(1, int(round(0.12 / self.g)))
            offs = [(di, dj) for di in range(-rb, rb + 1) for dj in range(-rb, rb + 1) if di * di + dj * dj <= rb * rb + rb]
            dl = inside.copy()
            for di, dj in offs:
                dl |= shifted(inside, di, dj, False)
            cl = dl.copy()
            for di, dj in offs:
                cl &= shifted(dl, di, dj, True)
            add = cl & ~inside & self.valid & ~self.lone & (self.ny >= 0.4)
            inside |= add
            w = np.where(add, np.maximum(w, FULL), w)
        # canvas and nets: the snow line runs smooth along the sheet. Tongues and notches narrower than about half
        # a metre (each pillow of a quilted wall, each pocket of a net) are taken off and filled in
        if self.kind == 'slick' and 'slickopen' not in OFF:
            ro = max(1, int(round(float(os.environ.get('SZ_SLICKOPEN', '0.5')) / self.g)))
            offs = [(di, dj) for di in range(-ro, ro + 1) for dj in range(-ro, ro + 1) if di * di + dj * dj <= ro * ro + ro]
            er = inside.copy()
            for di, dj in offs:
                er &= shifted(inside, di, dj, False)
            op = er.copy()
            for di, dj in offs:
                op |= shifted(er, di, dj, False)
            dl = op.copy()
            for di, dj in offs:
                dl |= shifted(op, di, dj, False)
            cl = dl.copy()
            for di, dj in offs:
                cl &= shifted(dl, di, dj, True)
            add = cl & ~op & self.valid & ~self.lone & (w > 0.02)
            inside = op | add
            w = np.where(add, np.maximum(w, EDGE + 0.05), w)
        # islands too small to hold snow
        lab = np.zeros(inside.shape, dtype=np.int32)
        cur = 0
        js, is_ = np.nonzero(inside)
        g2 = self.g * self.g
        for j0, i0 in zip(js, is_):
            if lab[j0, i0]:
                continue
            cur += 1
            comp = [(i0, j0)]
            lab[j0, i0] = cur
            q = 0
            while q < len(comp):
                i, j = comp[q]
                q += 1
                for a, b in self.neighbours(i, j):
                    if inside[b, a] and not lab[b, a]:
                        lab[b, a] = cur
                        comp.append((a, b))
            if len(comp) * g2 < min_area:
                for i, j in comp:
                    inside[j, i] = False
        # small holes in a cover (a roof pitched right at the slope limit, where the ribs of the sheet tip a few
        # samples over it: rows of diamond shaped holes). Snow bridges a hole under a quarter square metre that it
        # surrounds on one surface, unless the hole is a near vertical face
        if not rock or self.rough:
            hole = self.valid & ~inside & (self.ny >= 0.45)
            hl = np.zeros(inside.shape, dtype=np.int32)
            cur = 0
            for j0, i0 in zip(*np.nonzero(hole)):
                if hl[j0, i0]:
                    continue
                cur += 1
                comp = [(i0, j0)]
                hl[j0, i0] = cur
                closed = True
                q = 0
                while q < len(comp) and len(comp) * g2 < 0.25:
                    i, j = comp[q]
                    q += 1
                    n = 0
                    for a, b in self.neighbours(i, j):
                        n += 1
                        if hole[b, a] and not hl[b, a]:
                            hl[b, a] = cur
                            comp.append((a, b))
                        elif not hole[b, a] and not inside[b, a]:
                            closed = False
                    if n < 4:
                        closed = False
                if closed and len(comp) * g2 < 0.25 and q >= len(comp):
                    for i, j in comp:
                        inside[j, i] = True
                        # with the full cover: at the depth of the slope rule (nothing) it lay on the surface
                        if 'holew' not in OFF:
                            w[j, i] = max(w[j, i], FULL)
        # flat samples left out only for their size (the narrow top of a corbel under a ledge, a small step): the
        # snow next to them ends with its rounded edge, as where a surface ends. Thinned out towards them like towards
        # a too steep face it sank into a V notch at every corbel
        cut = by_slope & ~inside & (self.ny >= 0.8) if not rock else np.zeros_like(inside)
        # distance in from the soft edges (rocks: every edge) for the thinning out
        dist = np.full(inside.shape, 1e9)
        dq = collections.deque()
        js, is_ = np.nonzero(inside)
        for j, i in zip(js, is_):
            edge = False
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a, b = i + di, j + dj
                if not (0 <= a < self.nu and 0 <= b < self.nv):
                    edge = edge or rock
                    continue
                if inside[b, a]:
                    if rock and not self.linked(i, j, a, b):
                        edge = True
                    continue
                # a neighbour on the face falling away below the edge is no soft end: the snow keeps its depth up to
                # the bend (else it thinned at every step of a slanted ledge edge and the rim dipped there)
                if rock or (self.linked(i, j, a, b) and not cut[b, a]
                            and self.top.Z[j, i] - self.top.Z[b, a] <= 0.7 * self.g + 0.01):
                    edge = True
            if (i, j) in self.extra_soft:
                edge = True
            if edge:
                dist[j, i] = 0.5 * self.g
                dq.append((i, j))
        while dq:
            i, j = dq.popleft()
            for a, b in self.neighbours(i, j):
                if inside[b, a] and dist[b, a] > dist[j, i] + self.g + 1e-9:
                    dist[b, a] = dist[j, i] + self.g
                    dq.append((a, b))
        # (canvas: the snow thins out over a longer way down the sheet, as on a rock; ending within 35 cm the filled
        # folds of a quilted wall stood at its end as a fringed wall)
        taper = max(0.12, (3.0 if (rock or self.kind == 'slick') else 1.5) * thick)
        f = smoothstep((w - EDGE) / (FULL - EDGE)) * smoothstep(np.minimum(dist, 1e6) / taper)
        T = thick * f * (slope_factor(self.ny) if not rock else 1.0)
        # a narrow strip (the top edge of a sign board, a rail, a beam) holds no more snow than about one and a half
        # times its width: at the full depth it stood on it as a round sausage
        if self.cls == 'any' and not rock and 'narrow' not in OFF:
            da = np.full(inside.shape, 1e9)
            dq = collections.deque()
            for j, i in zip(*np.nonzero(inside)):
                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    a, b = i + di, j + dj
                    if not (0 <= a < self.nu and 0 <= b < self.nv) or not inside[b, a] or not self.linked(i, j, a, b):
                        da[j, i] = 0.5 * self.g
                        dq.append((i, j))
                        break
            while dq:
                i, j = dq.popleft()
                for a, b in self.neighbours(i, j):
                    if inside[b, a] and da[b, a] > da[j, i] + self.g + 1e-9:
                        da[b, a] = da[j, i] + self.g
                        dq.append((a, b))
            # the widest point of the strip across: twice the largest distance in from an edge among the neighbours
            wd = da.copy()
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                wd = np.maximum(wd, np.where(inside, shifted(np.where(inside, da, 0.0), di, dj, 0.0), 0.0))
            T = np.minimum(T, np.where(inside, 1.5 * 2.0 * np.minimum(wd, 1e3) + 0.02, T))
        Zn = np.where(self.valid, self.top.Z, 0.0)
        # deeper snow bridges wider hollows and lies smoother: light snow still shows the corrugation of a sheet roof
        # and the dents of a wreck, a deep cover hides them
        if self.rough:
            rc = max(0.08, 0.9 * thick)
        elif rock:
            rc = max(0.06, 0.8 * thick)
        elif self.cls == 'wall':
            rc = 0.03
        elif self.kind == 'slick' and 'slickfill' not in OFF:
            # canvas: the snow follows the quilting and folds of the sheet (filled, the deep cover bulged out over
            # the hollows of a quilted wall and hung in lobes along its lower edge)
            rc = 0.08
        else:
            rc = max(0.08, 1.6 * thick)
        # snow fills a hollow no deeper than itself: a groove or a gap between tiles, never the drop beside a walkway
        fill = max(0.05, 0.6 * thick) if self.rough else max(0.04, thick)
        Zc = np.where(self.valid, np.minimum(self.closed(rc), self.top.Z + fill), 0.0)
        # the snow lies smooth over a radius in metres (more passes on a finer grid): 15 cm in light snow, 35 cm in
        # the deepest. Flat roofs stay flat, so their long triangles shade evenly
        if self.rough:
            radius = max(0.12, 1.2 * thick)
        elif rock:
            radius = max(0.08, 0.8 * thick)
        else:
            radius = max(0.15, 1.5 * thick)
        # (the cap keeps the run time bounded on large grids; a fine grid needs more passes for the same radius)
        passes = int(min(150 * max(1.0, (0.04 / self.g) ** 2), max(2, 1.5 * (radius / self.g) ** 2)))
        if rock:
            if self.rough:
                # a heap of loose bricks, boards and bags: the snow lies on the highest of them within a hand's
                # width (up to 15 cm above the sample), so their thin edges stay under it instead of cutting through
                # it as dark shards; larger parts still shape the cover
                rd = max(1, int(round(0.08 / self.g)))
                Zm = np.where(self.valid, self.top.Z, -np.inf)
                Zx = Zm.copy()
                for di in range(-rd, rd + 1):
                    for dj in range(-rd, rd + 1):
                        if di * di + dj * dj <= rd * rd + rd:
                            sh = shifted(Zm, di, dj, -np.inf)
                            # (a neighbour higher than an edge can be is the side of a box or cabinet standing on
                            # the heap: lifted towards it the snow rose against it in a spike)
                            if 'lifttall' not in OFF:
                                sh = np.where(sh <= Zm + 0.15, sh, -np.inf)
                            Zx = np.maximum(Zx, sh)
                Zc = np.where(self.valid, np.maximum(Zc, np.minimum(Zx, Zn + 0.15)), Zc)
            S0 = Zc + T - 0.05 * (1.0 - f) - 0.015
            S = np.where(inside, self.soften(S0, inside, passes), S0)
            # the smoothed snow stays within its depth over the stone
            S = np.where(inside, np.minimum(S, Zc + T + 0.005), S)
            if self.rough:
                # the smoothing must not sink the snow into the tops of the sandbags or bodies it lies on
                S = np.where(inside, np.maximum(S, Zn + 0.5 * T), S)
                # the edges of bricks, boards and bags between the samples: the snow clears the highest surface
                # around each sample (within its depth), else they cut through it as dark shards. Towards the thin
                # ends of the cover less so, there the heap shows through
                Zm = np.where(self.valid, self.top.Z, -np.inf)
                Zx = Zm.copy()
                cap = max(0.04, 0.8 * thick)
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        sh = shifted(Zm, di, dj, -np.inf)
                        if 'lifttall' not in OFF:
                            sh = np.where(sh <= Zm + cap, sh, -np.inf)
                        Zx = np.maximum(Zx, sh)
                Zx = np.minimum(np.where(np.isfinite(Zx), Zx, Zn), Zn + cap)
                S = np.where(inside, np.maximum(S, Zn + (Zx - Zn + 0.35 * T) * f), S)
        else:
            extra = np.clip(self.conv * 0.9, 0.0, 0.5 * thick) * f
            # the filled hollows thin out with the snow towards its soft ends: a ledge at the foot of a wall is a
            # hollow too, filled in its middle, while the snow ends on the stone at its edge (no cliff between)
            S0 = Zn + (Zc - Zn) * f + T + extra
            Ss = self.soften(S0, inside, passes)
            # smoothing lifts the low samples beside higher ones: towards a soft end (a chamfered edge, the slope
            # into a steep face) no more than the snow is thick there, else its edge drops off as a tooth
            Ss = np.minimum(Ss, S0 + f * thick)
            S = np.where(inside, np.maximum(Ss, np.maximum(Zn + 0.6 * (T + extra), self.Zd + 0.45 * (T + extra))), Zn + T * 0.5)
            # a steep face rising from a ledge (the battered foot of a wall): the softened slope there is the ledge's,
            # so the snow climbed the face in a row of teeth where the grid steps along it. Snow lies level against
            # the face instead: at the height of the flat snow beside it, the part above runs inside the face
            # (faces over 50 degrees whose face goes on rising without snow above: the foot of a wall. A roof strip
            # with snow above it, a mansard or a pitch next to a gutter, keeps its snow)
            steep = inside & (self.top.NY < 0.64)
            if steep.any():
                flat = inside & (self.top.NY >= 0.8)
                r = 3
                lo = np.where(flat, S, np.inf)
                for di in range(-r, r + 1):
                    for dj in range(-r, r + 1):
                        lo = np.minimum(lo, shifted(np.where(flat, S, np.inf), di, dj, np.inf))
                lz = np.where(flat, Zn, np.inf)
                for di in range(-r, r + 1):
                    for dj in range(-r, r + 1):
                        lz = np.minimum(lz, shifted(np.where(flat, Zn, np.inf), di, dj, np.inf))
                # only where the face rises well above the flat beside it (a low ridge tile or batten stays covered)
                rise = steep & np.isfinite(lo) & (Zn - lz > np.maximum(T, 0.15))
                # and not the side of a raised block whose flat top carries snow too: lowered, its edge pulled the
                # snow of the top down with it and bared a strip of the top
                hz = np.where(flat, Zn, -np.inf)
                hi = hz.copy()
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        hi = np.maximum(hi, shifted(hz, di, dj, -np.inf))
                rise &= ~(hi > Zn + 0.03)
                bare = self.valid & ~inside
                zb = np.where(bare, Zn, -np.inf)
                above = np.zeros_like(rise)
                for di in range(-2, 3):
                    for dj in range(-2, 3):
                        above |= shifted(zb, di, dj, -np.inf) > Zn + 0.05
                rise &= above
                S = np.where(rise, np.minimum(S, lo + 0.01), S)
        # a single sample sunk below all four of its neighbours (the gap between two treads or boards, a bolt hole
        # the grid fell into): snow bridges it. Left, every one showed as a small dark pit in the cover
        if 'pitfill' not in OFF:
            for _ in range(2):
                Sn = np.where(inside, S, np.nan)
                lo4 = np.full(S.shape, np.inf)
                sm4 = np.zeros(S.shape)
                n4 = np.zeros(S.shape)
                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nb = shifted(Sn, di, dj, np.nan)
                    ok = ~np.isnan(nb)
                    lo4 = np.where(ok, np.minimum(lo4, nb), lo4)
                    sm4 += np.where(ok, nb, 0.0)
                    n4 += ok
                pit = inside & (n4 == 4) & (S < lo4 - 0.015)
                S = np.where(pit, sm4 / np.maximum(n4, 1), S)
        self.cut = cut
        return w, inside, S

    def refine(self, i, j, a, b):
        """a sample on a surface that ends towards its neighbour: where between them (0-1 from it), on the model"""
        key = (i, j, a, b)
        if key in self.refined:
            return self.refined[key]
        g = self.g
        top = self.top
        x0, z0 = top.u0 + i * g, top.v0 + j * g
        x1, z1 = top.u0 + a * g, top.v0 + b * g
        zp = self.top.Z[j, i]
        zq = self.top.Z[b, a] if self.valid[b, a] else None
        sl = self.edge_slope(i, j, a - i, b - j)
        lo, hi = 0.0, 1.0
        for _ in range(6):
            mid = (lo + hi) * 0.5
            x, z = x0 + (x1 - x0) * mid, z0 + (z1 - z0) * mid
            y = top.query(x, z)
            exp = zp + sl * mid * g
            if y != y:
                same = False
            elif zq is None:
                same = abs(y - exp) < 0.06
            else:
                same = abs(y - exp) < 0.45 * abs(zq - zp)
            if same:
                lo = mid
            else:
                hi = mid
        t = min(0.98, (lo + hi) * 0.5)
        self.refined[key] = t
        return t

    def dense(self, variant, thick, overhang, min_area, rock):
        """the snow of one variant as a dense mesh: (vertices, faces); faces wound with their normal outwards"""
        # two passes: the first finds the stretches of edge that end thinned out (short or ragged, see below); the
        # second thins the snow out towards them like towards a soft end, so it does not end there in a wall of its
        # full depth
        self.extra_soft = set()
        out = self.dense_pass(variant, thick, overhang, min_area, rock)
        if out is not None and self.flat_samples and 'twopass' not in OFF:
            self.extra_soft = set(self.flat_samples)
            out = self.dense_pass(variant, thick, overhang, min_area, rock)
        return out

    def dense_pass(self, variant, thick, overhang, min_area, rock):
        self.flat_samples = set()
        w, inside, S = self.field(variant, thick, min_area, rock)
        if not inside.any():
            return None
        g, u0, v0 = self.g, self.top.u0, self.top.v0
        Zs = np.where(self.valid, self.top.Z, 0.0)
        verts = []
        vidx = {}
        vbase = {}
        vkind = {}
        def vert(key, p, kind=None, base=None):
            k = vidx.get(key)
            if k is None:
                k = len(verts)
                verts.append(p)
                vidx[key] = k
                if kind:
                    vkind[k] = kind
                if base is not None:
                    vbase[k] = base
            return k
        def corner(i, j):
            return vert(('c', i, j), (u0 + i * g, float(S[j, i]), v0 + j * g))
        def crossing(p, q):
            (i, j), (a, b) = p, q
            du, dv = a - i, b - j
            # a neighbour far below (the face under a ledge, a battered wall) ends the snow at the bend, like a surface
            # that ends: else the edge runs part way down the face at some samples and not at others (a row of teeth)
            # (not on rocks and heaps: their snow sinks into the stone towards its ends, a hard end would stand above it)
            drop = (not rock) and self.valid[b, a] and (Zs[j, i] - Zs[b, a] > 0.7 * g + 0.01 or self.cut[b, a])
            # a steep face rising beside the snow (the battered wall behind a ledge): the snow tucks under it instead
            # of climbing it to the next sample (a row of spikes up the wall where the grid steps along it)
            climb = (not rock) and CLIMB and self.valid[b, a] and not inside[b, a] and Zs[b, a] - Zs[j, i] > 0.35 * g + 0.01
            if self.linked(i, j, a, b) and not drop and not climb:
                wa, wb = w[j, i], w[b, a]
                t = min(1.0, max(0.0, (wa - EDGE) / max(1e-6, wa - wb)))
                y = S[j, i] + (S[b, a] - S[j, i]) * t
                yb = Zs[j, i] + (Zs[b, a] - Zs[j, i]) * t
                return vert(('x', i, j, a, b), (u0 + (i + du * t) * g, float(min(y, yb + 0.004)) - 0.003, v0 + (j + dv * t) * g), 'soft')
            higher = (not self.valid[b, a]) or Zs[j, i] > Zs[b, a]
            if higher:
                t = self.refine(i, j, a, b)
                kind = 'hard'
            else:
                kind = 'tuck'
                # a tuck ends where the face rising beside it reaches the snow's height (a little into it), without
                # following the slope of the sample up the face: at a fixed distance the end stood out of a steep
                # roof in a valley at one sample and sank into it at the next (a row of tabs along the valley)
                rise = Zs[b, a] - Zs[j, i] if self.valid[b, a] else 0.0
                if rise > 1e-3:
                    t = float(np.clip((S[j, i] - Zs[j, i]) / rise + 0.08, 0.15, 0.95))
                else:
                    t = 0.9
                # against a wall or under an overhang (the face rises well above the snow): the snow runs into the
                # face, found on the model. At the fixed distance the gap to the wall changed from sample to sample
                # along a slanted wall (a row of teeth along the side of a fuselage, a chimney, a dormer)
                # (not on walls and fences: their strips are a few samples wide, the fixed distance reads better)
                if ('tuckwall' not in OFF and self.cls != 'wall' and self.valid[b, a]
                        and 0.45 * rise > S[j, i] - Zs[j, i] + 0.02):
                    t = max(t, min(0.98, self.refine(i, j, a, b) + 0.1))
                return vert(('x', i, j, a, b), (u0 + (i + du * t) * g, float(S[j, i]), v0 + (j + dv * t) * g), kind,
                            float(Zs[j, i]))
            dy = self.edge_slope(i, j, du, dv) * t * g
            # the snow's own slope carries its top out to the edge: a lip or a raised rim along the edge of a lid or
            # a slab (2 cm over the last sample) tilted the last strip of the cover and the game's smoothed normals
            # drew it as a dark band with dark wedges in the corners
            dys = dy
            if 'sslope' not in OFF:
                pa, pb = i - du, j - dv
                if (0 <= pa < self.nu and 0 <= pb < self.nv and inside[pb, pa] and self.linked(i, j, pa, pb)):
                    dys = float(np.clip((S[j, i] - S[pb, pa]) / g, -1.5, 1.5)) * t * g
                    if abs(dys - dy) > 0.5 * g:
                        dys = dy
            return vert(('x', i, j, a, b), (u0 + (i + du * t) * g, float(S[j, i] + dys), v0 + (j + dv * t) * g), kind,
                        float(Zs[j, i] + dy))
        faces = []
        polys = []
        js, is_ = np.nonzero(inside)
        cells = set()
        for j, i in zip(js, is_):
            for cj in (j - 1, j):
                for ci in (i - 1, i):
                    if 0 <= ci < self.nu - 1 and 0 <= cj < self.nv - 1:
                        cells.add((ci, cj))
        for (i, j) in sorted(cells):
            cs = ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))
            link = []
            for k in range(4):
                p, q = cs[k], cs[(k + 1) % 4]
                link.append(bool(self.valid[p[1], p[0]] and self.valid[q[1], q[0]] and self.linked(p[0], p[1], q[0], q[1])))
            if all(link):
                groups = [[0, 1, 2, 3]]
            else:
                s0 = next(k for k in range(4) if not link[k])
                groups = []
                cur = []
                for n in range(4):
                    k = (s0 + 1 + n) % 4
                    cur.append(k)
                    if not link[k]:
                        groups.append(cur)
                        cur = []
                if cur:
                    groups.append(cur)
            for grp in groups:
                if not any(inside[cs[k][1], cs[k][0]] for k in grp):
                    continue
                poly = []
                for idx, k in enumerate(grp):
                    p = cs[k]
                    pin = inside[p[1], p[0]]
                    prev = cs[(k - 1) % 4]
                    nxt = cs[(k + 1) % 4]
                    # the side before the first corner is broken (also when it is the only broken side of the cell:
                    # the surface steps inside the cell and the slit gets an edge on both of its sides)
                    if idx == 0 and not link[(k - 1) % 4] and pin:
                        poly.append(crossing(p, prev))
                    if pin:
                        poly.append(corner(*p))
                    if link[k]:
                        nin = inside[nxt[1], nxt[0]]
                        if pin != nin:
                            poly.append(crossing(p, nxt) if pin else crossing(nxt, p))
                    elif pin:
                        poly.append(crossing(p, nxt))
                clean = []
                for v in poly:
                    if not clean or clean[-1] != v:
                        clean.append(v)
                if len(clean) > 1 and clean[0] == clean[-1]:
                    clean.pop()
                pieces = [clean]
                # one broken side only: the polygon runs round the cell and closes across the step between its two
                # crossings, a wall of snow standing up the step. Over a high step (a curtain) cut it at the corner
                # opposite the step instead: the snow on each side ends at the step. A low step stays bridged by a
                # short ramp of snow (cut, every cell along a slanted step left a notch: a row of teeth)
                broken = [k for k in range(4) if not link[k]]
                tall = False
                if len(broken) == 1:
                    p, q = cs[broken[0]], cs[(broken[0] + 1) % 4]
                    if self.valid[p[1], p[0]] and self.valid[q[1], q[0]]:
                        tall = abs(Zs[p[1], p[0]] - Zs[q[1], q[0]]) > SPLIT_STEP
                if 'split' not in OFF and tall and len(grp) == 4 and len(clean) >= 5:
                    vcs = [vidx.get(('c',) + cs[k]) for k in grp]
                    if all(v is not None and v in clean for v in vcs):
                        mid = clean.index(vcs[2])
                        pieces = [clean[:mid + 1], clean[mid:]]
                for piece in pieces:
                    ys = [verts[v][1] for v in piece]
                    # a cell of the top spans a few centimetres of height; more is a seam between two surfaces
                    if len(piece) >= 3 and max(ys) - min(ys) < 0.5:
                        polys.append(piece)
        V = np.array(verts, dtype=np.float64)
        self.last_kind = (len(verts), dict(vkind))
        # the end of the cover never rises above the cover beside it (more than its slope over a step allows): a
        # crossing taken towards a higher rim or the next surface stood up as a thin spike
        adj = collections.defaultdict(set)
        for poly in polys:
            for v in poly:
                adj[v].update(poly)
        lift = max(0.03, 0.6 * g)
        for v, kind in vkind.items():
            cs_ = [c for c in adj.get(v, ()) if c not in vkind]
            if not cs_:
                # a sliver of the cover without a sample of its own: the other ends around it
                cs_ = [c for c in adj.get(v, ()) if c != v]
                if not cs_:
                    continue
            hi = max(V[c][1] for c in cs_) + lift
            if V[v][1] > hi:
                d = V[v][1] - hi
                V[v][1] = hi
                if v in vbase:
                    vbase[v] -= d
            if not rock:
                lo = min(V[c][1] for c in cs_) - max(0.06, thick + 0.6 * g)
                if V[v][1] < lo and kind != 'hard':
                    V[v][1] = lo
        # the top, wound so its normal points up (x z order of the grid is clockwise seen from above in x right, z up)
        edge_use = collections.Counter()
        edge_dir = {}
        for poly in polys:
            P = V[poly]
            area = 0.0
            for k in range(len(poly)):
                a, b = P[k], P[(k + 1) % len(poly)]
                area += a[0] * b[2] - b[0] * a[2]
            if area > 0:
                poly = poly[::-1]
            for t in range(1, len(poly) - 1):
                faces.append((poly[0], poly[t], poly[t + 1]))
            for k in range(len(poly)):
                a, b = poly[k], poly[(k + 1) % len(poly)]
                if a == b:
                    continue
                e = (min(a, b), max(a, b))
                edge_use[e] += 1
                edge_dir[e] = (a, b)
        # the rounded edge along the hard ends
        self.last_nf = len(faces)
        # a single other point on the outline between two hard ends (beside a beam end, a joint) lies on the stone
        # while its neighbours carry the full snow: a V notch. It joins the edge at their height
        bn = collections.defaultdict(list)
        for e, cnt in edge_use.items():
            if cnt == 1:
                bn[e[0]].append(e[1])
                bn[e[1]].append(e[0])
        for _ in range(2):
            for k, ns in bn.items():
                if vkind.get(k) != 'hard' and len(ns) == 2 and all(vkind.get(n) == 'hard' for n in ns):
                    a, b = ns
                    y = 0.5 * (V[a][1] + V[b][1])
                    ha = V[a][1] - vbase.get(a, V[a][1] - thick)
                    hb = V[b][1] - vbase.get(b, V[b][1] - thick)
                    V[k] = (V[k][0], y, V[k][2])
                    vbase[k] = y - 0.5 * (ha + hb)
                    vkind[k] = 'hard'
        # where the snow tucks under a face rising beside it (the belly of a fuselage, a curved tank, the foot of a
        # battered wall) the grid meets the face at another height in every row: the end of the snow rose and fell
        # as a row of small teeth along the face. Smoothed along the outline: the heights by a median of three and
        # an average (the positions stay: moved, they folded the cells along the face over each other)
        if 'tucksmooth' not in OFF and self.cls != 'wall':
            tn = {k: ns for k, ns in bn.items() if vkind.get(k) == 'tuck' and len(ns) == 2}
            if tn:
                ys = {k: V[k][1] for k in bn}
                new = {}
                for k, ns in tn.items():
                    vals = sorted([ys[k]] + [ys[n] for n in ns])
                    new[k] = vals[1]
                ys.update(new)
                for _ in range(2):
                    new = {k: 0.5 * ys[k] + 0.25 * (ys[ns[0]] + ys[ns[1]]) for k, ns in tn.items()}
                    ys.update(new)
                for k, ns in tn.items():
                    # raised only: lowered, the cover's own sample beside it stood up as a small peak
                    V[k] = (V[k][0], max(V[k][1], ys[k]), V[k][2])
        hard = []
        for e, cnt in edge_use.items():
            if cnt != 1:
                continue
            a, b = edge_dir[e]
            if vkind.get(a) != 'hard' or vkind.get(b) != 'hard':
                continue
            pa, pb = V[a], V[b]
            ex, ez = pb[0] - pa[0], pb[2] - pa[2]
            ln = math.hypot(ex, ez)
            if ln < 1e-5:
                continue
            # the polygon runs with its inside on the left of a -> b (area < 0 winding): outward is to the right
            ox, oz = -ez / ln, ex / ln
            hard.append((a, b, ox, oz))
        # the hard edge follows the grid in steps where it runs at an angle: smoothed along itself (positions and
        # heights, two passes) so a slanted eave or a round lip ends in one line instead of a row of teeth
        if hard:
            nb = collections.defaultdict(set)
            for a, b, _, _ in hard:
                nb[a].add(b)
                nb[b].add(a)
            for _ in range(3):
                newp = {}
                for k, ns in nb.items():
                    if len(ns) == 2:
                        n1, n2 = tuple(ns)
                        newp[k] = 0.5 * V[k] + 0.25 * (V[n1] + V[n2])
                for k, p in newp.items():
                    if k in vbase:
                        vbase[k] += p[1] - V[k][1]
                    V[k] = p
            redo = []
            for a, b, _, _ in hard:
                pa, pb = V[a], V[b]
                ex, ez = pb[0] - pa[0], pb[2] - pa[2]
                ln = math.hypot(ex, ez)
                if ln < 1e-5:
                    continue
                redo.append((a, b, -ez / ln, ex / ln))
            hard = redo
        # rocks end by thinning out into the stone everywhere: no rounded edge (it would hang as a white band off
        # every ledge)
        if hard and not rock:
            nb = collections.defaultdict(set)
            for a, b, _, _ in hard:
                nb[a].add(b)
                nb[b].add(a)
            cap = 1.2 * thick + 0.02
            hraw = {}
            for k in nb:
                p = V[k]
                # the rounded edge reaches no deeper than the snow is thick: over a dip beside the edge it would hang
                # down as a curtain
                hraw[k] = min(max(0.008, p[1] - vbase.get(k, p[1] - thick)), cap)
            # one depth along a stretch of edge: a single sample that found its base lower (a gap, a wire, a step in
            # the model) would hang down as a tooth. A median of three along the edge, then no point deeper than its
            # neighbours allow; the open end of a stretch closes to a point
            hs = dict(hraw)
            for _ in range(2):
                new = {}
                for k, ns in nb.items():
                    vals = sorted([hs[k]] + [hs[n] for n in ns])
                    new[k] = vals[len(vals) // 2] if len(vals) >= 3 else min(vals)
                hs = new
            for _ in range(2):
                for k, ns in nb.items():
                    lim = 1.5 * min(hs[n] for n in ns) + 0.01
                    if hs[k] > lim:
                        hs[k] = lim
            # the open end of a stretch closes to a point; two open ends facing each other across a small gap (a
            # wire or a pipe coming down over the eave, a joint) keep their depth, else the edge dipped into a V there
            ends = [k for k, ns in nb.items() if len(ns) == 1]
            near_end = set()
            if 'endgap' not in OFF and len(ends) > 1:
                E = np.array([V[k] for k in ends])
                for a_i, k in enumerate(ends):
                    dd = np.hypot(E[:, 0] - E[a_i, 0], E[:, 2] - E[a_i, 2])
                    dd[a_i] = 1e9
                    b_i = int(np.argmin(dd))
                    if dd[b_i] < max(0.25, 4.0 * g) and abs(E[b_i, 1] - E[a_i, 1]) < 0.15 and ends[b_i] not in nb[k]:
                        near_end.add(k)
            for k in ends:
                if k in near_end:
                    n0 = next(iter(nb[k]))
                    hs[k] = max(hs[k], hs[n0])
                else:
                    hs[k] = max(0.006, 0.35 * hs[k])
            # short stretches and those along a ragged base (a broken wall top, wire, debris) end thinned out instead
            seen = set()
            flat = set()
            self.last_chains = []
            for s in nb:
                if s in seen:
                    continue
                seen.add(s)
                members = [s]
                q = 0
                while q < len(members):
                    for n in nb[members[q]]:
                        if n not in seen:
                            seen.add(n)
                            members.append(n)
                    q += 1
                length = 0.5 * sum(float(np.linalg.norm(V[a] - V[b])) for a in members for b in nb[a])
                rag = sum(abs(hraw[k] - hs[k]) for k in members) / len(members)
                self.last_chains.append((length, rag, len(members), float(np.mean([V[k][1] for k in members])),
                                         float(np.mean([hs[k] for k in members])), float(np.mean([V[k][0] for k in members])),
                                         float(np.mean([V[k][2] for k in members])), any(len(nb[k]) == 1 for k in members)))
                # an open stretch under a metre (the edge breaks up along a ledge or a broken top) hangs as a lobe
                # with pointed ends; a closed one (the cap of a post) keeps its rounded edge
                open_ = any(len(nb[k]) == 1 for k in members)
                if length < max(0.12, 3 * g) or (open_ and length < 1.0) or rag > 0.5 * thick + 0.015:
                    flat.update(members)
            # (kept for the review tools: which edge points end thinned out, the rim depths)
            self.last_flat = set(flat)
            self.last_hs = (dict(hs), dict(hraw), {k: tuple(V[k]) for k in nb}, {k: len(ns) for k, ns in nb.items()})
            for k in flat:
                drop = max(0.0, min(hraw[k], hs[k]) - 0.012)
                V[k] = (V[k][0], V[k][1] - drop, V[k][2])
            hard = [hd for hd in hard if hd[0] not in flat and hd[1] not in flat]
            if flat:
                for key, v in vidx.items():
                    if key[0] == 'x' and v in flat:
                        self.flat_samples.add((key[1], key[2]))
        if hard and not rock:
            vdir = collections.defaultdict(list)
            for a, b, ox, oz in hard:
                vdir[a].append((ox, oz))
                vdir[b].append((ox, oz))
            rings = {}
            Vl = [tuple(p) for p in V]
            dirs = {}
            reach = {}
            for k, ds in vdir.items():
                sx = sum(d[0] for d in ds)
                sz = sum(d[1] for d in ds)
                ln = math.hypot(sx, sz)
                if ln < 0.3:
                    ux, uz = ds[0]
                else:
                    ux, uz = sx / ln, sz / ln
                    c = max(0.75, ux * ds[0][0] + uz * ds[0][1])
                    ux, uz = ux / c, uz / c
                dirs[k] = (ux, uz)
                reach[k] = min(overhang, 0.75 * hs[k])
            # in a hollow bend of the outline the outward reaches of neighbouring points converge: the rounded edges
            # of the two would cross and fold into a pinched knot. The reach is cut back so that the outer line of the
            # rounded edge runs on in the same direction as the edge itself
            if 'ringfold' not in OFF:
                for _ in range(2):
                    for a, b, _, _ in hard:
                        pa, pb = V[a], V[b]
                        ex, ez = pb[0] - pa[0], pb[2] - pa[2]
                        L2 = ex * ex + ez * ez
                        if L2 < 1e-10:
                            continue
                        (uax, uaz), (ubx, ubz) = dirs[a], dirs[b]
                        dd = (ubx * reach[b] - uax * reach[a]) * ex + (ubz * reach[b] - uaz * reach[a]) * ez
                        if dd < -0.6 * L2:
                            s = 0.6 * L2 / -dd
                            reach[a] *= s
                            reach[b] *= s
            for k in dirs:
                ux, uz = dirs[k]
                p = V[k]
                h = hs[k]
                base = p[1] - h
                r = reach[k]
                ring = [k]
                for fr, fu in RING[1:]:
                    y = base - SKIRT if fu is None else base + h * fu
                    Vl.append((p[0] + ux * r * fr, y, p[2] + uz * r * fr))
                    ring.append(len(Vl) - 1)
                rings[k] = ring
            for a, b, ox, oz in hard:
                ra, rb = rings[a], rings[b]
                for t in range(len(ra) - 1):
                    # outward faces: a -> b runs with the outside on the right; seen from outside a-b-b'-a' is clockwise
                    faces.append((ra[t], ra[t + 1], rb[t + 1]))
                    faces.append((ra[t], rb[t + 1], rb[t]))
            V = np.array(Vl, dtype=np.float64)
        return V, faces

# ---------------- Blender: merge and thin ----------------
def lod0_budget(area, V, F):
    """triangles for the first LOD: by the area covered and by the length of the snow's open edges (the slots of a
    pallet, the boards of a stack, the ledges of a castle wall): each metre of edge needs its rounded profile. With the
    area alone a small model with many edges was cut down so far that its cover folded across the gaps"""
    import collections as _c
    eu = _c.Counter()
    for f in F:
        n = len(f)
        for k in range(n):
            a, b = f[k], f[(k + 1) % n]
            eu[(min(a, b), max(a, b))] += 1
    Va = np.asarray(V)
    edge = sum(float(np.linalg.norm(Va[a] - Va[b])) for (a, b), c in eu.items() if c == 1)
    if os.environ.get('SZ_OLDBUDGET'):
        edge = 0.0
    return int(min(12000, max(400, area * 100, edge * 60)))

def simplify(V, F, budgets):
    """merges the flat parts and thins the mesh to each budget (one mesh per LOD). A collapse first (Blender's
    decimation, fast) brings the dense grid mesh down to a few times the largest budget; merging coplanar faces on the
    full mesh would make one polygon of thousands of corners per flat roof, slow to cut back into triangles"""
    import bpy, bmesh
    me = bpy.data.meshes.new('snow')
    me.from_pydata([tuple(v) for v in V], [], [tuple(f) for f in F])
    me.validate(clean_customdata=False)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0005)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new('snow', me)
    bpy.context.scene.collection.objects.link(obj)
    meshes = [me]
    def collapse(ratio):
        mod = obj.modifiers.new('d', 'DECIMATE')
        mod.decimate_type = 'COLLAPSE'
        mod.ratio = ratio
        mod.use_collapse_triangulate = True
        dg = bpy.context.evaluated_depsgraph_get()
        m2 = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
        obj.modifiers.remove(mod)
        return m2
    pre = max(budgets[0] * 3, 6000)
    if len(me.polygons) > pre:
        obj.data = collapse(pre / len(me.polygons))
        meshes.append(obj.data)
    # (merging the flat parts into large polygons and cutting them back into triangles laid triangles across the
    # outside of concave polygons: large folds standing up from flat roofs. The decimation alone keeps the shape)
    if os.environ.get('SZ_DISSOLVE'):
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.6), use_dissolve_boundaries=False, verts=bm.verts, edges=bm.edges)
        bmesh.ops.triangulate(bm, faces=bm.faces, quad_method='BEAUTY', ngon_method='BEAUTY')
        bm.to_mesh(obj.data)
        bm.free()
    base = len(obj.data.polygons)
    out = []
    for budget in budgets:
        ratio = min(1.0, budget / max(1, base))
        m2 = collapse(ratio) if ratio < 0.999 else obj.data
        if m2 is not obj.data:
            meshes.append(m2)
        vs = np.array([v.co[:] for v in m2.vertices])
        fs = [tuple(p.vertices) for p in m2.polygons]
        out.append((vs, fs))
    bpy.data.objects.remove(obj)
    for m2 in meshes:
        if m2.users == 0:
            bpy.data.meshes.remove(m2)
    return out

def drape_budget(dr, V, F):
    """the first LOD of draped snow: the budget the drape worked out for its last cap (by area and open edge), or the
    mesh as made (up to 20000 triangles) when it was not fused"""
    b = getattr(dr, 'last_budget', None)
    if b is not None and os.environ.get('SZ_NOFUSE') is None:
        return b
    return int(min(20000, max(lod0_budget(dr.area, V, F), len(F))))

# ---------------- MLOD ----------------
def asciiz(s):
    return s.encode('ascii') + b'\x00'

def p3dm(V, F, stage, period):
    """one LOD; faces written in the engine's order (its left handed space: clockwise from the front)"""
    tex = asciiz(B.tex_path(stage)) + asciiz(B.mat_path(stage))
    out = bytearray(b'P3DM')
    tris = []
    normals = []
    for f in F:
        for t in range(1, len(f) - 1):
            a, b, c = f[0], f[t], f[t + 1]
            pa, pb, pc = V[a], V[b], V[c]
            n = np.cross(pb - pa, pc - pa)
            ln = np.linalg.norm(n)
            if ln < 1e-12:
                continue
            tris.append((a, b, c))
            normals.append(n / ln)
    out += struct.pack('<IIIIII', 0x1C, 0x100, len(V), len(tris), len(tris), 0)
    for p in V:
        out += struct.pack('<fffI', float(p[0]), float(p[1]), float(p[2]), 0)
    for n in normals:
        out += struct.pack('<fff', float(-n[0]), float(-n[1]), float(-n[2]))
    uvs = bytearray()
    for k, ((a, b, c), n) in enumerate(zip(tris, normals)):
        out += struct.pack('<I', 3)
        corners = (a, c, b)
        for i in range(4):
            if i < 3:
                p = V[corners[i]]
                if n[1] > 0.45:
                    u, v = p[0] / period, p[2] / period
                else:
                    u = (p[0] * abs(n[2]) + p[2] * abs(n[0])) / period
                    v = -p[1] / period
                out += struct.pack('<IIff', int(corners[i]), k, u, v)
                uvs += struct.pack('<ff', u, v)
            else:
                out += struct.pack('<IIff', 0, 0, 0.0, 0.0)
        out += struct.pack('<I', 0)
        out += tex
    out += b'TAGG'
    def tag(name, data):
        out.extend(b'\x01' + asciiz(name) + struct.pack('<I', len(data)) + data)
    tag('#Property#', b'lodnoshadow'.ljust(64, b'\x00') + b'1'.ljust(64, b'\x00'))
    tag('#UVSet#', struct.pack('<I', 0) + bytes(uvs))
    tag('#EndOfFile#', b'')
    return bytes(out), len(tris)

def mlod(lods):
    body = b''
    for data, res in lods:
        body += data + struct.pack('<f', res)
    return b'MLOD' + struct.pack('<II', 257, len(lods)) + body

# ---------------- per model ----------------
def model_class(m):
    n = base_name(m.shape)
    if any(n.startswith(p) for p in os.environ.get('SZ_ASWALL', '').split(',') if p):
        return 'wall'
    if BOARDS.match(n):
        return 'wall'
    if m.rock or is_rough(m):
        return 'rock'
    if m.kind == 1:
        return 'wall'
    return 'any'

def base_name(shape):
    return os.path.splitext(os.path.basename(shape.replace('\\', '/')))[0].lower()

def is_rough(m):
    n = base_name(m.shape)
    if any(n.startswith(p) for p in os.environ.get('SZ_UNROUGH', '').split(',') if p):
        return False
    return (not m.rock) and bool(ROUGH.match(n))

def thin_rise_of(m):
    """how far a thin edge may stand above the surface and still be covered: on heaps (the edges of tilted bricks,
    boards and bags) the snow covers them up to 20 cm, else they cut through it as dark shards"""
    return 0.2 if is_rough(m) else 0.06

def make_top(m, V, T, ground, step):
    """the top of a model as the generator, the review tools and the metrics all see it"""
    cls = model_class(m)
    # (stairs: walls, fences and heaps keep the old mending of joints)
    return Top(V, T, ground, step, thin_rise=thin_rise_of(m), skip_vertical=(cls == 'wall'), stairs=(cls == 'any'))

def make_blanket(m, top, cls):
    """the blanket of a model as the generator, the review tools and the metrics all see it"""
    kind = 'slick' if (SLICK.match(base_name(m.shape)) and 'slick' not in OFF) else None
    mound = bool(MOUND.match(base_name(m.shape))) and 'mound' not in OFF
    if kind == 'slick' and 'slickbars' not in OFF:
        # the frame of a tent or net (poles and bars over the canvas): narrow ridges standing on the sheet. The
        # snow lies on the canvas and the bars stand out of it; lifted onto them it rose as a row of posts along
        # every bar. An opening of the top (about 10 cm) takes them off
        r = max(1, int(round(0.1 / top.g)))
        offs = [(di, dj) for di in range(-r, r + 1) for dj in range(-r, r + 1) if di * di + dj * dj <= r * r + r]
        A = np.where(top.valid, top.Z, np.inf)
        E = A.copy()
        for di, dj in offs:
            E = np.minimum(E, shifted(A, di, dj, np.inf))
        E = np.where(top.valid & np.isfinite(E), E, -np.inf)
        O = E.copy()
        for di, dj in offs:
            O = np.maximum(O, shifted(E, di, dj, -np.inf))
        top.Z = np.where(top.valid & np.isfinite(O), np.minimum(top.Z, O), top.Z)
    bl = Blanket(top, cls, is_rough(m), kind)
    if mound:
        bl.ny = slope_wide(np.where(top.valid, top.Z, np.nan), top.g, 0.5)
    return bl

# models whose snow is draped on their own faces (snow_drape) instead of the raster cover
DRAPE = re.compile(r'^$')

def drape_for(m, path, V, T, log=None):
    """the draped snow of a model (snow_drape.Drape), or None where it keeps the raster cover. SZ_DRAPE (a regex on the
    model name) overrides the list for tests"""
    n = base_name(m.shape)
    rx = os.environ.get('SZ_DRAPE')
    if rx is not None:
        if not re.match(rx, n):
            return None
    elif not DRAPE.match(n) or 'drape' in OFF:
        return None
    import snow_drape as SD
    cls, step, min_area, kind = params(m, V)
    if cls == 'rock':
        return None
    rough = is_rough(m)
    skind = 'slick' if (SLICK.match(n) and 'slick' not in OFF) else ('rough' if rough and 'roughslope' not in OFF else None)
    return SD.Drape(V, T, ground_for(path, V), 'any' if rough else cls, skind, min_area, kind, cls, log)

def ground_of(path):
    with open(path, encoding='latin-1') as fh:
        line = fh.readline()
    g = re.search(r' ground (-?\d+)', line)
    return int(g.group(1)) / 1000.0 if g else -1e6

def params(m, V):
    """class, grid step, smallest patch kept and slab table of a model"""
    cls = model_class(m)
    size = max(np.ptp(V[:, 0]), np.ptp(V[:, 2]))
    step = min(0.15, max(float(os.environ.get('SZ_STEPMIN', '0.04')), size / 300.0))
    if FINE.match(base_name(m.shape)):
        step = min(step, 0.02)
    if cls == 'wall':
        # pickets, planks and posts are a few centimetres wide: each gets its own small cap
        step = 0.02 if size <= 10.0 else 0.03
    min_area = {'rock': 0.08, 'wall': 0.003, 'any': 0.03}[cls]
    return cls, step, min_area, (1 if cls == 'wall' else 0)

def ground_for(path, V):
    """the height under which the terrain cover takes over: the terrain under the map object the bake sampled, but
    never above the lower third of the model (a wall set into a slope, a half buried monolith)"""
    return min(ground_of(path), float(V[:, 1].min() + 0.35 * np.ptp(V[:, 1])))

def overhang_of(cls, variant, thick):
    if cls == 'any':
        return OVERHANG[variant]
    if cls == 'rock':
        return 0.0
    return B.WALL_OVERHANG * thick

def craft(path, out_dir, name):
    m = B.parse(path)
    if base_name(m.shape) in SKIP:
        return 'skip (%s)' % SKIP[base_name(m.shape)], None
    hand = craft_hand(path, out_dir, name)
    if hand is not None:
        return hand
    od = X.read_model(m.shape)
    if od is None:
        return 'nomodel', None
    lod = X.visual_lod(od)
    if lod is None:
        return 'nolod', None
    V, T = VH.triangles(lod)
    if len(T) == 0:
        return 'nofaces', None
    ground = ground_for(path, V)
    cls, step, min_area, kind = params(m, V)
    dr = drape_for(m, path, V, T)
    if dr is None:
        top = make_top(m, V, T, ground, step)
        if not top.valid.any():
            return 'notop', None
        bl = make_blanket(m, top, cls)
    elif dr.empty:
        return 'notop', None
    files = []
    stats = []
    empty = []
    for variant in VARIANTS:
        stage = VARIANTS[variant]
        thick = THICK[kind][variant]
        over = overhang_of(cls, variant, thick)
        d = bl.dense(variant, thick, over, min_area, cls == 'rock') if dr is None else dr.cap(thick, over)
        if d is None:
            # light snow can find no face flat enough where a deeper cover does: that variant draws nothing (one
            # tiny triangle inside the model, the format needs a face)
            empty.append(variant)
            c = V.mean(0)
            tri = np.array([c, c + (0.001, 0, 0), c + (0, 0, 0.001)])
            data, _ = p3dm(tri, [(0, 1, 2)], stage, B.PERIOD)
            files.append(('%s_v%d.p3d' % (name, variant), mlod([(data, 1.0)])))
            stats.append([0, 0, 0])
            continue
        Vd, Fd = d
        if dr is None:
            area = float(top.valid.sum()) * step * step
            b0 = lod0_budget(area, Vd, Fd[:getattr(bl, 'last_nf', len(Fd))])
        else:
            b0 = drape_budget(dr, Vd, Fd)
        simp = simplify(Vd, Fd, (b0, max(80, b0 // 4), max(30, b0 // 14)))
        period = B.PERIOD_OPEN if stage < 4 else B.PERIOD
        lods = []
        tri_counts = []
        for (vs, fs), res in zip(simp, LOD_RES):
            data, nt = p3dm(vs, fs, stage, period)
            lods.append((data, res))
            tri_counts.append(nt)
        files.append(('%s_v%d.p3d' % (name, variant), mlod(lods)))
        stats.append(tri_counts)
    if len(empty) == len(VARIANTS):
        return 'nosnow', None
    for fn, data in files:
        with open(os.path.join(out_dir, fn), 'wb') as fh:
            fh.write(data)
    return ('ok' if not empty else 'ok-from-v%d' % (max(empty) + 1)), stats

APPROVED = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hand', 'approved')


def approved_mesh(name):
    """the frozen, reviewed snow of a model (tools/hand/approved/<name>.npz, written by the QA approve step): {variant:
    (V, F)} in model space, or None"""
    p = os.path.join(APPROVED, name + '.npz')
    if not os.path.exists(p):
        return None
    z = np.load(p)
    return {v: (np.asarray(z['V%d' % v], np.float64), np.asarray(z['F%d' % v], np.int64)) for v in range(1, 8)}


def craft_hand(path, out_dir, name):
    """the hand-made snow of a model: its approved (frozen) meshes first, else its recipe in tools/hand (snow_hand);
    None when it has neither. SZ_HAND=all makes every model's snow by hand (its recipe, or the default)"""
    import snow_hand as H
    ap = approved_mesh(name)
    # (Opus, 7 Oct) SZ_APPROVED_ONLY=1: a test build of the reviewed caps only; a model not yet approved keeps the
    # old route instead of building its (possibly heavy) recipe inside the craft
    if ap is None and os.environ.get('SZ_APPROVED_ONLY') == '1':
        return None
    if ap is None and H.recipe(name) is None and os.environ.get('SZ_HAND') != 'all':
        return None
    hm = H.Model(name, path=path)
    files, stats, empty = [], [], []
    for variant in VARIANTS:
        stage = VARIANTS[variant]
        d = ap[variant] if ap is not None else H.build(hm, variant)
        if d is None or len(d[1]) == 0:
            empty.append(variant)
            c = hm.V.mean(0)
            tri = np.array([c, c + (0.001, 0, 0), c + (0, 0, 0.001)])
            data, _ = p3dm(tri, [(0, 1, 2)], stage, B.PERIOD)
            files.append(('%s_v%d.p3d' % (name, variant), mlod([(data, 1.0)])))
            stats.append([0, 0, 0])
            continue
        Vd = np.asarray(d[0], dtype=np.float64)
        Fd = [tuple(int(i) for i in f) for f in d[1]]
        # the first LOD as made (a hand-made cap is lean already), the farther ones thinned
        b0 = int(min(12000, max(400, len(Fd))))
        simp = simplify(Vd, Fd, (b0, max(80, b0 // 4), max(30, b0 // 14)))
        period = B.PERIOD_OPEN if stage < 4 else B.PERIOD
        lods, tri_counts = [], []
        for (vs, fs), res in zip(simp, LOD_RES):
            data, nt = p3dm(vs, fs, stage, period)
            lods.append((data, res))
            tri_counts.append(nt)
        files.append(('%s_v%d.p3d' % (name, variant), mlod(lods)))
        stats.append(tri_counts)
    if len(empty) == len(VARIANTS):
        return 'nosnow', None
    for fn, data in files:
        with open(os.path.join(out_dir, fn), 'wb') as fh:
            fh.write(data)
    return ('ok-hand' if not empty else 'ok-hand-from-v%d' % (max(empty) + 1)), stats

def main(argv):
    src, out_dir = argv[0], argv[1]
    only = set(argv[argv.index('--only') + 1].split(',')) if '--only' in argv else None
    sl = argv[argv.index('--slice') + 1] if '--slice' in argv else '0/1'
    k, n = (int(x) for x in sl.split('/'))
    log_dir = argv[argv.index('--log') + 1] if '--log' in argv else out_dir
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    used = {}
    jobs = []
    for fn in sorted(os.listdir(src)):
        if not fn.endswith('.txt'):
            continue
        with open(os.path.join(src, fn), encoding='latin-1') as fh:
            first = fh.readline().split()
        if len(first) < 2 or first[0] != 'model':
            continue
        shape = first[1]
        name = B.short_name(shape, used)
        if only is not None and name not in only:
            continue
        jobs.append((fn, shape, name))
    log = open(os.path.join(log_dir, 'craft_%d.log' % k), 'a')
    for idx, (fn, shape, name) in enumerate(jobs):
        if idx % n != k:
            continue
        t0 = time.time()
        try:
            res, stats = craft(os.path.join(src, fn), out_dir, name)
        except Exception as ex:
            import traceback
            res, stats = 'error ' + repr(ex).replace('\n', ' ')[:200], None
            traceback.print_exc()
        line = '%s\t%s\t%s\t%s\t%.1fs' % (name, shape, res, stats[3] if stats else '', time.time() - t0)
        print(line, flush=True)
        log.write(line + '\n')
        log.flush()

if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    main(argv)
