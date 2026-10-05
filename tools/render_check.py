"""Offline check of the crafted snow: Blender renders the model's visual LOD (grey) with the snow of a few variants
(white, LOD 0) from four sides into one sheet per model.
    blender -b --factory-startup --python render_check.py -- <szbake dir> <out dir> <name,name> [variants 2,4,7]"""
import os, sys, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
import snow_craft as SC
import bake_snow as B
import odol_extract as X
import vis_height as VH

def mesh_obj(name, V, F, color):
    me = bpy.data.meshes.new(name)
    # the game's space is left handed (y up): Blender z up, the game z as Blender y
    me.from_pydata([(float(v[0]), float(v[2]), float(v[1])) for v in V], [], [tuple(f) for f in F])
    me.validate()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    mat = bpy.data.materials.new(name + 'm')
    mat.diffuse_color = color
    me.materials.append(mat)
    return ob

def setup():
    sc = bpy.context.scene
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'
    sc.display.shading.color_type = 'MATERIAL'
    sc.display.shading.show_shadows = True
    sc.display.shading.show_cavity = True
    sc.render.resolution_x = 800
    sc.render.resolution_y = 450
    sc.render.film_transparent = False
    sc.world = sc.world or bpy.data.worlds.new('w')
    cam = bpy.data.cameras.new('c')
    cam.lens = 35
    co = bpy.data.objects.new('cam', cam)
    sc.collection.objects.link(co)
    sc.camera = co
    return co

def look(co, target, az, el, dist):
    a, e = math.radians(az), math.radians(el)
    pos = (target[0] + math.cos(a) * math.cos(e) * dist, target[1] + math.sin(a) * math.cos(e) * dist, target[2] + math.sin(e) * dist)
    co.location = pos
    d = np.array(target) - np.array(pos)
    import mathutils
    co.rotation_euler = mathutils.Vector(d).to_track_quat('-Z', 'Y').to_euler()

def main(argv):
    src, out, names = argv[0], argv[1], argv[2].split(',')
    variants = [int(v) for v in argv[3].split(',')] if len(argv) > 3 else [2, 4, 7]
    os.makedirs(out, exist_ok=True)
    used = {}
    files = {}
    for fn in sorted(os.listdir(src)):
        if fn.endswith('.txt'):
            with open(os.path.join(src, fn), encoding='latin-1') as fh:
                first = fh.readline().split()
            if len(first) > 1 and first[0] == 'model':
                files[B.short_name(first[1], used)] = fn
    for name in names:
        path = os.path.join(src, files[name])
        m = B.parse(path)
        lod = X.visual_lod(X.read_model(m.shape))
        V, T = VH.triangles(lod)
        if len(T) == 0:
            print('sheet', name, 'no faces that hold snow', flush=True)
            continue
        ground = SC.ground_for(path, V)
        cls, step, min_area, kind = SC.params(m, V)
        size = max(np.ptp(V[:, 0]), np.ptp(V[:, 2]))
        dr = SC.drape_for(m, path, V, T, lambda s: print(name, s, flush=True))
        if dr is None:
            top = SC.make_top(m, V, T, ground, step)
            bl = SC.make_blanket(m, top, cls)

        def cap(var):
            thick = SC.THICK[kind][var]
            over = SC.overhang_of(cls, var, thick)
            if dr is not None:
                d = dr.cap(thick, over)
                return (d, dr.area, None) if d else (None, 0, None)
            d = bl.dense(var, thick, over, min_area, cls == 'rock')
            return d, float(top.valid.sum()) * step * step, getattr(bl, 'last_nf', None)
        # framed on the snow (the deepest variant): a tall tower or wall keeps its top in view
        d7 = cap(7)[0]
        # framed on the model and its deepest snow: a tall tower keeps its top in view, a fence its wire
        P = np.vstack([d7[0], V]) if d7 else V
        lo, hi = P.min(0), P.max(0)
        center = ((lo[0] + hi[0]) / 2, (lo[2] + hi[2]) / 2, (lo[1] + hi[1]) / 2)
        ext = max(hi[0] - lo[0], hi[2] - lo[2], hi[1] - lo[1], 1.5)
        # a tall model (tower, silo, crane) needs the distance for its height in the narrow vertical field of view
        dist = max(0.95 * ext + 2.5, 2.0 * (hi[1] - lo[1]) + 2.0)
        views = [(40, 35, variants[min(1, len(variants) - 1)]), (220, 40, variants[min(1, len(variants) - 1)]), (130, 50, variants[0]), (310, 30, variants[-1])]
        for k, (az, el, var) in enumerate(views):
            co = setup()
            mesh_obj('model', V, [tuple(t) for t in T], (0.35, 0.33, 0.3, 1))
            # the terrain under the map object: what lies below it is buried in the game, and what lies within
            # 25 cm over it gets the terrain's snow instead of a cap
            if ground > -1e5:
                m = 0.3 * size + 2.0
                x0, x1 = V[:, 0].min() - m, V[:, 0].max() + m
                z0, z1 = V[:, 2].min() - m, V[:, 2].max() + m
                mesh_obj('ground', [(x0, ground, z0), (x1, ground, z0), (x1, ground, z1), (x0, ground, z1)], [(0, 3, 2, 1)],
                         (0.2, 0.24, 0.16, 1))
            d, area, last_nf = cap(var)
            if d:
                b0 = SC.lod0_budget(area, d[0], d[1][:last_nf]) if last_nf else SC.drape_budget(dr, d[0], d[1])
                if os.environ.get('SZ_BUDGET'):
                    b0 = int(os.environ['SZ_BUDGET'])
                (vs, fs), = SC.simplify(d[0], d[1], (b0,))
                so = mesh_obj('snow', vs, fs, (0.95, 0.96, 1.0, 1))
                # the game smooths the normals of the snow: so does the check
                for p in so.data.polygons:
                    p.use_smooth = True
            look(co, center, az, el, dist)
            fp = os.path.join(out, '_tile_%s_%d_v%d.png' % (name, k, var))
            bpy.context.scene.render.filepath = fp
            bpy.ops.render.render(write_still=True)
        print('sheet', name, flush=True)

if __name__ == '__main__':
    main(sys.argv[sys.argv.index('--') + 1:])
