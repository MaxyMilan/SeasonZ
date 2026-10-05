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
RING = ((0.0, 1.0), (0.42, 0.97), (0.78, 0.87), (0.97, 0.68), (1.0, 0.47), (0.86, 0.26), (0.55, 0.1), (0.2, None))
SKIRT = 0.02
LOD_RES = (1.0, 2.0, 3.0)
# ragged models (heaps, sandbags, nets, rubble, mounds): their snow thins out into them like on a rock, no rounded edge
# (a cornice along every sandbag or body would hang as rows of teeth)
ROUGH = re.compile(r'^(dead_pile|dead_massgrave|garbage_pile|misc_bagfence|roadblock_bags|hbarrier|misc_pallets|'
                   r'misc_tirepile|misc_woodpile|mil_camonet|cihly|craterlong|rubble_|ruin_rubble|cemetery_grave|'
                   r'misc_haybale_decayed|mil_reinforcedtank|mil_blastcover\d_grass|mil_fortified_nest_small|'
                   r'mil_artillery_nest)')
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
}

def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)

class Model:
    pass

def slope_w(cls, variant, ny):
    if cls == 'rock':
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

def mend(Z, N, g):
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
            hole = ok & (np.isnan(Zf) | (Zf < mid - 0.025))
            Zf = np.where(hole, mid, Zf)
            Nf = np.where(hole, 0.5 * (shifted(N, di, dj, 0.0) + shifted(N, -di, -dj, 0.0)), Nf)
    return Zf, Nf

class Top:
    """the top of one model on a grid"""
    def __init__(self, V, T, ground, step, pad=2):
        self.V, self.T = V, T
        mn = V.min(0)
        mx = V.max(0)
        self.g = step
        self.u0 = math.floor(mn[0] / step) * step - pad * step
        self.v0 = math.floor(mn[2] / step) * step - pad * step
        self.nu = int(math.ceil((mx[0] - self.u0) / step)) + pad + 1
        self.nv = int(math.ceil((mx[2] - self.v0) / step)) + pad + 1
        Z, N = VH.zbuffer(V, T, self.u0, self.v0, step, self.nu, self.nv)
        # the terrain cover handles what lies just over the ground (porches, slabs, foundations)
        Z[Z < ground + 0.25] = np.nan
        Z, N = mend(Z, N, step)
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
    def __init__(self, top, cls, rough=False):
        self.top = top
        self.cls = cls
        # a heap, sandbags, a net: thins out like a rock, but the snow bridges the gaps between its parts
        self.rough = rough
        Z = top.Z
        g = top.g
        self.g = g
        self.nv, self.nu = Z.shape
        self.valid = top.valid
        thr = 1.8 * g + 0.02
        Zn = np.where(self.valid, Z, -1e6)
        self.Zn = Zn
        self.lx = self.valid[:, 1:] & self.valid[:, :-1] & (np.abs(Zn[:, 1:] - Zn[:, :-1]) <= thr)
        self.lz = self.valid[1:, :] & self.valid[:-1, :] & (np.abs(Zn[1:, :] - Zn[:-1, :]) <= thr)
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

    def closed(self, radius):
        r = int(round(radius / self.g))
        if r not in self.Zc_cache:
            self.Zc_cache[r] = closing(self.top.Z, self.valid, r)
        return self.Zc_cache[r]

    def soften(self, A, mask, passes):
        A = np.where(mask, A, 0.0)
        for _ in range(passes):
            tot = A * 2.0 * mask
            cnt = mask * 2.0
            m = self.lx & mask[:, 1:] & mask[:, :-1]
            tot[:, :-1] += np.where(m, A[:, 1:], 0.0); cnt[:, :-1] += m
            tot[:, 1:] += np.where(m, A[:, :-1], 0.0); cnt[:, 1:] += m
            m = self.lz & mask[1:, :] & mask[:-1, :]
            tot[:-1, :] += np.where(m, A[1:, :], 0.0); cnt[:-1, :] += m
            tot[1:, :] += np.where(m, A[:-1, :], 0.0); cnt[1:, :] += m
            A = np.where(cnt > 0, tot / np.maximum(cnt, 1e-9), A)
        return A

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
        w = slope_w('any' if self.rough else self.cls, variant, self.ny)
        w = np.where(self.valid & ~self.lone, w, 0.0)
        w = self.soften(w, self.valid, 3)
        inside = self.valid & (w > EDGE)
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
            if steep.any():
                er = inside.copy()
                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    er &= shifted(inside, di, dj, False)
                op = er.copy()
                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    op |= shifted(er, di, dj, False)
                inside &= ~steep | op
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
                if rock or self.linked(i, j, a, b):
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
        taper = max(0.12, (3.0 if rock else 1.5) * thick)
        f = smoothstep((w - EDGE) / (FULL - EDGE)) * smoothstep(np.minimum(dist, 1e6) / taper)
        T = thick * f * (slope_factor(self.ny) if not rock else 1.0)
        Zn = np.where(self.valid, self.top.Z, 0.0)
        # deeper snow bridges wider hollows and lies smoother: light snow still shows the corrugation of a sheet roof
        # and the dents of a wreck, a deep cover hides them
        if self.rough:
            rc = max(0.08, 0.9 * thick)
        elif rock:
            rc = max(0.06, 0.8 * thick)
        elif self.cls == 'wall':
            rc = 0.03
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
        passes = int(min(150, max(2, 1.5 * (radius / self.g) ** 2)))
        if rock:
            S0 = Zc + T - 0.05 * (1.0 - f) - 0.015
            S = np.where(inside, self.soften(S0, inside, passes), S0)
            # the smoothed snow stays within its depth over the stone
            S = np.where(inside, np.minimum(S, Zc + T + 0.005), S)
            if self.rough:
                # the smoothing must not sink the snow into the tops of the sandbags or bodies it lies on
                S = np.where(inside, np.maximum(S, Zn + 0.5 * T), S)
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
        sx, sz = self.gx[j, i], self.gz[j, i]
        lo, hi = 0.0, 1.0
        for _ in range(6):
            mid = (lo + hi) * 0.5
            x, z = x0 + (x1 - x0) * mid, z0 + (z1 - z0) * mid
            y = top.query(x, z)
            exp = zp + sx * (x - x0) + sz * (z - z0)
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
            drop = (not rock) and self.valid[b, a] and Zs[j, i] - Zs[b, a] > 0.7 * g + 0.01
            if self.linked(i, j, a, b) and not drop:
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
                t = 0.9
                kind = 'tuck'
            dy = (self.gx[j, i] * du + self.gz[j, i] * dv) * t * g
            return vert(('x', i, j, a, b), (u0 + (i + du * t) * g, float(S[j, i] + dy), v0 + (j + dv * t) * g), kind,
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
                ys = [verts[v][1] for v in clean]
                # a cell of the top spans a few centimetres of height; more is a seam between two surfaces
                if len(clean) >= 3 and max(ys) - min(ys) < 0.5:
                    polys.append(clean)
        V = np.array(verts, dtype=np.float64)
        self.last_kind = (len(verts), dict(vkind))
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
            for k, ns in nb.items():
                if len(ns) == 1:
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
                self.last_chains.append((length, rag, len(members), float(np.mean([V[k][1] for k in members])), float(np.mean([hs[k] for k in members]))))
                # an open stretch under a metre (the edge breaks up along a ledge or a broken top) hangs as a lobe
                # with pointed ends; a closed one (the cap of a post) keeps its rounded edge
                open_ = any(len(nb[k]) == 1 for k in members)
                if length < max(0.12, 3 * g) or (open_ and length < 1.0) or rag > 0.5 * thick + 0.015:
                    flat.update(members)
            for k in flat:
                drop = max(0.0, min(hraw[k], hs[k]) - 0.012)
                V[k] = (V[k][0], V[k][1] - drop, V[k][2])
            hard = [hd for hd in hard if hd[0] not in flat and hd[1] not in flat]
        if hard and not rock:
            vdir = collections.defaultdict(list)
            for a, b, ox, oz in hard:
                vdir[a].append((ox, oz))
                vdir[b].append((ox, oz))
            rings = {}
            Vl = [tuple(p) for p in V]
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
                p = V[k]
                h = hs[k]
                base = p[1] - h
                r = min(overhang, 0.75 * h)
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
    if m.rock or is_rough(m):
        return 'rock'
    if m.kind == 1:
        return 'wall'
    return 'any'

def base_name(shape):
    return os.path.splitext(os.path.basename(shape.replace('\\', '/')))[0].lower()

def is_rough(m):
    return (not m.rock) and bool(ROUGH.match(base_name(m.shape)))

def ground_of(path):
    with open(path, encoding='latin-1') as fh:
        line = fh.readline()
    g = re.search(r' ground (-?\d+)', line)
    return int(g.group(1)) / 1000.0 if g else -1e6

def params(m, V):
    """class, grid step, smallest patch kept and slab table of a model"""
    cls = model_class(m)
    size = max(np.ptp(V[:, 0]), np.ptp(V[:, 2]))
    step = min(0.15, max(0.04, size / 300.0))
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
    top = Top(V, T, ground, step)
    if not top.valid.any():
        return 'notop', None
    bl = Blanket(top, cls, is_rough(m))
    files = []
    stats = []
    empty = []
    for variant in VARIANTS:
        stage = VARIANTS[variant]
        thick = THICK[kind][variant]
        over = overhang_of(cls, variant, thick)
        d = bl.dense(variant, thick, over, min_area, cls == 'rock')
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
        area = float(top.valid.sum()) * step * step
        b0 = int(min(12000, max(400, area * 100)))
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
