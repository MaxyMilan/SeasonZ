"""Geometric checks of the snow caps (no Blender needed): for each model and depth, measures of what looks wrong.
    python snow_metrics.py <szbake dir> <out.tsv> [--only a,b] [--slice k/n] [--variants 2,4,7]
Columns per model and variant:
  jag     sharp zigzags along the outline of the cover, per metre of outline (teeth, tabs, notches)
  vjag    up and down steps along the outline (cm per metre): an edge that rises and falls between samples
  spike   points standing more than 3 cm above all their neighbours
  pit     points more than 3 cm below all their neighbours
  bare    bare flat open surface the snow should cover (m2), in patches of 0.02 m2 and more
  barefr  that as a share of the flat open surface
  holes   enclosed bare holes in the cover (count) under 0.5 m2
  steep   snow on faces steeper than 60 degrees (m2) that is not the thin end of the cover
  outline metres of outline of the cover
"""
import os, sys, math, collections, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bake_snow as B
import odol_extract as X
import vis_height as VH
import snow_craft as SC

def outline_measures(V, faces, nf):
    eu = collections.Counter()
    for f in faces[:nf]:
        for k in range(3):
            a, b = f[k], f[(k + 1) % 3]
            eu[(min(a, b), max(a, b))] += 1
    nb = collections.defaultdict(list)
    for (a, b), c in eu.items():
        if c == 1:
            nb[a].append(b)
            nb[b].append(a)
    length = 0.0
    for (a, b), c in eu.items():
        if c == 1:
            length += float(np.linalg.norm(V[a] - V[b]))
    sharp = 0
    vstep = 0.0
    for v, ns in nb.items():
        if len(ns) != 2:
            continue
        p, a, b = V[v], V[ns[0]], V[ns[1]]
        d1 = np.array([p[0] - a[0], p[2] - a[2]])
        d2 = np.array([b[0] - p[0], b[2] - p[2]])
        l1, l2 = np.linalg.norm(d1), np.linalg.norm(d2)
        if l1 < 1e-4 or l2 < 1e-4:
            continue
        cosang = float(np.dot(d1, d2) / (l1 * l2))
        # a turn sharper than 100 degrees between two short pieces (under 15 cm): a tooth or notch, not a corner
        if cosang < -0.17 and max(l1, l2) < 0.15:
            sharp += 1
        # height: the point off the line between its neighbours
        mid = 0.5 * (a[1] + b[1])
        vstep += abs(p[1] - mid) if abs(p[1] - mid) > 0.015 else 0.0
    return length, sharp, vstep

def spikes_pits(V, faces):
    """points of the inside of the cover (not its outline, which on a slope has all its neighbours to one side)
    standing out of or sunk into the surface around them"""
    nbr = collections.defaultdict(set)
    eu = collections.Counter()
    for f in faces:
        for k in range(3):
            a, b = f[k], f[(k + 1) % 3]
            nbr[a].add(b)
            nbr[b].add(a)
            eu[(min(a, b), max(a, b))] += 1
    edge = set()
    for (a, b), c in eu.items():
        if c == 1:
            edge.add(a)
            edge.add(b)
    sp = pt = 0
    for v, ns in nbr.items():
        if v in edge:
            continue
        ys = [V[n][1] for n in ns]
        if V[v][1] - max(ys) > 0.03:
            sp += 1
        if min(ys) - V[v][1] > 0.03:
            pt += 1
    return sp, pt

def cliffs(V, faces):
    """area (m2, seen from the side) of near vertical faces in the top of the cover: a wall of snow standing up a
    step or a flap hanging down, where the cover should end or bridge"""
    a = 0.0
    for f in faces:
        P = V[list(f)]
        n = np.cross(P[1] - P[0], P[2] - P[0])
        ln = np.linalg.norm(n)
        if ln < 1e-9:
            continue
        if abs(n[1]) / ln < 0.3 and P[:, 1].max() - P[:, 1].min() > 0.08:
            a += 0.5 * ln
    return a

def grid_measures(top, bl, inside, rock):
    g = top.g
    g2 = g * g
    valid = top.valid
    flat = valid & (top.NY >= 0.85) & (bl.ny >= 0.85) & ~bl.lone
    bare = flat & ~inside
    # patches of bare flat surface
    lab = np.zeros(bare.shape, np.int32)
    cur = 0
    bare_area = 0.0
    holes = 0
    for j0, i0 in zip(*np.nonzero(bare)):
        if lab[j0, i0]:
            continue
        cur += 1
        comp = [(i0, j0)]
        lab[j0, i0] = cur
        closed = True
        q = 0
        while q < len(comp):
            i, j = comp[q]
            q += 1
            for a, b in bl.neighbours(i, j):
                if bare[b, a] and not lab[b, a]:
                    lab[b, a] = cur
                    comp.append((a, b))
                elif not bare[b, a] and not inside[b, a]:
                    closed = False
            if i in (0, top.nu - 1) or j in (0, top.nv - 1):
                closed = False
        area = len(comp) * g2
        if area >= 0.02:
            bare_area += area
        # (a narrow level strip left out only for its size, the step between a tank roof and its rim, is no hole)
        cut = getattr(bl, 'cut', None)
        if cut is not None and all(cut[j, i] for i, j in comp):
            closed = False
        if closed and 0.005 <= area < 0.5:
            holes += 1
    flat_area = float(flat.sum()) * g2
    steep = inside & (top.NY < 0.5)
    return bare_area, bare_area / max(flat_area, 1e-6), holes, float(steep.sum()) * g2

def measure(path, name, variants):
    m = B.parse(path)
    if SC.base_name(m.shape) in SC.SKIP:
        return []
    od = X.read_model(m.shape)
    if od is None:
        return []
    lod = X.visual_lod(od)
    if lod is None:
        return []
    V, T = VH.triangles(lod)
    if len(T) == 0:
        return []
    ground = SC.ground_for(path, V)
    cls, step, min_area, kind = SC.params(m, V)
    top = SC.make_top(m, V, T, ground, step)
    if not top.valid.any():
        return []
    bl = SC.make_blanket(m, top, cls)
    rock = cls == 'rock'
    out = []
    for var in variants:
        thick = SC.THICK[kind][var]
        w, inside, S = bl.field(var, thick, min_area, rock)
        d = bl.dense(var, thick, SC.overhang_of(cls, var, thick), min_area, rock)
        if d is None:
            out.append((name, cls, var, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0))
            continue
        Vd, F = d
        nf = getattr(bl, 'last_nf', len(F))
        length, sharp, vstep = outline_measures(Vd, F, nf)
        sp, pt = spikes_pits(Vd, F[:nf])
        cl = cliffs(Vd, F[:nf])
        bare, barefr, holes, steep = grid_measures(top, bl, inside, rock)
        L = max(length, 1e-6)
        out.append((name, cls, var, round(sharp / L, 3), round(100 * vstep / L, 2), sp, pt, round(bare, 3),
                    round(barefr, 3), holes, round(steep, 3), round(length, 1), sharp, round(cl, 3)))
    return out

def main(argv):
    src, out = argv[0], argv[1]
    only = set(argv[argv.index('--only') + 1].split(',')) if '--only' in argv else None
    k, n = (int(x) for x in (argv[argv.index('--slice') + 1] if '--slice' in argv else '0/1').split('/'))
    variants = [int(v) for v in argv[argv.index('--variants') + 1].split(',')] if '--variants' in argv else [2, 4, 7]
    used = {}
    jobs = []
    for fn in sorted(os.listdir(src)):
        if not fn.endswith('.txt'):
            continue
        with open(os.path.join(src, fn), encoding='latin-1') as fh:
            first = fh.readline().split()
        if len(first) < 2 or first[0] != 'model':
            continue
        name = B.short_name(first[1], used)
        if only is not None and name not in only:
            continue
        jobs.append((fn, name))
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write('model\tcls\tvar\tjag\tvjag\tspike\tpit\tbare\tbarefr\tholes\tsteep\toutline\tsharp\tcliff\n')
        for idx, (fn, name) in enumerate(jobs):
            if idx % n != k:
                continue
            try:
                rows = measure(os.path.join(src, fn), name, variants)
            except Exception as ex:
                rows = [(name, 'error', 0, repr(ex)[:80])]
            for r in rows:
                fh.write('\t'.join(str(x) for x in r) + '\n')
            fh.flush()

if __name__ == '__main__':
    main(sys.argv[1:])

