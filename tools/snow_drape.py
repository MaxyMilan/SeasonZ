"""Snow draped on a model's own faces (headless Blender: bmesh and BVH ray casts).

The raster cover (snow_craft.Blanket) lays the snow over a height grid and finds the model's edges between its samples:
slanted edges, the steps of a stair, slats, boards and tubes came out with teeth, folds and flaps. Here the snow lies
on the faces of the visual LOD themselves:

  * the faces a falling snow reaches: every face flat enough, cut finer where something above hides part of it, kept
    where most rays a little off the vertical meet nothing (snow does not fall exactly straight: a rail over a floor
    leaves no bare strip under it, a roof over a porch or an open stair over a walkway does). Rods and wires hide
    nothing at all
  * the depth: the variant's depth by the slope the snow feels (the normals averaged around each point, so tiles and
    corrugations do not count), and no more than the support is wide (a rail holds a low ridge, not a wall)
  * the surface: hollows and small steps filled (up to 12 cm, at most 60% of the depth), a fillet against a step or a
    lip rising beside it, rounded a little
  * the edges, each found on the model: where the surface falls away the snow ends with its rounded edge (a cornice in
    deep snow); where a face rises beside it the snow runs into that face; under an overhang it thins out; across a
    gap to a surface at about the same height (slats, boards, the stones of a step, the next tile row) it bridges the
    gap, the wider and the more uneven the deeper the snow
"""
import os, math, time, collections
import numpy as np

SKIRT = 0.02
FILL_MAX = 0.12
FILL_SHARE = 0.6
CONE = 0.7
ROD = 0.025
PROBES = (0.012, 0.025, 0.04, 0.06, 0.08, 0.10, 0.125, 0.15)
WALL_RAYS = (0.012, 0.035)
WALL_REACH = 0.06
TILT = math.radians(15.0)
SHADE_SHARE = 0.35
# the rounded edge (out, up as shares of its reach and depth); the last point runs down to the skirt under the surface
DRING = ((0.0, 1.0), (0.55, 0.97), (0.92, 0.8), (1.0, 0.52), (0.82, 0.22), (0.25, None))
OPEN, WALL, BRIDGE, SHADE = 0, 1, 2, 3
# the pieces (each tread, board and bridge with its rounded edge, closed by a bottom under the support) fused into one
# body of snow by a voxel remesh: overlapping pieces join in soft fillets instead of cutting through each other in
# pleats and slits, and the fused body thins down cleanly to the triangle budget
FUSE = os.environ.get('SZ_NOFUSE') is None


def edges_of(F):
    """unique undirected edges of triangles F (k, 3): E (e, 2), the edge of each face side (k, 3), faces per edge"""
    e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    s = np.sort(e, axis=1)
    E, inv, cnt = np.unique(s, axis=0, return_inverse=True, return_counts=True)
    fe = inv.ravel().reshape(3, -1).T
    return E, fe, cnt


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


class Drape:
    def __init__(self, V, T, ground, slope_cls, slope_kind, min_area, thick_kind, cls, log=None):
        import bmesh
        from mathutils import Vector
        from mathutils.bvhtree import BVHTree
        from mathutils.kdtree import KDTree
        import snow_craft as SC
        t0 = time.time()
        self.SC = SC
        self.thick_kind, self.cls = thick_kind, cls
        self.empty = True
        glass = getattr(T, 'glass', None)
        V = np.asarray(V, dtype=np.float64)
        T = np.asarray(T, dtype=np.int64).reshape(-1, 3)
        glass = np.zeros(len(T), bool) if glass is None else np.asarray(glass, bool)
        size = max(float(np.ptp(V[:, 0])), float(np.ptp(V[:, 2])), 0.5)
        L = float(os.environ.get('SZ_DRAPE_L', '0')) or min(2.0, max(0.35, size / 12.0))
        Lmin = 0.03 if size > 4.0 else 0.02
        A, Bv, C = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
        n = np.cross(Bv - A, C - A)
        ln = np.linalg.norm(n, axis=1)
        longest = np.max(np.stack([np.linalg.norm(Bv - A, axis=1), np.linalg.norm(C - Bv, axis=1),
                                   np.linalg.norm(A - C, axis=1)]), 0)
        good = ln > 1e-10
        wide = good & (ln / np.maximum(longest, 1e-9) >= ROD)
        ny = np.abs(n[:, 1]) / np.maximum(ln, 1e-12)
        # one vertex per position (the LOD splits them along texture seams)
        key = np.round(V / 0.001).astype(np.int64)
        _, vid = np.unique(key, axis=0, return_inverse=True)
        vid = vid.ravel()
        TV = vid[T]
        # thin triangles joined by an edge to a wide one (a sliver of a roof) belong to a surface; the others are rods,
        # wires and cables: they hide nothing and hold nothing
        E0, fe0, cnt0 = edges_of(TV)
        slot_face = np.repeat(np.arange(len(T)), 3)
        by_edge = collections.defaultdict(list)
        for f, e in zip(slot_face, fe0.ravel()):
            by_edge[int(e)].append(int(f))
        sheet = wide.copy()
        todo = [int(f) for f in np.nonzero(wide)[0]]
        while todo:
            f = todo.pop()
            for e in fe0[f]:
                for g in by_edge[int(e)]:
                    if not sheet[g] and good[g]:
                        sheet[g] = True
                        todo.append(g)
        occ = sheet & good
        self.bvh = BVHTree.FromPolygons([tuple(p) for p in V], [tuple(int(i) for i in t) for t in T[occ]],
                                        all_triangles=True, epsilon=0.0)
        bvh = self.bvh
        cy = (A[:, 1] + Bv[:, 1] + C[:, 1]) / 3.0
        cand = good & (ny >= 0.3) & ~(glass & (ny < 0.8)) & (cy >= ground + 0.25)
        idx = np.nonzero(cand)[0]
        self.stats = {'tris': int(len(T)), 'cand': int(len(idx))}
        if len(idx) == 0:
            return
        # the candidate faces as one mesh, cut to edges of at most L
        bm = bmesh.new()
        used, inv = np.unique(TV[idx].ravel(), return_inverse=True)
        first = np.zeros(int(vid.max()) + 1, dtype=np.int64)
        first[vid[::-1]] = np.arange(len(vid))[::-1]
        pos = V[first[used]]
        bv = [bm.verts.new((float(p[0]), float(p[1]), float(p[2]))) for p in pos]
        seen = set()
        for a, b, c in inv.reshape(-1, 3):
            if a == b or b == c or a == c:
                continue
            s = tuple(sorted((int(a), int(b), int(c))))
            if s in seen:
                continue
            seen.add(s)
            try:
                bm.faces.new((bv[a], bv[b], bv[c]))
            except ValueError:
                pass
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)

        def tri_all():
            ng = [f for f in bm.faces if len(f.verts) > 3]
            if ng:
                bmesh.ops.triangulate(bm, faces=ng, quad_method='BEAUTY', ngon_method='BEAUTY')

        tri_all()
        for _ in range(16):
            long = [e for e in bm.edges if e.calc_length() > L]
            if not long:
                break
            bmesh.ops.subdivide_edges(bm, edges=long, cuts=1, use_grid_fill=False)
            tri_all()
        up = Vector((0.0, 1.0, 0.0))
        st = math.sin(TILT)
        ct = math.cos(TILT)
        tilted = [Vector((st, ct, 0.0)), Vector((-st, ct, 0.0)), Vector((0.0, ct, st)), Vector((0.0, ct, -st))]

        def visible(f):
            c = f.calc_center_median()
            o = Vector((c.x, c.y + 0.004, c.z))
            free = 0
            for d in tilted:
                if bvh.ray_cast(o, d)[0] is None:
                    free += 1
            if free >= 3:
                return True
            return free >= 2 and bvh.ray_cast(o, up)[0] is None

        state = {}
        for _ in range(7):
            state = {f: visible(f) for f in bm.faces}
            todo = set()
            for e in bm.edges:
                lf = e.link_faces
                if len(lf) == 2 and state[lf[0]] != state[lf[1]]:
                    for f in lf:
                        for e2 in f.edges:
                            if e2.calc_length() > Lmin:
                                todo.add(e2)
            if not todo:
                break
            bmesh.ops.subdivide_edges(bm, edges=list(todo), cuts=1, use_grid_fill=False)
            tri_all()
            state = {}
        if not state:
            state = {f: visible(f) for f in bm.faces}
        bm.verts.index_update()
        P = np.array([v.co[:] for v in bm.verts], dtype=np.float64)
        F = np.array([[v.index for v in f.verts] for f in bm.faces if len(f.verts) == 3 and state.get(f)],
                     dtype=np.int64).reshape(-1, 3)
        bm.free()
        if len(F) == 0:
            return
        # faces up (their normal +y), deduplicated
        s = np.sort(F, axis=1)
        _, keep = np.unique(s, axis=0, return_index=True)
        F = F[np.sort(keep)]
        nf = np.cross(P[F[:, 1]] - P[F[:, 0]], P[F[:, 2]] - P[F[:, 0]])
        flip = nf[:, 1] < 0
        F[flip] = F[flip][:, [0, 2, 1]]
        nf[flip] = -nf[flip]
        ar = np.linalg.norm(nf, axis=1)
        ok = ar > 1e-12
        F, nf, ar = F[ok], nf[ok], ar[ok]
        nu = nf / ar[:, None]
        # the slope the snow feels: normals averaged around each point
        E, fe, cnt = edges_of(F)
        nv = np.zeros_like(P)
        for k in range(3):
            np.add.at(nv, F[:, k], nf)
        for _ in range(3):
            s2 = nv.copy()
            np.add.at(s2, E[:, 0], nv[E[:, 1]])
            np.add.at(s2, E[:, 1], nv[E[:, 0]])
            nv = s2 / np.maximum(np.linalg.norm(s2, axis=1, keepdims=True), 1e-12)
        nyv = nv[:, 1]
        nyf = (nyv[F[:, 0]] + nyv[F[:, 1]] + nyv[F[:, 2]]) / 3.0
        wf = np.array([SC.slope_w(slope_cls, 4, float(x), slope_kind) for x in nyf])
        # a face past the slope limit holds nothing, even where the averaged slope carried some cover onto it
        keepf = (wf >= 0.1) & (nu[:, 1] >= 0.45)
        F, nf, ar, wf = F[keepf], nf[keepf], ar[keepf], wf[keepf]
        if len(F) == 0:
            return
        E, fe, cnt = edges_of(F)
        # patches: faces joined by an edge
        slot_face = np.repeat(np.arange(len(F)), 3)
        order = np.argsort(fe.ravel(), kind='stable')
        ef = fe.ravel()[order]
        sf = slot_face[order]
        uf = UF(len(F))
        same = ef[1:] == ef[:-1]
        for i in np.nonzero(same)[0]:
            uf.union(int(sf[i]), int(sf[i + 1]))
        patch = np.array([uf.find(i) for i in range(len(F))])
        # boundary edges (one face): the vertex across in that face
        single = cnt[ef] == 1
        BE = E[ef[single]]
        BF = sf[single]
        third = []
        for (a, b), f in zip(BE, BF):
            tri = F[f]
            third.append(int(tri[(tri != a) & (tri != b)][0]))
        BC = np.array(third, dtype=np.int64)
        # the edges, each found on the model: a face rising beside it (a wall, a riser, a lip), an overhang above it,
        # and the surfaces beyond it
        ytop = float(V[:, 1].max()) + 1.0
        down = Vector((0.0, -1.0, 0.0))
        nb = len(BE)
        npb = len(PROBES)
        good_e = np.ones(nb, bool)
        bn = np.zeros((nb, 2))
        wall_d = np.full(nb, np.nan)
        wall_top = [None] * nb
        shade = np.zeros(nb, bool)
        pdy = np.full((nb, npb), np.nan)
        pny = np.zeros((nb, npb))
        ploc = [[None] * npb for _ in range(nb)]
        for i in range(nb):
            a, b, c = int(BE[i, 0]), int(BE[i, 1]), int(BC[i])
            pa, pb, pc = P[a], P[b], P[c]
            mx, my, mz = (pa + pb) / 2.0
            ex, ez = pb[0] - pa[0], pb[2] - pa[2]
            el = math.hypot(ex, ez)
            if el < 1e-5:
                good_e[i] = False
                continue
            nx, nz = ez / el, -ex / el
            if (mx - pc[0]) * nx + (mz - pc[2]) * nz < 0:
                nx, nz = -nx, -nz
            bn[i] = (nx, nz)
            hit = None
            for dy in WALL_RAYS:
                loc, nrm, _, dist = bvh.ray_cast(Vector((mx - 0.01 * nx, my + dy, mz - 0.01 * nz)), Vector((nx, 0.0, nz)),
                                                 WALL_REACH + 0.01)
                if loc is not None and (hit is None or dist < hit):
                    hit = dist
            if hit is not None:
                wall_d[i] = max(0.0, hit - 0.01)
                loc = bvh.ray_cast(Vector((mx + nx * (wall_d[i] + 0.03), ytop, mz + nz * (wall_d[i] + 0.03))), down)[0]
                if loc is not None and 0.0 < loc.y - my <= 0.3:
                    wall_top[i] = (loc.x, loc.y, loc.z)
                continue
            for k, d in enumerate(PROBES):
                loc, nrm, _, _ = bvh.ray_cast(Vector((mx + nx * d, ytop, mz + nz * d)), down)
                if loc is None:
                    continue
                pdy[i, k] = loc.y - my
                pny[i, k] = abs(nrm.y)
                ploc[i][k] = (loc.x, loc.y, loc.z)
            if pdy[i, 0] > 0.08:
                shade[i] = True
        self.P, self.F, self.E = P, F, E
        self.BE, self.bn, self.wall_d, self.shade, self.pdy, self.pny = BE, bn, wall_d, shade, pdy, pny
        self.good_e = good_e
        # how wide the support is (to its open edges in a middle depth): the largest disk inside its outline that
        # holds each point
        typ4, _, _ = self.kinds(SC.THICK[thick_kind][4], links=False)
        vin = np.zeros(len(P), bool)
        vin[F.ravel()] = True
        openE = BE[(typ4 == OPEN) & good_e]
        dv = np.full(len(P), 10.0)
        if len(openE):
            pts = []
            for a, b in openE:
                pa, pb = P[a], P[b]
                k = max(1, int(math.hypot(pb[0] - pa[0], pb[2] - pa[2]) / 0.005))
                for t in np.linspace(0.0, 1.0, k + 1):
                    pts.append((pa[0] + (pb[0] - pa[0]) * t, pa[2] + (pb[2] - pa[2]) * t))
            kd = KDTree(len(pts))
            for k, (x, z) in enumerate(pts):
                kd.insert((x, 0.0, z), k)
            kd.balance()

            def dist(x, z):
                return kd.find((x, 0.0, z))[2]

            dv = np.zeros(len(P))
            for v in np.nonzero(vin)[0]:
                dv[v] = dist(P[v, 0], P[v, 2])
            cen = (P[F[:, 0]] + P[F[:, 1]] + P[F[:, 2]]) / 3.0
            dc = np.array([dist(c[0], c[2]) for c in cen])
            mid = (P[E[:, 0]] + P[E[:, 1]]) / 2.0
            dm = np.array([dist(c[0], c[2]) for c in mid])
            for k in range(3):
                np.maximum.at(dv, F[:, k], dc)
            np.maximum.at(dv, E[:, 0], dm)
            np.maximum.at(dv, E[:, 1], dm)
        R = np.where(vin, dv, 0.0)
        rem = R.copy()
        el3 = np.linalg.norm(P[E[:, 0]] - P[E[:, 1]], axis=1)
        for _ in range(60):
            nR = R.copy()
            for s_, t_ in ((0, 1), (1, 0)):
                u, v = E[:, s_], E[:, t_]
                okm = rem[u] - el3 >= 0
                np.maximum.at(nR, v[okm], R[u][okm])
            nrem = np.where(nR > R + 1e-9, -1.0, rem)
            for s_, t_ in ((0, 1), (1, 0)):
                u, v = E[:, s_], E[:, t_]
                cm = rem[u] - el3
                m = (cm >= 0) & (np.abs(R[u] - nR[v]) < 1e-9)
                np.maximum.at(nrem, v[m], cm[m])
            if not (nR > R + 1e-9).any() and np.allclose(nrem, rem):
                break
            R, rem = nR, np.maximum(nrem, 0.0)
        W = 2.0 * R
        # rods and scraps: patches narrower than a rod or smaller than the smallest patch kept
        pk = {}
        for f, p in enumerate(patch):
            pk.setdefault(int(p), []).append(f)
        keepf = np.ones(len(F), bool)
        for p, fs in pk.items():
            fs = np.array(fs)
            vs = np.unique(F[fs].ravel())
            area = 0.5 * float(np.abs(nf[fs, 1]).sum())
            if W[vs].max() < ROD or area < min_area:
                keepf[fs] = False
        live = np.zeros(len(P), bool)
        live[F[keepf].ravel()] = True
        # vertex weight: the steepest kept face round a vertex does not thin the snow at its edge
        wv = np.zeros(len(P))
        for k in range(3):
            np.maximum.at(wv, F[keepf][:, k], wf[keepf])
        # the support vertex at each surface found beyond an edge (for fillets and bridges)
        pvert = np.full((nb, npb), -1, dtype=np.int64)
        wvert = np.full(nb, -1, dtype=np.int64)
        if live.any():
            kdv = KDTree(int(live.sum()))
            for v in np.nonzero(live)[0]:
                kdv.insert(P[v], int(v))
            kdv.balance()
            for i in range(nb):
                if wall_top[i] is not None:
                    co, j, dd = kdv.find(wall_top[i])
                    if j is not None and dd <= 0.06:
                        wvert[i] = j
                for k in range(npb):
                    if ploc[i][k] is not None:
                        co, j, dd = kdv.find(ploc[i][k])
                        if j is not None and dd <= 0.06:
                            pvert[i, k] = j
        bok = good_e & live[BE[:, 0]] & live[BE[:, 1]] & keepf[BF]
        self.F = F[keepf]
        self.E = edges_of(self.F)[0] if len(self.F) else E[:0]
        self.BE, self.bn, self.wall_d, self.shade = BE[bok], bn[bok], wall_d[bok], shade[bok]
        self.pdy, self.pny, self.pvert, self.wvert = pdy[bok], pny[bok], pvert[bok], wvert[bok]
        self.good_e = good_e[bok]
        self.W, self.wv = W, wv
        self.area = 0.5 * float(np.abs(nf[keepf, 1]).sum())
        self.empty = not keepf.any()
        t4 = self.kinds(SC.THICK[thick_kind][4], links=False)[0]
        self.stats.update({'support': int(len(self.F)), 'verts': int(len(P)), 'edges': int(len(self.BE)),
                           'open': int((t4 == OPEN).sum()), 'wall': int((t4 == WALL).sum()),
                           'bridge': int((t4 == BRIDGE).sum()), 'shade': int((t4 == SHADE).sum()),
                           'time': round(time.time() - t0, 2)})
        if log:
            log('drape %s' % self.stats)

    def kinds(self, h, links=True):
        """the type of each edge for snow of depth h (and the gap or wall distance), with the links for the fill"""
        d = np.array(PROBES)
        tol = 0.02 + 0.3 * d + 0.3 * h
        gmax = min(0.15, 0.02 + 0.5 * h)
        dy = np.nan_to_num(self.pdy, nan=9.0)
        wall = ~np.isnan(self.wall_d)
        ok = (np.abs(dy) <= tol[None, :]) & (self.pny >= 0.45) & (d[None, :] <= gmax + 1e-9)
        ok &= ~(self.shade | wall)[:, None]
        anyok = ok.any(1)
        first = np.argmax(ok, 1)
        typ = np.full(len(self.BE), OPEN)
        typ[self.shade] = SHADE
        typ[wall] = WALL
        typ[anyok] = BRIDGE
        val = np.where(wall, np.nan_to_num(self.wall_d), 0.0)
        val[anyok] = d[first[anyok]]
        if not links:
            return typ, val, None
        # the support vertex across each bridged gap
        part = np.full(len(self.BE), -1, dtype=np.int64)
        part[anyok] = self.pvert[np.nonzero(anyok)[0], first[anyok]]
        self.part = part
        lk = []
        for i in np.nonzero(anyok)[0]:
            j = self.pvert[i, first[i]]
            if j >= 0:
                for a in self.BE[i]:
                    if a != j:
                        lk.append((int(a), int(j)))
        # a fillet only against a low lip (a tile row, a batten, a kerb): against a real step (a riser) the snow of
        # each tread keeps its own cover (filled up to the next tread it rose as a slanted sheet over the whole tread)
        for i in np.nonzero(wall & (self.wvert >= 0))[0]:
            j = self.wvert[i]
            for a in self.BE[i]:
                if a != j and self.P[j, 1] - self.P[a, 1] <= min(FILL_MAX, 0.5 * h):
                    lk.append((int(a), int(j)))
        return typ, val, np.array(lk, dtype=np.int64).reshape(-1, 2)

    def cap_variant(self, variant):
        SC = self.SC
        thick = SC.THICK[self.thick_kind][variant]
        over = SC.overhang_of(self.cls, variant, thick)
        return self.cap(thick, over)

    def cap(self, thick, over):
        """the snow of one depth: (vertices, faces) or None"""
        if self.empty:
            return None
        P, F, E = self.P, self.F, self.E
        typ, val, LE = self.kinds(thick)
        y = P[:, 1]
        h0 = thick * self.wv
        h0 = np.minimum(h0, 1.5 * self.W + 0.02)
        # under an overhang the snow thins out to its edge
        sv = np.unique(self.BE[typ == SHADE].ravel())
        h0[sv] *= SHADE_SHARE
        top = y + h0
        ub = top + np.minimum(FILL_MAX, FILL_SHARE * h0)
        ub[sv] = top[sv]
        AE = np.vstack([E, LE]) if len(LE) else E
        AL = np.concatenate([np.linalg.norm(P[E[:, 0]] - P[E[:, 1]], axis=1),
                             np.hypot(P[LE[:, 0], 0] - P[LE[:, 1], 0], P[LE[:, 0], 2] - P[LE[:, 1], 2])
                             if len(LE) else np.zeros(0)])
        for _ in range(100):
            best = np.full_like(top, -np.inf)
            np.maximum.at(best, AE[:, 1], top[AE[:, 0]] - CONE * AL)
            np.maximum.at(best, AE[:, 0], top[AE[:, 1]] - CONE * AL)
            new = np.maximum(top, np.minimum(ub, best))
            done = float(np.max(new - top)) < 1e-5
            top = new
            if done:
                break
        for _ in range(2):
            s = np.zeros_like(top)
            c = np.zeros_like(top)
            np.add.at(s, E[:, 0], top[E[:, 1]])
            np.add.at(c, E[:, 0], 1.0)
            np.add.at(s, E[:, 1], top[E[:, 0]])
            np.add.at(c, E[:, 1], 1.0)
            avg = np.where(c > 0, s / np.maximum(c, 1.0), top)
            top = np.clip(0.5 * top + 0.5 * avg, y + 0.85 * h0, np.maximum(ub, y + 0.85 * h0))
        H = top - y
        K = len(DRING)
        Vt = P.copy()
        Vt[:, 1] = top
        n = len(P)
        Vb = P.copy()
        Vb[:, 1] -= SKIRT
        newv = []
        base = 2 * n
        tris = []
        expn = []
        DOWN = (0.0, -1.0, 0.0)

        part = self.part

        def profile(v, t, va, pj):
            h = H[v]
            yv = y[v]
            r = min(over, 0.75 * h) if t == OPEN else 0.0
            if t == OPEN and r > 0.004:
                return [r * fr for fr, fu in DRING], [yv + h * fu if fu is not None else yv - SKIRT for fr, fu in DRING]
            # the other edges need no more than a few of the ring's points: the rest fall together and their faces
            # drop out (no area)
            if t in (OPEN, SHADE):
                return [0.0] * K, [yv + h] * (K - 1) + [yv - SKIRT]
            if t == WALL:
                ext = min(WALL_REACH, va + 0.02)
                return [0.0] + [ext] * (K - 1), [yv + h] * (K - 1) + [yv - SKIRT]
            # a bridge: its underside a little over the support (a skirt down into the gap hung as a white curtain
            # between slats); its top runs to the middle height of both sides, so the two halves meet without a step
            ext = va / 2.0 + 0.012
            ym = 0.5 * (top[v] + top[pj]) if pj >= 0 else top[v]
            return [0.0] + [ext] * (K - 1), [yv + h] + [ym] * (K - 2) + [min(yv + 0.15 * h, ym - 0.01)]

        def ring(v, nx, nz, outs, ys):
            ids = [int(v)]
            for o, yy in zip(outs[1:], ys[1:]):
                newv.append((P[v, 0] + nx * o, yy, P[v, 2] + nz * o))
                ids.append(base + len(newv) - 1)
            return ids

        def strip(ra, rb, na, nb_, oa, ya, ob, yb):
            for j in range(K - 1):
                do = 0.5 * ((oa[j + 1] - oa[j]) + (ob[j + 1] - ob[j]))
                dy = 0.5 * ((ya[j + 1] - ya[j]) + (yb[j + 1] - yb[j]))
                nx, nz = 0.5 * (na[0] + nb_[0]), 0.5 * (na[1] + nb_[1])
                ex = (nx * -dy, do, nz * -dy)
                q = (ra[j], rb[j], rb[j + 1], ra[j + 1])
                if q[0] != q[1]:
                    tris.append((q[0], q[1], q[2]))
                    expn.append(ex)
                tris.append((q[0], q[2], q[3]))
                expn.append(ex)

        def close_edge(ra, rb, a, b):
            if FUSE:
                tris.append((ra[-1], rb[-1], b + n))
                expn.append(DOWN)
                tris.append((ra[-1], b + n, a + n))
                expn.append(DOWN)

        rings = {}
        at = collections.defaultdict(list)
        for i, (a, b) in enumerate(self.BE):
            nx, nz = self.bn[i]
            pa = profile(a, typ[i], val[i], part[i])
            pb = profile(b, typ[i], val[i], part[i])
            ra = ring(a, nx, nz, *pa)
            rb = ring(b, nx, nz, *pb)
            strip(ra, rb, (nx, nz), (nx, nz), pa[0], pa[1], pb[0], pb[1])
            close_edge(ra, rb, int(a), int(b))
            rings[(i, int(a))] = (ra, pa)
            rings[(i, int(b))] = (rb, pb)
            at[int(a)].append((i, int(b)))
            at[int(b)].append((i, int(a)))
        # round the convex corners of the outline (in steps by how far the edge reaches out)
        for v, lst in at.items():
            if len(lst) != 2:
                continue
            (i1, o1), (i2, o2) = lst
            n1, n2 = self.bn[i1], self.bn[i2]
            d2 = P[o2, [0, 2]] - P[v, [0, 2]]
            l2 = float(np.hypot(*d2))
            if l2 < 1e-6 or float(n1 @ d2) / l2 > -0.02:
                continue
            th = math.atan2(n1[0] * n2[1] - n1[1] * n2[0], float(n1 @ n2))
            r1, p1 = rings[(i1, v)]
            r2, p2 = rings[(i2, v)]
            rmax = max(max(p1[0]), max(p2[0]))
            k = max(1, int(math.ceil(abs(th) / (math.pi / 2) * (1.0 + 2.0 * min(1.0, rmax / 0.06)))))
            prev, pprev, nprev = r1, p1, n1
            for t in range(1, k + 1):
                if t < k:
                    a_ = th * t / k
                    ca, sa = math.cos(a_), math.sin(a_)
                    nd = (n1[0] * ca - n1[1] * sa, n1[0] * sa + n1[1] * ca)
                    f = t / k
                    pc = ([o1_ * (1 - f) + o2_ * f for o1_, o2_ in zip(p1[0], p2[0])],
                          [y1 * (1 - f) + y2 * f for y1, y2 in zip(p1[1], p2[1])])
                    rc = ring(v, nd[0], nd[1], *pc)
                else:
                    nd, pc, rc = n2, p2, r2
                strip(prev, rc, nprev, nd, pprev[0], pprev[1], pc[0], pc[1])
                if FUSE:
                    tris.append((prev[-1], rc[-1], int(v) + n))
                    expn.append(DOWN)
                prev, pprev, nprev = rc, pc, nd
        Vall = np.vstack([Vt, Vb, np.array(newv, dtype=np.float64).reshape(-1, 3)])
        T2 = np.array(tris, dtype=np.int64).reshape(-1, 3)
        X = np.array(expn, dtype=np.float64).reshape(-1, 3)
        if len(T2):
            n2 = np.cross(Vall[T2[:, 1]] - Vall[T2[:, 0]], Vall[T2[:, 2]] - Vall[T2[:, 0]])
            flip = (n2 * X).sum(1) < 0
            T2[flip] = T2[flip][:, [0, 2, 1]]
        # faces wound like the raster cover's (their cross product outward, see snow_craft.p3dm)
        parts = [F, T2]
        if FUSE:
            parts.append(F[:, [0, 2, 1]] + n)
        Fall = np.vstack(parts)
        if os.environ.get('SZ_DRAPE_FLIP'):
            Fall = Fall[:, [0, 2, 1]]
        na = np.linalg.norm(np.cross(Vall[Fall[:, 1]] - Vall[Fall[:, 0]], Vall[Fall[:, 2]] - Vall[Fall[:, 0]]), axis=1)
        Fall = Fall[na > 1e-9]
        usedv = np.unique(Fall.ravel())
        remap = -np.ones(len(Vall), dtype=np.int64)
        remap[usedv] = np.arange(len(usedv))
        Vo, Fo = Vall[usedv], remap[Fall]
        # the budget of the first LOD: by the area and the length of the snow's open edges, as the raster cover's
        el = 0.0
        for (a, b), t in zip(self.BE, typ):
            if t in (OPEN, SHADE):
                el += float(np.hypot(P[a, 0] - P[b, 0], P[a, 2] - P[b, 2]))
        self.last_budget = int(min(12000, max(400, self.area * 100, el * 60)))
        if not FUSE:
            return Vo, [tuple(int(i) for i in f) for f in Fo]
        hmin = float(np.min(H[np.unique(F.ravel())])) if len(F) else thick
        return self.fuse(Vo, Fo, thick, hmin)

    def fuse(self, V, F, thick, hmin):
        """the closed pieces as one body: a voxel remesh (fine enough for the thinnest snow), the bottom faces lying
        under the support taken off (hidden in the model, they would only cost triangles)"""
        import bpy, bmesh
        from mathutils import Vector
        area = max(self.area, 0.05)
        vox = float(os.environ.get('SZ_VOXEL', '0')) or float(np.clip(math.sqrt(2.5 * area / 8e5), 0.005, 0.03))
        vox = min(vox, max(0.004, (min(hmin, thick) + SKIRT) / 3.0))
        me = bpy.data.meshes.new('pieces')
        me.from_pydata([tuple(p) for p in V], [], [tuple(int(i) for i in f) for f in F])
        me.validate(clean_customdata=False)
        ob = bpy.data.objects.new('pieces', me)
        bpy.context.scene.collection.objects.link(ob)
        mod = ob.modifiers.new('r', 'REMESH')
        mod.mode = 'VOXEL'
        mod.voxel_size = vox
        mod.adaptivity = 0.0
        dg = bpy.context.evaluated_depsgraph_get()
        m2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        bpy.data.objects.remove(ob)
        bpy.data.meshes.remove(me)
        bm = bmesh.new()
        bm.from_mesh(m2)
        bpy.data.meshes.remove(m2)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        up = Vector((0.0, 1.0, 0.0))
        gone = []
        for f in bm.faces:
            no = f.normal
            if no.y < -0.3:
                c = f.calc_center_median()
                if self.bvh.ray_cast(c, up, SKIRT + 3 * vox)[0] is not None:
                    gone.append(f)
        bmesh.ops.delete(bm, geom=gone, context='FACES')
        bm.verts.ensure_lookup_table()
        bm.verts.index_update()
        Vo = np.array([v.co[:] for v in bm.verts], dtype=np.float64)
        Fo = [tuple(v.index for v in f.verts) for f in bm.faces]
        bm.free()
        self.last_voxel = vox
        return Vo, Fo

