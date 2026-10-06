"""Small fence-top cushions measured from the original supporting faces.

Owned by planken. Unlike the raster ridge, a cushion uses one part's actual
top corners and limits its height to a fraction of the wood's narrow width.
Thin planks receive millimetres, with smooth growth across all seven depths.
Steep pointed cuts and surfaces smaller than 8 mm hold no separate cap.
"""
import math
import numpy as np
import snow_hand as H


def cushion(m, part, v, ny_min=0.85, min_width=0.008):
    """A shallow cushion on a four-corner flat or gently slanted cut top.

    The top must consist of two triangles; bevel faces are excluded. The
    border seats 1 mm into its support and no snow extends down vertical wood.
    All vertices and expected support cells are registered with Model.check.
    """
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    tt = np.where((m.part_t == part) & (m.n_t[:, 1] >= ny_min))[0]
    if not len(tt):
        return None
    # Restrict to the highest cut, excluding disconnected lower ledges.
    ym = m.V[m.T[tt]].mean(1)[:, 1]
    tt = tt[ym >= ym.max() - 0.045]
    P = np.unique(m.V[m.T[tt]].reshape(-1, 3), axis=0)
    if len(P) != 4:
        return None
    c = P.mean(0)
    order = np.argsort(np.arctan2(P[:, 2]-c[2], P[:, 0]-c[0]))
    P = P[order]
    edges = np.linalg.norm(np.roll(P[:, [0, 2]], -1, 0)-P[:, [0, 2]], axis=1)
    if edges[0] < edges[1]:
        P = np.roll(P, -1, 0)
        edges = np.roll(edges, -1)
    width = float(min(edges[1], edges[3]))
    if width < min_width:
        return None
    ny = float(m.n_t[tt, 1].min())
    # (Opus, 6 Oct) the review saw bare picket tops: a cap of a few millimetres does not show in the game. Cohesive
    # snow on a narrow cut top stands as high as on a rail (snow_hand.RIDGE_W): 1.5 cm at v1, about 2.8 cm at v7 on a
    # 2 cm board, a rounded loaf across it
    height = min(m.thick(v), H.RIDGE_W*width + 0.006) * ny**2
    ns, nu = 7, 5  # (a fence has dozens of cut tops: 48 triangles each)
    s = (np.sin(np.linspace(-math.pi/2, math.pi/2, ns))+1)*0.5
    u = (np.sin(np.linspace(-math.pi/2, math.pi/2, nu))+1)*0.5
    S, U = np.meshgrid(s, u, indexing='ij')
    W = ((1-S)*(1-U), S*(1-U), S*U, (1-S)*U)
    V = sum(w[..., None]*p for w, p in zip(W, P)).reshape(-1, 3)
    own = BVHTree.FromPolygons([tuple(p) for p in m.V], [tuple(map(int,t)) for t in m.T[tt]], all_triangles=True)
    down, up = Vector((0,-1,0)), Vector((0,1,0))
    # Interior probes avoid precision misses on triangle edges.
    for i, p in enumerate(V):
        pin = p*0.999+c*0.001
        hit = own.ray_cast(Vector((float(pin[0]), float(P[:,1].max()+0.1), float(pin[2]))), down, 1.0)[0]
        if hit is not None:
            V[i,1] = hit.y
    # Small sheltered cut tops have no independent accumulation.
    hit, normal, _, _ = m.bvh_all.ray_cast(Vector((float(c[0]),float(c[1]+0.006),float(c[2]))), up, 3.0)
    if hit is not None and normal.y < -0.3:
        return None
    profile = (np.maximum(0, 4*S*(1-S))**0.3*np.maximum(0, 4*U*(1-U))**0.3).ravel()
    V[:,1] += height*profile
    idx = np.arange(ns*nu).reshape(ns,nu)
    foot = np.zeros(ns*nu, bool)
    foot[idx[0,:]]=foot[idx[-1,:]]=foot[idx[:,0]]=foot[idx[:,-1]]=True
    V[foot,1] -= 0.001
    F = []
    for i in range(ns-1):
        for j in range(nu-1):
            a,b,c_,d = idx[i,j],idx[i+1,j],idx[i+1,j+1],idx[i,j+1]
            F.extend(((a,b,c_),(a,c_,d)))
    F = np.array(F, dtype=np.int64)
    n = np.cross(V[F[:,1]]-V[F[:,0]],V[F[:,2]]-V[F[:,0]])
    if n[:,1].sum()<0:
        F=F[:,[0,2,1]]
    m._caps.append({'V':V,'F':F,'role':np.where(foot,3,0),
                    'anchor':np.full(len(V),-1),'foot':foot})
    # Only the chosen cut faces hold the cushion; a leaning upright face may
    # have a deceptively gentle *raster-averaged* normal near a neighbour.
    sel=m.tops(v,parts=[part],ny_min=ny_min) & np.isin(m.TID,tt)
    m._sel |= sel
    m._claimed |= sel
    return V,F


def coping(m, part, v, cutters=(), smooth=False):
    """Continuous cushion on a rectangular masonry coping, sampled on its own
    original faces, so upright pickets cannot deform the supporting surface.
    A smooth transverse dome and rounded ends seat at the coping boundary.
    """
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    tt=np.where((m.part_t==part)&(m.n_t[:,1]>0.45))[0]
    P=m.V[m.T[tt]].reshape(-1,3)
    x0,z0=P[:,[0,2]].min(0)+0.0005
    x1,z1=P[:,[0,2]].max(0)-0.0005
    width=z1-z0; length=x1-x0
    ns=max(17,int(math.ceil(length/0.06))+1); nu=17
    sx=np.linspace(0,1,ns)
    uz=(np.sin(np.linspace(-math.pi/2,math.pi/2,nu))+1)/2
    # Extra close stations make both rail-like ends smoothly rounded.
    sx=np.unique(np.concatenate([sx,[0.002,0.006,0.015,0.03,0.97,0.985,0.994,0.998]]))
    ns=len(sx)
    S,U=np.meshgrid(sx,uz,indexing='ij')
    X=x0+S*length; Z=z0+U*width
    V=np.column_stack([X.ravel(),np.zeros(X.size),Z.ravel()])
    bp=BVHTree.FromPolygons([tuple(p) for p in m.V],[tuple(map(int,t)) for t in m.T[tt]],all_triangles=True)
    base=[]
    for vi,(x,_,z) in enumerate(V):
        hit=bp.ray_cast(Vector((float(x),float(P[:,1].max()+0.2),float(z))),Vector((0,-1,0)),2.0)[0]
        if hit is None:
            # Rectangular chamfer corners: nearest original top, never a
            # disconnected patch suspended above the coping.
            loc=bp.find_nearest(Vector((float(x),float(P[:,1].min()),float(z))))[0]
            V[vi,0],V[vi,2]=loc.x,loc.z
            base.append(float(loc.y))
        else: base.append(float(hit.y))
    base=np.asarray(base)
    height=min(m.thick(v)*0.65,0.25*width)
    end=min(width*0.55,length*0.4)
    q=np.minimum(np.clip(S*length/end,0,1),np.clip((1-S)*length/end,0,1))
    profile=np.sqrt(q*(2-q))*np.sqrt(4*U*(1-U))
    raised=base.reshape(ns,nu).copy()
    if smooth:
        for _ in range(6):
            for axis in (0,1):
                raised=np.apply_along_axis(lambda a:np.maximum(a,np.convolve(np.pad(a,1,mode='edge'),[0.25,0.5,0.25],'valid')),axis,raised)
    # Keep the seating boundary on the original wood/stone.
    blend=np.minimum(1.0,profile*4)
    V[:,1]=base+(raised.ravel()-base)*blend.ravel()+height*profile.ravel()
    idx=np.arange(ns*nu).reshape(ns,nu)
    foot=np.zeros(ns*nu,bool)
    foot[idx[0,:]]=foot[idx[-1,:]]=foot[idx[:,0]]=foot[idx[:,-1]]=True
    V[foot,1]=base[foot]-0.001
    F=[]
    for i in range(ns-1):
        for j in range(nu-1):
            a,b,c,d=idx[i,j],idx[i+1,j],idx[i+1,j+1],idx[i,j+1]
            F.extend(((a,c,b),(a,d,c)))
    F=np.asarray(F,dtype=np.int64)
    if cutters:
        V,F,foot=clip_exact(m,V,F,foot,cutters)
    m._caps.append({'V':V,'F':F,'role':np.where(foot,3,0),'anchor':np.full(len(V),-1),'foot':foot})
    sel=np.isin(m.TID,tt)&m.valid & (m.Zall<=m.Z+0.002)
    m._sel|=sel; m._claimed|=sel
    return V,F


def clip_exact(m,V,F,foot,parts):
    """Cut the actual, potentially warped picket solids out of a coping top."""
    import bpy, bmesh
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    me=bpy.data.meshes.new('planken_snow_cut')
    me.from_pydata(V.tolist(),[],F.tolist()); me.update()
    ob=bpy.data.objects.new('planken_snow_cut',me); bpy.context.scene.collection.objects.link(ob)
    cm=bpy.data.meshes.new('planken_uprights')
    tris=m.T[np.isin(m.part_t,parts)]
    cm.from_pydata(m.V.tolist(),[],tris.tolist()); cm.update()
    bm=bmesh.new(); bm.from_mesh(cm)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
    bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(cm); bm.free()
    cut=bpy.data.objects.new('planken_uprights',cm); bpy.context.scene.collection.objects.link(cut)
    mod=ob.modifiers.new('actual wood','BOOLEAN'); mod.operation='DIFFERENCE'; mod.solver='EXACT'; mod.object=cut
    deps=bpy.context.evaluated_depsgraph_get(); ev=ob.evaluated_get(deps); mesh=ev.to_mesh()
    # Exact cuts can leave micron-sized edges where a picket meets a grid
    # diagonal. Weld these and improve triangle aspect before exporting.
    bm=bmesh.new(); bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=0.00002)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=0.00002)
    bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='BEAUTY')
    bmesh.ops.beautify_fill(bm,faces=list(bm.faces),edges=list(bm.edges),use_restrict_tag=False,method='AREA')
    bm.to_mesh(mesh); bm.free()
    mesh.calc_loop_triangles()
    Vn=np.array([v.co[:] for v in mesh.vertices]); Fn=np.array([t.vertices[:] for t in mesh.loop_triangles],dtype=np.int64)
    Fn=gentle_diagonals(Vn,Fn)
    # Original seated boundary and new exact intersections with wood are feet.
    old=V[foot]; fn=np.zeros(len(Vn),bool)
    for i,p in enumerate(Vn):
        fn[i]=bool(np.min(np.linalg.norm(old-p,axis=1))<2e-6 or m.bvh_all.find_nearest(Vector(tuple(p)),0.001)[0] is not None)
    ev.to_mesh_clear(); bpy.data.objects.remove(ob,do_unlink=True); bpy.data.objects.remove(cut,do_unlink=True)
    bpy.data.meshes.remove(me); bpy.data.meshes.remove(cm)
    return Vn,Fn,fn


def gentle_diagonals(V,F):
    """Select the gentler diagonal of non-planar quads after an exact cut.
    Geometry, boundary positions and support contact are unchanged.
    """
    from collections import defaultdict
    role=np.zeros(len(V),int)
    for _ in range(3):
        score=H.fold_score(V,F,role)
        if score<=0: break
        by=defaultdict(list)
        for i,f in enumerate(F):
            for a,b in zip(f,np.roll(f,-1)):
                by[tuple(sorted((int(a),int(b))))].append(i)
        changed=False
        for (a,b),fs in by.items():
            if len(fs)!=2: continue
            ia,ib=fs; old=F[[ia,ib]].copy()
            if not all(a in face and b in face for face in old): continue
            c=next((int(i) for i in old[0] if i not in (a,b)),None)
            d=next((int(i) for i in old[1] if i not in (a,b)),None)
            if c is None or d is None or c==d: continue
            n=np.cross(V[old[:,1]]-V[old[:,0]],V[old[:,2]]-V[old[:,0]])
            n/=np.maximum(np.linalg.norm(n,axis=1),1e-15)[:,None]
            if n[:,1].min()<0.75 or n[0]@n[1]>math.cos(math.radians(25)): continue
            nf=np.array([[c,d,a],[d,c,b]],dtype=np.int64)
            nn=np.cross(V[nf[:,1]]-V[nf[:,0]],V[nf[:,2]]-V[nf[:,0]])
            if nn[:,1].sum()<0: nf=nf[:,[0,2,1]]; nn=-nn
            if nn[:,1].min()<=0: continue
            # Reject flips that would create a thin needle.
            lengths=np.stack([np.linalg.norm(V[nf[:,(j+1)%3]]-V[nf[:,j]],axis=1) for j in range(3)],axis=1)
            if np.min(np.linalg.norm(nn,axis=1)/np.maximum(lengths.max(1)**2,1e-15))<0.025: continue
            F[[ia,ib]]=nf
            new=H.fold_score(V,F,role)
            if new<score-1e-6:
                score=new; changed=True
            else: F[[ia,ib]]=old
        if not changed: break
    return F

