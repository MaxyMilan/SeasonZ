"""Volumetric snow experiments for recipes (method='addon').

build(m, variant) is A6: original addon surface kernels up to 6 cm base depth,
vertical field extrusion, and one soft support floor. Shared global lattice
edges are welded exactly. A2, A3 and A5 remain available as build_a2,
build_a3 and build_a5; no old clipping cleanup is used by A6.

This module is an integration candidate. Check m.addon_stats and the volume
agent report before choosing it for a production recipe. It never installs
an add-on or alters snow_hand / snow_craft.
"""
import math,time
import numpy as np
from mathutils import Vector
import snow_hand as H
import snow_volume as G

SEED=644
THRESHOLD=1.3
STIFFNESS=.75


def budget(area):
    """LOD0 triangles from the snow area (m2): about 1500 per m2 on props (a fence rail with a few hundred, a bench
    seat about 1500), at most 5800; larger caps 8000/10000/12000 up to 40/120/more m2"""
    if area<=12: return int(np.clip(1500*area,400,5800))
    return 8000 if area<=40 else 10000 if area<=120 else 12000


def _surface(m):
    # Pre-emission sky mask. m.Z is the uppermost reachable surface, so floors
    # and furniture inside a closed house never contribute particles.
    mask=m.tops(4,slope=False)&(m.NYF>=.5)
    z=np.nan_to_num(m.Z,nan=-1e6)
    lx=mask[:,:-1]&mask[:,1:]&(np.abs(np.diff(z,axis=1))<=1.8*m.g+.002)
    lz=mask[:-1,:]&mask[1:,:]&(np.abs(np.diff(z,axis=0))<=1.8*m.g+.002)
    labels,n=H.label(mask,lx,lz)
    excluded=0
    for lab in range(n):
        part=labels==lab
        area=float(np.sum(m.g*m.g/np.maximum(m.NYF[part],.5)))
        width=2*float(H.distance(part,4).max())*m.g
        if area<.01 or width<.04-1e-8:
            excluded+=int(part.sum()); mask[part]=False
    lx&=mask[:,:-1]&mask[:,1:]; lz&=mask[:-1,:]&mask[1:,:]
    edge=mask.copy()
    interior=np.zeros_like(mask)
    interior[1:-1,1:-1]=(mask[1:-1,1:-1]&lx[1:-1,:-1]&lx[1:-1,1:]&lz[:-1,1:-1]&lz[1:,1:-1])
    edge &= ~interior
    distance=H.distance(interior,40)*m.g
    return mask,lx,lz,edge,distance,excluded


def _relax(A,lx,lz,strength):
    total=np.zeros_like(A); degree=np.zeros_like(A)
    total[:,:-1]+=np.where(lx,A[:,1:],0); degree[:,:-1]+=lx
    total[:,1:]+=np.where(lx,A[:,:-1],0); degree[:,1:]+=lx
    total[:-1]+=np.where(lz,A[1:],0); degree[:-1]+=lz
    total[1:]+=np.where(lz,A[:-1],0); degree[1:]+=lz
    return A+strength*np.where(degree>0,total/np.maximum(degree,1)-A,0)


def _field(m,mask,reference_depth,keep_mesh=False,particle_depth=None):
    """Sum of binned Poisson particles and Blender-style compact cubic kernels.

    K(r)=stiffness*(1-r^2/R^2)^3 for r<R, otherwise zero. R=.54*height
    is the effective world radius of the supplied hair/metaball setup (4x
    hair instance factor, 1.5 element radius, .09 object scale).
    Binning conserves particle mass. The same seed and realization are reused
    for every depth; output growth is a constrained vertical deformation.
    """
    g=m.g; gy=min(g,(particle_depth or reference_depth)/3)
    height=reference_depth/.331; radius=.54*height
    halo=int(math.ceil(radius/g))+2; core=64
    rng=np.random.default_rng(SEED)
    particle_height=(particle_depth or reference_depth)/.331
    mean=np.where(mask,50/(particle_height*particle_height)*g*g/np.maximum(m.NYF,.5),0)
    counts=rng.poisson(mean).astype(np.float32)
    out=np.full(mask.shape,np.nan)
    kernel_cache={}; mesh_chunks=[]; triangles=0; blocks=0
    for j0 in range(0,m.nv,core):
        for i0 in range(0,m.nu,core):
            j1=min(j0+core,m.nv); i1=min(i0+core,m.nu)
            if not mask[j0:j1,i0:i1].any(): continue
            js0=max(0,j0-halo); js1=min(m.nv,j1+halo)
            is0=max(0,i0-halo); is1=min(m.nu,i1+halo)
            sj,si=np.nonzero(counts[js0:js1,is0:is1]>0)
            if not len(si): continue
            sj+=js0; si+=is0
            y=m.Z[sj,si]
            y0=math.floor((float(y.min())-radius-2*gy)/gy)*gy
            ny=int(math.ceil((float(y.max())+radius+2*gy-y0)/gy))+1
            shape=(i1-i0+2*halo,ny,j1-j0+2*halo)
            fftshape=tuple(1<<(int(n)-1).bit_length() for n in shape)
            density=np.zeros(fftshape,np.float32)
            xx=si-(i0-halo); zz=sj-(j0-halo)
            yf=(y-y0)/gy; yy=np.floor(yf).astype(int); f=yf-yy
            np.add.at(density,(xx,yy,zz),counts[sj,si]*(1-f))
            np.add.at(density,(xx,yy+1,zz),counts[sj,si]*f)
            if fftshape not in kernel_cache:
                n=int(math.ceil(radius/g))
                q=np.arange(-n,n+1)
                qy=np.arange(-int(math.ceil(radius/gy)),int(math.ceil(radius/gy))+1)
                r2=(q[:,None,None]**2*g*g+qy[None,:,None]**2*gy*gy+q[None,None,:]**2*g*g)/(radius*radius)
                ker=STIFFNESS*np.maximum(1-r2,0)**3
                padded=np.zeros(fftshape,np.float32)
                padded[np.ix_(q%fftshape[0],qy%fftshape[1],q%fftshape[2])]=ker
                kernel_cache[fftshape]=np.fft.rfftn(padded)
            field=np.fft.irfftn(np.fft.rfftn(density)*kernel_cache[fftshape],s=fftshape).astype(np.float32)-THRESHOLD
            field=field[:shape[0],:shape[1],:shape[2]]
            # One extra grid point joins each block. Extraction remains in
            # ordinary world coordinates, including steep/uneven supports.
            cut=field[halo:halo+i1-i0+1,:,halo:halo+j1-j0+1]
            origin=np.array((m.u0+i0*g,y0,m.v0+j0*g))
            vv,ff=G._march(cut,origin,np.array((g,gy,g)))
            triangles+=len(ff); blocks+=1
            if keep_mesh and len(ff): mesh_chunks.append((vv,ff))
            slab=cut[:i1-i0,:,:j1-j0]
            present=np.any(slab>0,axis=1)
            iy=slab.shape[1]-1-np.argmax(slab[:,::-1,:]>0,axis=1)
            ix,iz=np.indices(iy.shape)
            ya=slab[ix,iy,iz]; yb=slab[ix,np.minimum(iy+1,slab.shape[1]-1),iz]
            top=y0+(iy+ya/np.maximum(ya-yb,1e-12))*gy
            out[j0:j1,i0:i1]=np.where(present,top,np.nan).T
    return out,dict(seed=SEED,reference_depth=reference_depth,reference_height=height,
                    particle_count=int(counts.sum()),particle_depth=particle_depth or reference_depth,
                    represented_emitter_area_m2=float((mean*particle_height*particle_height/50).sum()),
                    grid_pitch=g,vertical_grid_pitch=gy,blocks=blocks,extracted_triangles=triangles),H.join(mesh_chunks)


def reference_mesh(m,depth=None):
    mask,*_= _surface(m)
    top,stats,mesh=_field(m,mask,depth or m.thick(4),keep_mesh=True)
    return mesh,stats


def _source_points(m,xy):
    top=float(m.V[:,1].max()+5); down=Vector((0,-1,0))
    y=np.zeros(len(xy)); ny=np.zeros(len(xy)); part=np.full(len(xy),-1,int)
    for k,(x,z) in enumerate(xy):
        hit,n,tid,_=m.bvh_all.ray_cast(Vector((float(x),top,float(z))),down)
        if hit is not None:
            y[k]=hit.y; ny[k]=abs(n.y); part[k]=m.part_t[m._all_t[tid]]
    return y,ny,part


def _rowkey(A):
    """one int64 per row of small non-negative ints (fast 1-d unique instead of np.unique(axis=0)); None if it overflows"""
    A=np.asarray(A,np.int64); base=int(A.max(initial=0))+1
    if base**A.shape[1]>=2**62: return None
    k=np.zeros(len(A),np.int64)
    for j in range(A.shape[1]): k=k*base+A[:,j]
    return k


def _edges(F):
    """the unique undirected edges of a triangle list"""
    e=np.sort(np.concatenate((F[:,[0,1]],F[:,[1,2]],F[:,[2,0]])),axis=1)
    k=_rowkey(e)
    if k is None: return np.unique(e,axis=0,return_counts=True)
    u,i,c=np.unique(k,return_index=True,return_counts=True)
    return e[i],c


def _boundary(F,n):
    e,c=_edges(F)
    out=np.zeros(n,bool); out[e[c==1].ravel()]=True
    return out


def _prepare(m):
    start=time.perf_counter()
    M,lx,lz,edge,D,excluded=_surface(m)
    if not M.any(): return None
    ref=m.thick(4)
    top,stats,_=_field(m,M,ref)
    field_s=time.perf_counter()-start
    Z=np.nan_to_num(m.Z,nan=0.)
    T=np.where(M,np.where(np.isfinite(top),top,Z+ref),0.)
    # Taubin pair preserves broad shapes; constraints are applied afterwards.
    for _ in range(3):
        T=_relax(T,lx,lz,.5); T=_relax(T,lx,lz,-.53)
    noise=np.where(M,np.clip((T-Z)/ref,.85,1.15),1.)
    slopes=np.clip((m.NYF-.5)/(math.cos(math.radians(35))-.5),0,1)
    slopes=slopes*slopes*(3-2*slopes)
    d7=m.thick(7)
    # The 6 cm limit is an outward cornice limit, not a limit on the distance
    # over which a cap rounds inward onto its support.
    rim=max(2*m.g,min(1.3*d7,.35))
    taper=np.sqrt(np.maximum(0,1-np.maximum(0,1-D/rim)**2))
    h7=np.minimum(d7*noise*slopes*taper,1.2*D)
    h7=np.where(edge,.0025,np.maximum(h7,.006))
    jj,ii=np.indices(M.shape)
    gridV=np.column_stack((m.u0+ii.ravel()*m.g,(Z+h7).ravel(),m.v0+jj.ravel()*m.g))
    ids=np.arange(M.size).reshape(M.shape)
    a=ids[:-1,:-1]; b=ids[1:,:-1]; c=ids[1:,1:]; d=ids[:-1,1:]
    A=np.stack((a,b,c),axis=-1).reshape(-1,3); B=np.stack((a,c,d),axis=-1).reshape(-1,3)
    F=np.vstack((A,B)); selected=M.ravel()[F].all(1)
    parts=m.PART.ravel()[F]; z=Z.ravel()[F]
    selected&=np.ptp(z,axis=1)<=2.55*m.g+.002
    V,F=G._compact(gridV,F[selected])
    area=float(np.sum(m.g*m.g/np.maximum(m.NYF[M],.5)))
    cap_budget=budget(area)
    if len(F)>cap_budget: V,F=G._decimate(V,F,cap_budget)
    source_y,ny,part=_source_points(m,V[:,[0,2]])
    valid=(part>=0)&(ny>=.5)&(source_y>=m.ground+.25)
    F=F[np.all(valid[F],axis=1)]
    # Test face interiors and edge midpoints for unsupported bridges.
    if len(F):
        probes=np.concatenate((V[F].mean(1),.5*(V[F[:,0]]+V[F[:,1]]),
                              .5*(V[F[:,1]]+V[F[:,2]]),.5*(V[F[:,2]]+V[F[:,0]])))
        _,pn,pp=_source_points(m,probes[:,[0,2]])
        allowed=(pp>=0)&(pn>=.5)
        F=F[allowed.reshape(4,-1).all(0)]
    # A fixed xy winding and topology is essential for monotone interpolation.
    n=np.cross(V[F[:,1]]-V[F[:,0]],V[F[:,2]]-V[F[:,0]])
    F=F[n[:,1]>1e-12]
    V,F=G._compact(V,F)
    source_y,ny,part=_source_points(m,V[:,[0,2]])
    u,j=m.ij(V[:,0],V[:,2])
    N=H.bilinear(noise,u,j); W=H.bilinear(D,u,j)
    factor=np.clip((ny-.5)/(math.cos(math.radians(35))-.5),0,1)
    factor=factor*factor*(3-2*factor)
    taper=np.sqrt(np.maximum(0,1-np.maximum(0,1-W/rim)**2))
    foot=_boundary(F,len(V))
    heights=[]
    for k in range(1,8):
        dep=m.thick(k)
        h=np.minimum(dep*N*factor*taper,1.2*W)
        h=np.where(foot,.0025,np.maximum(h,.006))
        heights.append(h)
    heights=np.maximum.accumulate(np.array(heights),axis=0)
    # Smooth the final sampled envelope as well as the dense field. Reusing
    # only the field smoothing after decimation left tiny sharp height changes
    # on short edges. Positive averaging plus a final cumulative maximum
    # preserves the depth order; boundary contact remains fixed.
    E=np.unique(np.sort(np.concatenate((F[:,[0,1]],F[:,[1,2]],F[:,[2,0]])),axis=1),axis=0)
    degree=np.bincount(E.ravel(),minlength=len(V))
    for k in range(7):
        Y=source_y+heights[k]
        limit=np.maximum(.006,np.minimum(1.15*m.thick(k+1)*factor,1.2*W))
        for _ in range(2):
            acc=np.zeros(len(V))
            np.add.at(acc,E[:,0],Y[E[:,1]]); np.add.at(acc,E[:,1],Y[E[:,0]])
            new=Y+.25*(acc/np.maximum(degree,1)-Y)
            Y=np.where(foot,source_y+.0025,np.clip(new,source_y+.006,source_y+limit))
        heights[k]=Y-source_y
    heights=np.maximum.accumulate(heights,axis=0)
    minimum=np.where(foot,.0025,np.maximum(.006,.85*heights[0]))
    V[:,1]=source_y+minimum
    # Bounded repair only. In particular, never lift a lower log cap metres
    # onto an occluding log. Such faces are rejected, not stretched.
    corrected,repair=G._lift_clear(m,V,F,.0025,max_passes=3)
    delta=corrected[:,1]-V[:,1]
    rejected=delta>.005
    F=F[~np.any(rejected[F],axis=1)]
    safe_minimum=np.where(rejected,minimum,corrected[:,1]-source_y)
    heights=np.maximum(heights,safe_minimum[None])
    # Remove residual collisions on a shared face set across every depth.
    collision_faces=set()
    for k in range(7):
        vv=V.copy(); vv[:,1]=source_y+heights[k]
        collision_faces.update(i for i,j in G.intersections(m,vv,F))
    removed=len(collision_faces)
    if removed:
        keep=np.ones(len(F),bool); keep[list(collision_faces)]=False; F=F[keep]
    # Decimation and clipping can split a valid input surface into crumbs.
    # Reapply the area/width/support rules to the final connected components.
    uf=H.UF(len(V))
    for a,b,c in F.tolist(): uf.union(a,b); uf.union(b,c)
    roots=np.array([uf.find(int(f[0])) for f in F])
    retain=np.zeros(len(F),bool); pruned=0
    for root in np.unique(roots):
        face_ids=np.flatnonzero(roots==root); pts=np.unique(F[face_ids])
        q=V[pts][:,[0,2]]; q=q-q.mean(0)
        _,_,axes=np.linalg.svd(q,full_matrices=False)
        width=float(np.ptp(q@axes.T,axis=0).min()) if len(pts)>2 else 0.
        tri=V[F[face_ids]]
        area=float(np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1).sum()*.5)
        touching=any(m.bvh_all.find_nearest(Vector(V[i]),.005)[0] is not None for i in pts)
        thick=bool(np.any(heights[-1,pts]>=.006))
        if area>=.01 and width>=.04 and touching and thick: retain[face_ids]=True
        else: pruned+=1
    F=F[retain]
    used,inv=np.unique(F,return_inverse=True)
    V=V[used]; F=inv.reshape(-1,3); source_y=source_y[used]; heights=heights[:,used]
    safe_minimum=safe_minimum[used]; foot=foot[used]
    stats.update(area_m2=area,budget=cap_budget,triangles=len(F),excluded_cells=excluded,
                 field_s=field_s,prepare_s=time.perf_counter()-start,
                 rejected_large_lift_vertices=int(rejected.sum()),deleted_collision_faces=removed,pruned_components=pruned,
                 fixed_topology=True,reference_variant=4,repair=repair)
    return dict(V=V,F=F,source_y=source_y,heights=heights,selected=M,distance=D,stats=stats,
                safe_minimum=safe_minimum,foot=foot,nested_fields={})


def build_a2(m,variant):
    """Recipe entry point. Model.reset() may run between calls; our cache survives."""
    if variant not in range(1,8): raise ValueError('variant must be 1..7')
    start=time.perf_counter(); cold=not hasattr(m,'_snow_addon_cache')
    if cold: m._snow_addon_cache=_prepare(m)
    data=m._snow_addon_cache
    if data is None:
        m.addon_stats=dict(empty=True,seconds=time.perf_counter()-start)
        return None
    V=data['V'].copy(); F=data['F'].copy()
    depth=m.thick(variant)
    # Actual nested particle fields: keep the exact same v1 Poisson counts,
    # stiffness and positions; only grow each kernel radius. Their sum is
    # pointwise nondecreasing. A shallow continuous foundation fills particle
    # pinholes, then the physical cap envelope limits excessive accumulation.
    if depth not in data['nested_fields']:
        top,nested_stats,_=_field(m,data['selected'],depth,particle_depth=m.thick(1))
        data['nested_fields'][depth]=(top,nested_stats)
    top,nested_stats=data['nested_fields'][depth]
    u,j=m.ij(V[:,0],V[:,2])
    raw=np.maximum(0,np.nan_to_num(top-m.Z,nan=0.))
    raw_h=H.bilinear(raw,u,j)
    envelope=data['heights'][variant-1]
    foundation=np.where(data['foot'],.0025,np.maximum(.006,.85*envelope))
    final_h=np.maximum(data['safe_minimum'],np.minimum(envelope,np.maximum(foundation,raw_h)))
    V[:,1]=data['source_y']+final_h
    m._sel|=data['selected']; m._claimed|=data['selected']
    m._soft|=data['selected']&(m.NYF<math.cos(math.radians(35)))
    result=G._register(m,V,F,.0025,m.g)
    m.addon_stats=dict(data['stats'],variant=variant,depth=m.thick(variant),nested_field=nested_stats,
                       cold=cold,seconds=time.perf_counter()-start,
                       intersections=len(G.intersections(m,*result)))
    return result


# ---------------- A3: retain the 3D surface ----------------
def _smin(a,b,k):
    """Polynomial smooth intersection for fields positive inside."""
    k=np.maximum(k,1e-8)
    h=np.maximum(k-np.abs(a-b),0)/k
    return np.minimum(a,b)-.25*k*h*h


def _a3_lattice(m):
    M,_,_,_,D,excluded=_surface(m)
    g=m.g; gy=min(g,m.thick(1)/4)
    maxd=m.thick(7); maxr=.54*(maxd/.331); ro=min(.5*maxd,.06)
    pad=int(math.ceil((maxr+ro+.6*maxd)/g))+5
    M=np.pad(M,pad)
    Z=np.pad(np.nan_to_num(m.Z,nan=-1e6),pad,constant_values=-1e6)
    NY=np.pad(m.NYF,pad)
    W=np.pad(2*(D+.5*g),pad)
    S=np.where(M,Z,-np.inf); support_dist=np.where(M,0.,np.inf)
    carried_w=W.copy(); carried_ny=NY.copy()
    rr=int(math.ceil(ro/g))+1
    # Freeze ownership at the largest collar reach. A cell becomes available
    # only when the current reach includes that owner, so its support height
    # never jumps up when a deeper variant admits another nearby surface.
    for dj in range(-rr,rr+1):
        for di in range(-rr,rr+1):
            ds=max(0.,math.hypot(dj,di)*g-.5*g)
            if ds>ro or (dj==0 and di==0): continue
            cand=H.sh(np.where(M,Z,-np.inf),dj,di,-np.inf)
            use=(~M)&((cand>S+1e-9)|((np.abs(cand-S)<1e-9)&(ds<support_dist)))
            S[use]=cand[use]; support_dist[use]=ds
            cw=H.sh(W,dj,di,0); cn=H.sh(NY,dj,di,0)
            carried_w[use]=cw[use]; carried_ny[use]=cn[use]
    rng=np.random.default_rng(SEED)
    ph=m.thick(1)/.331
    mean=np.where(M,50/(ph*ph)*g*g/np.maximum(NY,.5),0)
    counts=rng.poisson(mean).astype(np.float32)
    u0=m.u0-pad*g; v0=m.v0-pad*g
    x=u0+np.arange(M.shape[1])*g; z=v0+np.arange(M.shape[0])*g
    phase=np.random.default_rng(SEED+1).uniform(0,2*np.pi,3)
    noise=(.45*np.sin(7*x[None]+phase[0])*np.cos(9*z[:,None])+
           .35*np.sin(13*x[None]-5*z[:,None]+phase[1])+
           .2*np.cos(17*z[:,None]+3*x[None]+phase[2]))
    y0=math.floor((float(Z[M].min())-maxr-.6*maxd-4*gy)/gy)*gy
    y1=math.ceil((float(Z[M].max())+maxr+.6*maxd+4*gy)/gy)*gy
    active=H.dilate(M,int(math.ceil(maxr/g))+2)
    return dict(M=M,Z=Z,NY=NY,S=S,W=carried_w,normal=carried_ny,dist=support_dist,
                noise=noise,counts=counts,u0=u0,v0=v0,y0=y0,y1=y1,g=g,gy=gy,
                maxr=maxr,active=active,pad=pad,excluded=excluded,
                source_selected=M[pad:-pad,pad:-pad])


def _a3_weld(V,F,eps,edge_keys=None):
    if edge_keys is not None:
        # Weld by the exact global lattice edge, not by Euclidean proximity.
        # Distance welding merged distinct sides of very thin contact volumes.
        k=_rowkey(edge_keys)
        _,inv=np.unique(edge_keys,axis=0,return_inverse=True) if k is None else np.unique(k,return_inverse=True)
        inv=inv.ravel(); count=np.bincount(inv)
        vv=np.column_stack([np.bincount(inv,weights=V[:,i],minlength=len(count)) for i in range(3)])/count[:,None]
        ff=inv[F]
        good=(ff[:,0]!=ff[:,1])&(ff[:,1]!=ff[:,2])&(ff[:,2]!=ff[:,0])
        ff=ff[good]; k=_rowkey(np.sort(ff,axis=1))
        _,ind=np.unique(np.sort(ff,axis=1),axis=0,return_index=True) if k is None else np.unique(k,return_index=True)
        return G._compact(vv,ff[np.sort(ind)])
    import bmesh
    import bpy
    me=bpy.data.meshes.new('a3_weld')
    me.from_pydata(V.tolist(),[],F.tolist())
    bm=bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=eps)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-9)
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(me); bm.free(); me.calc_loop_triangles()
    V=np.array([v.co[:] for v in me.vertices])
    F=np.array([t.vertices[:] for t in me.loop_triangles],dtype=np.int64)
    bpy.data.meshes.remove(me)
    # Welding can leave duplicate coplanar triangles where the iso-level hits
    # a lattice node exactly. Keep one with its original winding.
    _,ind=np.unique(np.sort(F,axis=1),axis=0,return_index=True)
    return G._compact(V,F[np.sort(ind)])


def _a3_topology(V,F,lat,core):
    e=np.sort(np.concatenate((F[:,[0,1]],F[:,[1,2]],F[:,[2,0]])),axis=1)
    e,c=np.unique(e,axis=0,return_counts=True)
    bd=e[c==1]
    mid=V[bd].mean(1) if len(bd) else np.empty((0,3))
    px=(mid[:,0]-lat['u0'])/(core*lat['g'])
    pz=(mid[:,2]-lat['v0'])/(core*lat['g'])
    seam=(np.abs(px-np.round(px))<1e-4)|(np.abs(pz-np.round(pz))<1e-4)
    return dict(boundary_edges=int(len(bd)),nonmanifold_edges=int((c>2).sum()),
                seam_boundary_edges=int(seam.sum()))


def _a3_block(m,lat,tile,variants):
    g,gy=lat['g'],lat['gy']; core=32
    j0,j1,i0,i1=tile
    halo=int(math.ceil(lat['maxr']/g))+3
    js0=max(0,j0-halo); js1=min(lat['M'].shape[0],j1+halo+1)
    is0=max(0,i0-halo); is1=min(lat['M'].shape[1],i1+halo+1)
    jj,ii=np.nonzero(lat['counts'][js0:js1,is0:is1])
    if not len(jj): return None
    jj+=js0; ii+=is0; sy=lat['Z'][jj,ii]
    # All y limits are integer indices on the one global lattice.
    iy0=max(0,int(math.floor((float(sy.min())-lat['maxr']-3*gy-lat['y0'])/gy)))
    iy1=min(int(round((lat['y1']-lat['y0'])/gy)),int(math.ceil((float(sy.max())+lat['maxr']+3*gy-lat['y0'])/gy)))
    ny=iy1-iy0+1; y0=lat['y0']+iy0*gy
    nx=i1-i0+1+2*halo; nz=j1-j0+1+2*halo
    fs=tuple(1<<(int(n)-1).bit_length() for n in (nx,ny,nz))
    density=np.zeros(fs,np.float32)
    yi=(sy-y0)/gy; yb=np.floor(yi).astype(int); yf=yi-yb
    xx=ii-(i0-halo); zz=jj-(j0-halo)
    np.add.at(density,(xx,yb,zz),lat['counts'][jj,ii]*(1-yf))
    np.add.at(density,(xx,yb+1,zz),lat['counts'][jj,ii]*yf)
    transform=np.fft.rfftn(density); del density
    mask=lat['M'][j0:j1+1,i0:i1+1].T
    S=lat['S'][j0:j1+1,i0:i1+1].T
    finite=np.isfinite(S); S=np.where(finite,S,-1e4)
    W=lat['W'][j0:j1+1,i0:i1+1].T
    dist=lat['dist'][j0:j1+1,i0:i1+1].T
    noise=lat['noise'][j0:j1+1,i0:i1+1].T
    ny_support=lat['normal'][j0:j1+1,i0:i1+1].T
    slope=np.clip((ny_support-.5)/(math.cos(math.radians(35))-.5),0,1)
    slope=slope*slope*(3-2*slope)
    yy=y0+np.arange(ny)*gy
    previous=None; last_depth=None; result={}; positive_on_y_boundary=0
    for v in range(1,max(variants)+1):
        d=m.thick(v); radius=.54*(d/.331)
        if d!=last_depth:
            q=np.arange(-int(math.ceil(radius/g)),int(math.ceil(radius/g))+1)
            qy=np.arange(-int(math.ceil(radius/gy)),int(math.ceil(radius/gy))+1)
            rr=(q[:,None,None]**2*g*g+qy[None,:,None]**2*gy*gy+q[None,None,:]**2*g*g)/(radius*radius)
            kernel=STIFFNESS*np.maximum(1-rr,0)**3
            kp=np.zeros(fs,np.float32)
            kp[np.ix_(q%fs[0],qy%fs[1],q%fs[2])]=kernel
            dense=np.fft.irfftn(transform*np.fft.rfftn(kp),s=fs).astype(np.float32)-THRESHOLD
            # Derivatives see one halo node past every core boundary.
            extended=dense[halo-1:halo+i1-i0+2,:ny,halo-1:halo+j1-j0+2]
            dx,dy,dz=np.gradient(extended,g,gy,g)
            gradient=np.sqrt(dx*dx+dy*dy+dz*dz)[1:-1,:,1:-1]
            raw=extended[1:-1,:,1:-1].copy()
            fdist=np.clip(raw/np.maximum(gradient,.01*THRESHOLD/radius),-radius,radius)
            del dense,extended,dx,dy,dz,kp
            last_depth=d
        reach=min(.5*d,.06)
        allowed=finite&(mask|(dist<=reach+1e-9))
        droop=np.where(mask,.003,.5*d*np.maximum(0,1-dist/max(reach,1e-6)))
        # A3's envelope follows the requested formula. Applying the previous
        # per-face slope multiplier here introduced bands at source facets.
        # Steep faces are excluded before emission by the sky mask.
        h=np.minimum(d*(1+.15*noise),.6*W)
        C=(S+h)[:,None,:]-yy[None,:,None]
        lower=yy[None,:,None]-(S-droop)[:,None,:]
        # Adapt radius only in very thin edge columns so the two opposite
        # support constraints do not annihilate a physically valid thin rim.
        k=np.minimum(.3*d,.75*np.maximum(h+droop,.003))[:,None,:]
        candidate=_smin(_smin(fdist,C,k),lower,k)
        lateral=np.where(mask,1.,reach-dist)[:,None,:]
        candidate=_smin(candidate,lateral,k)
        candidate=np.where(allowed[:,None,:],candidate,-radius)
        # Increasing smoothing radius / distance normalization alone does
        # not prove nesting. Explicit union with the preceding 3D volume
        # gives that guarantee on the fixed lattice, without rewriting y.
        current=candidate if previous is None else np.maximum(previous,candidate)
        previous=current
        if v in variants:
            origin=np.array((lat['u0']+i0*g,y0,lat['v0']+j0*g))
            V,F,edges=G._march(current-3.14159e-7,origin,np.array((g,gy,g)),return_edges=True)
            Vr,Fr,redges=G._march(raw-3.14159e-7,origin,np.array((g,gy,g)),return_edges=True)
            offset=np.array((i0,iy0,j0))
            stride=np.array((int(round((lat['y1']-lat['y0'])/gy))+1,lat['M'].shape[0]))
            def keys(e):
                e=e+offset
                return (e[:,:,0]*stride[0]+e[:,:,1])*stride[1]+e[:,:,2]
            positive_on_y_boundary+=int((current[:,0,:]>0).sum()+(current[:,-1,:]>0).sum())
            result[v]=(V,F,keys(edges),Vr,Fr,keys(redges))
    return result,positive_on_y_boundary


def _a3_prune(m,V,F):
    if not len(F): return V,F,0
    uf=H.UF(len(V))
    for a,b,c in F.tolist(): uf.union(a,b); uf.union(b,c)
    roots=np.array([uf.find(int(t[0])) for t in F]); keep=np.zeros(len(F),bool); removed=0
    for root in np.unique(roots):
        ids=np.flatnonzero(roots==root); pts=np.unique(F[ids]); tri=V[F[ids]]
        area=float(np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1).sum()*.5)
        xy=V[pts][:,[0,2]]; xy-=xy.mean(0)
        _,_,ax=np.linalg.svd(xy,full_matrices=False)
        width=float(np.ptp(xy@ax.T,axis=0).min()) if len(pts)>2 else 0.
        contact=any(m.bvh_all.find_nearest(Vector(V[i]),.008)[0] is not None for i in pts)
        if area>=.01 and width>=.04 and contact: keep[ids]=True
        else: removed+=1
    return (*G._compact(V,F[keep]),removed)


def _a3_taubin(V,F,passes=3):
    fixed=_boundary(F,len(V)); original=V.copy(); n=len(V)
    e,_=_edges(F)
    degree=np.bincount(e.ravel(),minlength=n)
    a=np.concatenate((e[:,0],e[:,1])); b=np.concatenate((e[:,1],e[:,0]))
    for _ in range(passes):
        for strength in (.5,-.53):
            total=np.column_stack([np.bincount(a,weights=V[b,i],minlength=n) for i in range(3)])
            V+=strength*(total/np.maximum(degree[:,None],1)-V)
            V[fixed]=original[fixed]
    return V


def _a3_collision_faces(m,V,F):
    pairs=G.intersections(m,V,F)
    if not pairs: return [],0
    y,_,part=_source_points(m,V[:,[0,2]])
    rel=np.where(part>=0,V[:,1]-y,1.)
    bd=_boundary(F,len(V))
    near=np.zeros(len(V),bool)
    for i in np.unique(F[[a for a,b in pairs]]):
        near[i]=m.bvh_all.find_nearest(Vector(V[i]),.006)[0] is not None
    bad=[]; foot_pairs=0
    for a,b in pairs:
        ids=F[a]
        foot=(np.any(bd[ids]&near[ids]) and rel[ids].min()>=-.0035)
        if foot: foot_pairs+=1
        else: bad.append(a)
    return sorted(set(bad)),foot_pairs


def prepare_a3(m,variants=(1,4,7),workers=4):
    """Prepare only the requested extraction stages on one shared lattice."""
    from concurrent.futures import ThreadPoolExecutor
    start=time.perf_counter(); lat=_a3_lattice(m); core=32
    tiles=[]
    nz,nx=lat['M'].shape
    for j0 in range(0,nz-1,core):
        for i0 in range(0,nx-1,core):
            j1=min(j0+core,nz-1); i1=min(i0+core,nx-1)
            if lat['active'][j0:j1+1,i0:i1+1].any(): tiles.append((j0,j1,i0,i1))
    chunks={v:[] for v in variants}; raw_chunks={v:[] for v in variants}; cropped=0
    edges={v:[] for v in variants}; rawedges={v:[] for v in variants}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for result in pool.map(lambda t:_a3_block(m,lat,t,variants),tiles):
            if result is None: continue
            data,boundary=result; cropped+=boundary
            for v,(V,F,E,Vr,Fr,Er) in data.items():
                if len(F): chunks[v].append((V,F)); edges[v].append(E)
                if len(Fr): raw_chunks[v].append((Vr,Fr)); rawedges[v].append(Er)
    field_seconds=time.perf_counter()-start
    cache={}
    for v in variants:
        t=time.perf_counter(); mesh=H.join(chunks[v]); rawmesh=H.join(raw_chunks[v])
        if mesh is None:
            cache[v]=dict(mesh=None,stats=dict(empty=True)); continue
        V,F=_a3_weld(*mesh,max(2e-5,lat['g']*.003),edge_keys=np.vstack(edges[v]))
        rawmesh=_a3_weld(*rawmesh,max(2e-5,lat['g']*.003),edge_keys=np.vstack(rawedges[v]))
        topology=_a3_topology(V,F,lat,core); rawtopology=_a3_topology(*rawmesh,lat,core)
        closed_triangles=len(F)
        y,_,part=_source_points(m,V[:,[0,2]])
        rel=np.where(part>=0,V[:,1]-y,1.)
        norm=np.cross(V[F[:,1]]-V[F[:,0]],V[F[:,2]]-V[F[:,0]])
        norm/=np.maximum(np.linalg.norm(norm,axis=1),1e-15)[:,None]
        inside=np.all(rel[F]<-.003,axis=1)
        contact_bottom=(norm[:,1]<.05)&np.all(rel[F]<.003,axis=1)
        V,F=G._compact(V,F[~(inside|contact_bottom)])
        V,F,pruned=_a3_prune(m,V,F)
        if len(F): V=_a3_taubin(V,F)
        pre_budget=len(F); area=float(np.sum(m.g*m.g/np.maximum(m.NYF[lat['source_selected']],.5)))
        limit=budget(area)
        if len(F)>limit: V,F=G._decimate(V,F,limit)
        bad,foot_pairs=_a3_collision_faces(m,V,F)
        # Cut residual intrusions; do not move vertices up to another support.
        if bad:
            keep=np.ones(len(F),bool); keep[bad]=False; V,F=G._compact(V,F[keep])
        V,F,pp=_a3_prune(m,V,F); pruned+=pp
        bad_final,foot_final=_a3_collision_faces(m,V,F)
        stats=dict(method='a3',variant=v,depth=m.thick(v),seed=SEED,
                   particles=int(lat['counts'].sum()),grid_pitch=lat['g'],vertical_grid_pitch=lat['gy'],
                   lattice_origin=[lat['u0'],lat['y0'],lat['v0']],blocks=len(tiles),
                   cropped_positive_y_samples=cropped,closed_topology=topology,raw_topology=rawtopology,
                   closed_triangles=closed_triangles,pre_budget_triangles=pre_budget,triangles=len(F),
                   budget=limit,field_seconds_shared=field_seconds,cleanup_seconds=time.perf_counter()-t,
                   field_seconds_amortized=field_seconds/len(variants),deleted_intrusion_faces=len(bad),
                   nonfoot_intersections=len(bad_final),foot_intersection_pairs=foot_final,
                   pruned_components=pruned,excluded_source_cells=lat['excluded'],nested_field_union=True)
        cache[v]=dict(mesh=(V,F),raw=rawmesh,stats=stats,selected=lat['source_selected'])
    m._snow_a3_cache=cache
    m._snow_a3_total_seconds=time.perf_counter()-start
    return cache


def build_a3(m,variant):
    """A3 recipe entry point; no resampling or vertical rewriting of vertices."""
    if not hasattr(m,'_snow_a3_cache') or variant not in m._snow_a3_cache:
        prepare_a3(m,(variant,))
    data=m._snow_a3_cache[variant]
    m.addon_stats=dict(data['stats'])
    if data['mesh'] is None: return None
    m._sel|=data['selected']; m._claimed|=data['selected']
    out=G._register(m,*data['mesh'],.003,m.g)
    return out


# ---------------- A4: small kernels throughout a target volume ----------------
A4_C=24.
A4_THRESHOLDS={.015:5.794341351653021,.018:5.790033662412078,.025:5.810858150911452,
               .035:5.818861230538518,.045:5.785360745590266,.055:5.7784668458589294,
               .065:5.788944770208743,.05:5.625508528582733,.09:5.742310118986252,
               .11:5.740969698315656,.15:5.7293667303437,.19:5.707672203822953,
               .23:5.6747710055212455}


A4_RMAX=.07     # cap of the volume kernel radius (m)
A7_OVH=0.       # addonfine lip: how far a deep cap rolls out over a free edge, as a share of its depth (0: off)
A7_OVMAX=.07    # ... at most this far (m)
A4_STRAT=False  # stratified particle heights in a column: less shot noise, a smoother deep cap
A7_SKIN=True    # deep caps keep the lifted surface-particle skin on the volume body
A7_TAUBIN=1
A7_COARSE=6     # wide kernels on a lattice of R/A7_COARSE (0: always the fine lattice)
A7_FADE=12.     # the surface-particle density fades out over the last degrees before the slope limit (0: hard)
A7_OVL=0.       # the lip hangs over its carrier's edge by at most this share of the depth (+1 cm); 0: no limit
A7_OVK=.6       # ... rounded by a smooth intersection of this share of that limit
A7_RISE=1.      # outside its carrier the floor rises this many metres per metre: the lip's underside slopes up
                # like a cornice, so a bin or box gets a cap with a short lip, not a mushroom (0: level floor)
A7_LEDGE=True   # a narrow ledge just below a higher top (a box rim, a frame strip) holds no bead of its own
A7_LEDGEW=.05   # ... narrower than this (2 x area / outline)
A7_FLOORBLUR=.25 # outside its carriers the floor is smoothed over this share of the kernel radius (0: nearest carrier)
A7_LIPDROP=.3   # the smoothed floor under a lip stays within this share of the depth (+5 mm) of its carrier; 0: free
A7_FLOORK=.1    # rounding of the cut at the carrier's floor, as a share of the particle depth (0: 5 mm)
# addonfine (Opus, 6 Oct): the user's choice for deep snow is the addonfine look - soft round pillows that roll over
# the edge. That is the surface-particle recipe (a6) at the full depth, kernel ~1.6x the depth; the floors, blocked
# parts, sky test and tip rules keep out its drips, bridges and snow underneath. The a5 volume body remains for
# A7_BASEMAX < depth.
A7_BASEMAX=1.   # surface particles (the addonfine recipe) carry the cap up to this depth; a volume body above it


def _a4_radius(d):
    return float(np.clip(.6*d,.025,A4_RMAX))


def _a4_threshold(d):
    if round(d,6) in A4_THRESHOLDS: return A4_THRESHOLDS[round(d,6)]*A4_C/24.
    # Integral of the cubic kernel over the slab, evaluated at its top.
    # Calibrated values replace this continuum estimate after coupon tests.
    t=min(1.,(d+.005)/_a4_radius(d))
    integral=t-4*t**3/3+6*t**5/5-4*t**7/7+t**9/9
    return A4_C*STIFFNESS*math.pi*.25*integral


A5_HMIN=.006
A5_BEAD=.3      # the lip at the slope limit: a rounded bead of about a third of the kernel radius
A5_STEEP=72.    # no snow beyond this slope
A5_FULL=50.     # full depth up to this slope
A5_STEEP_SMOOTH=60.
A5_FULL_SMOOTH=35.


def _a5_sink(m,base,Z):
    """how deep the particle slab reaches under the support: 40% of the part's own thickness there (the next
    surface straight down), 3..20 mm, so the cap's lip meets the surface steeply (a clean edge line, no lace)
    yet never shows under a plank; 3 mm where nothing lies below (single-sided sheet)"""
    from mathutils import Vector
    out=np.full(base.shape,.003)
    jj,ii=np.nonzero(base)
    down=Vector((0,-1,0)); bvh=m.bvh_all
    for j,i in zip(jj.tolist(),ii.tolist()):
        y=float(Z[j,i])-.002
        hit=bvh.ray_cast(Vector((m.u0+i*m.g,y,m.v0+j*m.g)),down,100.)[0]
        if hit is not None:
            out[j,i]=min(.02,max(.003,.4*(y-hit.y+.002)))
    return out


def _a5_integral(h,R):
    t=np.minimum(1.,(np.asarray(h,float)+.005)/R)
    return t-4*t**3/3+6*t**5/5-4*t**7/7+t**9/9


def _a5_boost(h,d,R):
    """particle weight for a column of thickness h in a cap calibrated for depth d (1 where h >= d)"""
    full=float(_a5_integral(d,R))
    return np.clip(full/np.maximum(_a5_integral(h,R),1e-6),1.,6.).astype(np.float32)


A5_REPOSE=math.tan(math.radians(50.))


def _repose(Z,h,M,g,hmin):
    """the angle of repose: within a support the snow top may not rise more steeply than 50 degrees from a neighbour,
    so a thick cap on a round tank, bale or boulder slopes down to its flanks instead of ending in a step"""
    T=np.where(M,Z+h,np.inf)
    n=int(min(80,math.ceil(float(h.max(initial=0))/(g*A5_REPOSE))+2))
    # only neighbours on the same continuous surface (a step up to another part is not a slope)
    steps=[(dj,di,math.hypot(dj,di)*g*A5_REPOSE,
            M&H.sh(M,dj,di,False)&(np.abs(H.sh(Z,dj,di,1e6)-Z)<=3.5*g*math.hypot(dj,di)))
           for dj in (-1,0,1) for di in (-1,0,1) if dj or di]
    for _ in range(n):
        new=T.copy()
        for dj,di,rise,cont in steps:
            new=np.where(cont,np.minimum(new,H.sh(T,dj,di,np.inf)+rise),new)
        new=np.where(M,np.maximum(new,Z+hmin),np.inf)
        if np.array_equal(new,T): break
        T=new
    return np.where(M,np.minimum(h,np.maximum(T-Z,hmin)),h)


def _sky_open(m,mask):
    """the share of the sky a top sees: nine rays (straight up and eight at 25 degrees); snow falls within about that
    cone, so a board seen only through the slot between two pallet boards, or a log deep in a pile, gets little"""
    if getattr(m,'_sz_sky',None) is not None and m._sz_sky.shape==mask.shape: return m._sz_sky
    a=math.radians(25.); dirs=[Vector((0.,1.,0.))]+[Vector((math.sin(a)*math.cos(t),math.cos(a),math.sin(a)*math.sin(t)))
                                                     for t in np.linspace(0,2*math.pi,8,endpoint=False)]
    out=np.ones(mask.shape); jj,ii=np.nonzero(mask); Z=np.nan_to_num(m.Z,nan=0.); bvh=m.bvh_all
    for j,i in zip(jj.tolist(),ii.tolist()):
        o=Vector((m.u0+i*m.g,float(Z[j,i])+.004,m.v0+j*m.g))
        # (Opus, 6 Oct) straight up blocked: no snow, however much of the slanted sky is open (a bus stop's bench under
        # its roof, the inside of a pipe mouth, a pallet board under the deck)
        out[j,i]=0. if bvh.ray_cast(o,dirs[0],60.)[0] is not None else sum(bvh.ray_cast(o,d,60.)[0] is None for d in dirs)/9.
    m._sz_sky=out
    return out


def _drop_tips(m,mask):
    """tops that hold no cap: less than 45% of the sky open; and small separate tops (under 0.006 m2) unless they are
    nearly flat (under 20 degrees) and at least 3 cm wide - a post top keeps its cap, the slanted point or the 2 cm
    edge of a picket gets no bead"""
    mask=mask&(_sky_open(m,mask)>=.45)
    lx=mask[:,:-1]&mask[:,1:]; lz=mask[:-1,:]&mask[1:,:]
    labels,n=H.label(mask,lx,lz)
    if not n: return mask
    lab=np.where(mask,labels,n)
    cnt=np.bincount(lab.ravel(),minlength=n+1)[:n]
    ny=np.bincount(lab.ravel(),weights=np.where(mask,m.NYF,0).ravel(),minlength=n+1)[:n]
    wide=np.zeros(n+1); np.maximum.at(wide,lab.ravel(),(2*H.distance(mask,6)*m.g).ravel())
    bad=(cnt*m.g*m.g<.006)&((ny/np.maximum(cnt,1)<math.cos(math.radians(20)))|(wide[:n]<.03))
    if A7_LEDGE:
        # a narrow strip (under 5 cm) 1.5-25 cm under a higher top within 8 cm: a box rim, a frame or trim strip just
        # below a lid. It would carry a row of beads under the cap's lip; the cap's own lip covers that edge
        Zm=np.where(mask,np.nan_to_num(m.Z,nan=-1e6),-1e6)
        higher=H.maxf(Zm,max(1,int(math.ceil(.08/m.g))))-Zm
        # the grid links a rim to its lid (one mask region): split it into levels - neighbours are one surface only if
        # their step fits the slope - and measure each level's width as 2 x area / perimeter
        tn=np.sqrt(np.clip(1-m.NYF**2,0,1))/np.maximum(m.NYF,.05)
        Zf=np.nan_to_num(m.Z,nan=-1e6)
        sx=mask[:,:-1]&mask[:,1:]&(np.abs(Zf[:,:-1]-Zf[:,1:])<=m.g*1.5*np.maximum(tn[:,:-1],tn[:,1:])+.008)
        sz=mask[:-1]&mask[1:]&(np.abs(Zf[:-1]-Zf[1:])<=m.g*1.5*np.maximum(tn[:-1],tn[1:])+.008)
        lev,nl=H.label(mask,sx,sz)
        if nl:
            le=np.where(mask,lev,nl); deg=np.zeros(mask.shape)
            deg[:,:-1]+=sx; deg[:,1:]+=sx; deg[:-1]+=sz; deg[1:]+=sz
            c2=np.bincount(le.ravel(),minlength=nl+1)[:nl]
            per=np.bincount(le.ravel(),weights=np.where(mask,4-deg,0).ravel(),minlength=nl+1)[:nl]
            # a ledge runs along a step up: a quarter of its outline or more borders a level 2-25 cm higher (bench
            # slats at different heights are parted by gaps, so they never qualify)
            up=np.zeros(mask.shape)
            cx=mask[:,:-1]&mask[:,1:]&~sx; dx=Zf[:,1:]-Zf[:,:-1]
            up[:,:-1]+=cx&(dx>.02)&(dx<.25); up[:,1:]+=cx&(-dx>.02)&(-dx<.25)
            cz=mask[:-1]&mask[1:]&~sz; dz=Zf[1:]-Zf[:-1]
            up[:-1]+=cz&(dz>.02)&(dz<.25); up[1:]+=cz&(-dz>.02)&(-dz<.25)
            steps=np.bincount(le.ravel(),weights=np.where(mask,up,0).ravel(),minlength=nl+1)[:nl]
            narrow=(2*c2*m.g/np.maximum(per,1)<A7_LEDGEW)&(steps>.25*per)
            mask=mask&~np.r_[narrow,False][le]
        if (getattr(m,'rough',False) or m.cls=='rock') and nl:
            # a small facet low on a rock's flank (one level, under 0.03 m2) with a higher top within 20 cm: it showed
            # as a drip hanging under the main cap. Its share of snow slides into the main cap's lip
            near=H.maxf(Zm,max(1,int(math.ceil(.2/m.g))))
            own=np.full(nl+1,-1e6); np.maximum.at(own,le.ravel(),Zm.ravel())
            hi_=np.full(nl+1,-1e6); np.maximum.at(hi_,le.ravel(),np.where(mask,near,-1e6).ravel())
            mask=mask&~np.r_[(c2*m.g*m.g<.03)&(hi_[:nl]>own[:nl]+.03),False][le]
    return mask&~np.r_[bad,False][lab]


def _a4_close(M,Z,d,g):
    limit=max(.02,.5*d)
    r=max(1,int(math.ceil(limit/(2*g))))
    cand=H.erode(H.dilate(M,r),r)&~M
    linked=np.zeros_like(M)
    zn=np.where(M,Z,np.nan)
    for dj,di in ((0,1),(1,0),(1,1),(1,-1)):
        step=math.hypot(dj,di)*g
        reach=int(math.ceil(limit/step))+1
        a,da=H.nearest_along(zn,dj,di,reach)
        b,db=H.nearest_along(zn,-dj,-di,reach)
        good=cand&np.isfinite(a)&np.isfinite(b)
        good&=(np.abs(a-b)<.5*d)&((da+db-1)*step<limit+1e-9)
        linked|=good
    return M|linked


def _a4_plan(m,calibration=False,seed=SEED):
    g=m.g
    # a5 (Opus): snow holds to 72 degrees on rough surfaces (logs, bales, rock); full depth up to 50
    # smooth made surfaces (a bench back, a sheet roof) shed snow from about 60 degrees
    steep,full=(A5_STEEP,A5_FULL) if getattr(m,'rough',False) or m.cls=='rock' else (A5_STEEP_SMOOTH,A5_FULL_SMOOTH)
    base=_drop_tips(m,m.tops(4,slope=False)&(m.NYF>=math.cos(math.radians(steep))))
    Z=np.nan_to_num(m.Z,nan=-1e6)
    angle=np.degrees(np.arccos(np.clip(m.NYF,0,1)))
    taper=np.clip((steep-angle)/(steep-full),0,1); taper=taper*taper*(3-2*taper)
    sink=_a5_sink(m,base,Z)
    x=m.u0+np.arange(m.nu)*g; z=m.v0+np.arange(m.nv)*g
    ph=np.random.default_rng(seed+7).uniform(0,2*np.pi,3)
    noise=(.45*np.sin(7*x[None]+ph[0])*np.cos(9*z[:,None])+
           .35*np.sin(13*x[None]-5*z[:,None]+ph[1])+
           .2*np.cos(17*z[:,None]+3*x[None]+ph[2]))
    if calibration: noise[:]=0
    closed=base.copy(); stages={}
    for v in range(1,8):
        d=m.thick(v); closed|=_a4_close(base,Z,d,g)
        W=2*H.distance(closed,int(math.ceil(max(.3,d)/g))+2)*g
        labels,n=H.label(closed,closed[:,:-1]&closed[:,1:],closed[:-1]&closed[1:])
        eligible=np.zeros_like(base)
        for lab in range(n):
            region=labels==lab
            if float(W[region].max())>=.03-1e-9: eligible|=region
        h=d*taper*(1+.15*noise)*np.minimum(1.,W/max(d,1e-9))
        # a5 (Opus): a cap ends in a thin rounded lip at the slope limit, never in particle crumbs
        R=_a4_radius(d)
        h=np.where(base&eligible&(taper>0),np.maximum(h,max(A5_HMIN,A5_BEAD*R)),0.)
        h=_repose(Z,h,base&eligible&(taper>0),g,max(A5_HMIN,A5_BEAD*R))
        pillow=h.copy()
        reach=int(math.ceil(R/g))
        for dj in range(-reach,reach+1):
            for di in range(-reach,reach+1):
                if math.hypot(dj,di)*g>R: continue
                hs=H.sh(h,dj,di,0); zs=H.sh(Z,dj,di,-1e6)
                pillow=np.maximum(pillow,np.where(np.abs(zs-Z)<.5*d,hs,0))
        stages[v]=dict(depth=d,R=R,h=h,pillow_h=pillow,closed=closed.copy(),width=W)
    flat=np.arange(base.size).reshape(base.shape)
    owner=np.where(base,flat,-1)
    distance=np.where(base,0.,np.inf)
    final_closed=closed.copy()
    reach=max(.04,A7_OVMAX if A7_OVH>0 else 0.)
    rr=int(math.ceil(reach/g))+1
    offsets=sorted((math.hypot(dj,di)*g,dj,di) for dj in range(-rr,rr+1) for di in range(-rr,rr+1) if dj or di)
    for ds,dj,di in offsets:
        if ds-.5*g>reach: continue
        candidate=H.sh(np.where(base,flat,-1),dj,di,-1)
        # a5 (Opus): bridged gaps (between bench slats) get bridge columns too, else the cap dips over each gap
        use=(~base)&(owner<0)&(candidate>=0)
        owner[use]=candidate[use]; distance[use]=max(0,ds-.5*g)
    possible=owner>=0
    max_lambda=np.zeros(base.shape)
    for s in stages.values():
        ho=np.where(base,s['h'].ravel()[np.maximum(owner,0)],s['pillow_h'].ravel()[np.maximum(owner,0)])
        # Conservative bank intensity for outer columns; per-particle weights
        # account for the actual permitted upper interval after xy jitter.
        span=np.where(base,ho+.005,ho)
        lam=np.where(possible&(ho>1e-6),A4_C*g*g*span/s['R']**3,0.)
        max_lambda=np.maximum(max_lambda,lam)
    rng=np.random.default_rng(seed)
    # a5 (Opus): systematic rounding instead of Poisson counts (same mean, far less shot noise -> no torn edges)
    count=np.floor(max_lambda+rng.random(max_lambda.shape)).astype(int)
    cols=np.repeat(np.arange(base.size),count.ravel())
    jj,ii=np.unravel_index(cols,base.shape)
    px=m.u0+(ii+rng.uniform(-.5,.5,len(cols)))*g
    pz=m.v0+(jj+rng.uniform(-.5,.5,len(cols)))*g
    q=rng.random(len(cols))
    if A4_STRAT:
        starts=np.cumsum(np.r_[0,count.ravel()[:-1]]); rank=np.arange(len(cols))-starts[cols]
        q=(rank+q)/np.maximum(count.ravel()[cols],1)
    own=owner.ravel()[cols]; oj,oi=np.unravel_index(own,base.shape)
    primary=base.ravel()[cols]
    S=Z.ravel()[own].copy()
    sky,nyp,parts=_source_points(m,np.column_stack((px,pz)))
    # Primary points are projected to the actual visible source face before
    # emission. Reject jitter that crosses a discontinuity into another part.
    normal=m.n_t[m.TID.ravel()[own]]
    dx=px-(m.u0+oi*g); dz=pz-(m.v0+oj*g)
    expected=S-(normal[:,0]*dx+normal[:,2]*dz)/np.where(np.abs(normal[:,1])>1e-7,normal[:,1],1.)
    good_primary=(parts>=0)&(nyp>=math.cos(math.radians(steep)))&(np.abs(sky-expected)<max(.025,3*g))
    alive=(~primary)|good_primary
    S[primary]=sky[primary]
    outside=np.maximum(0,np.hypot(dx,dz)-.5*g)
    clouds={}; cache={}
    for v,s in stages.items():
        d=s['depth']
        if d in cache:
            clouds[v]=cache[d]; continue
        hp=np.where(primary,s['h'].ravel()[own],s['pillow_h'].ravel()[own])
        lower=np.where(primary,-sink.ravel()[own],np.maximum(.3*hp,4*outside)); top=hp
        if A7_OVH>0 and d>.06+1e-9:
            # addonfine (Opus): the rolled lip - an elliptic tube along a free edge that bulges A7_OVH of the depth
            # out at half height and curls back to the edge at the top and at the support
            ov=np.minimum(A7_OVH*hp,A7_OVMAX); e=np.sqrt(np.clip(1-(outside/np.maximum(ov,1e-6))**2,0,1))
            lower=np.where(primary,lower,.5*hp*(1-e)); top=np.where(primary,hp,.5*hp*(1+e))
        span=np.maximum(0,top-lower)
        lam=A4_C*g*g*span/s['R']**3
        weight=lam/np.maximum(max_lambda.ravel()[cols],1e-15)
        # a5 (Opus): a slab thinner than the kernel sums to less field at its top; weight it up by the kernel
        # integral ratio so the iso surface still sits on S+h and a thin layer stays whole
        weight=weight*_a5_boost(hp,d,s['R'])
        py=S+lower+q*span
        good=alive&(hp>1e-6)&(span>1e-6)&(primary|(outside<=reach))
        good&=(parts<0)|(py>=sky-sink.ravel()[own]-.001)
        P=np.column_stack((px[good],py[good],pz[good]))
        cloud=dict(P=P,weight=weight[good].astype(np.float32),R=s['R'],depth=d,
                   threshold=_a4_threshold(d),selected=base&(s['h']>1e-6))
        clouds[v]=cloud; cache[d]=cloud
    return dict(clouds=clouds,base=base,stages=stages,seed=seed,bank_points=len(cols),
                rejected_primary_points=int((primary&~good_primary).sum()),
                primary_source_cells=int(base.sum()),calibration=calibration)


def _a4_grid(plan):
    unique={s['depth']:s for s in plan['clouds'].values()}
    maxR=max(s['R'] for s in unique.values())
    smallest=min(s['depth'] for s in unique.values())
    pitch=np.array((.0075,min(.005,smallest/4),.0075))
    lo=np.min(np.array([s['P'].min(0) for s in unique.values() if len(s['P'])]),axis=0)
    hi=np.max(np.array([s['P'].max(0) for s in unique.values() if len(s['P'])]),axis=0)
    origin=np.floor((lo-maxR-3*pitch)/pitch)*pitch
    shape=np.ceil((hi+maxR+3*pitch-origin)/pitch).astype(int)+1
    core=64; nb=np.ceil((shape-1)/core).astype(int)
    keys=[]
    for s in unique.values():
        unit=(s['P']-origin)/pitch
        s['unit']=unit
        block=np.floor(unit/core).astype(int)
        ids=(block[:,0]*nb[1]+block[:,1])*nb[2]+block[:,2]
        order=np.argsort(ids,kind='stable'); vals,start=np.unique(ids[order],return_index=True)
        ends=np.r_[start[1:],len(order)]
        s['groups']={int(k):order[a:b] for k,a,b in zip(vals,start,ends)}
        low=np.maximum(0,np.floor((unit-maxR/pitch)/core).astype(int))
        high=np.minimum(nb-1,np.floor((unit+maxR/pitch)/core).astype(int))
        for a in (0,1):
            for b in (0,1):
                for c in (0,1):
                    q=np.column_stack((high[:,0] if a else low[:,0],high[:,1] if b else low[:,1],high[:,2] if c else low[:,2]))
                    keys.append(np.unique((q[:,0]*nb[1]+q[:,1])*nb[2]+q[:,2]))
    allkeys=np.unique(np.concatenate(keys))
    tiles=[(int(k//(nb[1]*nb[2])),int((k//nb[2])%nb[1]),int(k%nb[2])) for k in allkeys]
    return dict(origin=origin,pitch=pitch,shape=shape,core=core,nb=nb,maxR=maxR,tiles=tiles)


from functools import lru_cache

@lru_cache(maxsize=24)
def _a4_kernel_fft(radius,pitch,shape):
    axes=[np.arange(-int(math.ceil(radius/h)),int(math.ceil(radius/h))+1) for h in pitch]
    x,y,z=axes
    r2=(x[:,None,None]**2*pitch[0]**2+y[None,:,None]**2*pitch[1]**2+z[None,None,:]**2*pitch[2]**2)/radius**2
    kernel=STIFFNESS*np.maximum(1-r2,0)**3
    padded=np.zeros(shape,np.float32)
    padded[np.ix_(x%shape[0],y%shape[1],z%shape[2])]=kernel
    return np.fft.rfftn(padded)


def _a4_tile(plan,grid,tile,variants,retain_density=False):
    pitch=grid['pitch']; core=grid['core']; nb=grid['nb']
    start=np.array(tile)*core; end=np.minimum(start+core,grid['shape']-1)
    halo=np.ceil(grid['maxR']/pitch).astype(int)+2
    length=end-start+1
    full=length+2*halo
    fftshape=tuple(1<<(int(n)-1).bit_length() for n in full)
    padded_start=start-halo
    previous=None; lastdepth=None; outputs={}; boundary_positive=0
    for v in range(1,max(variants)+1):
        s=plan['clouds'][v]
        if s['depth']!=lastdepth:
            neighbors=[]
            for a in range(max(0,tile[0]-1),min(nb[0],tile[0]+2)):
                for b in range(max(0,tile[1]-1),min(nb[1],tile[1]+2)):
                    for c in range(max(0,tile[2]-1),min(nb[2],tile[2]+2)):
                        k=(a*nb[1]+b)*nb[2]+c
                        if k in s['groups']: neighbors.append(s['groups'][k])
            density=np.zeros(fftshape,np.float32)
            if neighbors:
                ids=np.concatenate(neighbors)
                pos=s['unit'][ids]-padded_start
                ok=np.all((pos>=0)&(pos<full-1),axis=1)
                pos=pos[ok]; ids=ids[ok]
                ijk=np.floor(pos).astype(int); frac=pos-ijk
                for a in (0,1):
                    for b in (0,1):
                        for c in (0,1):
                            weight=s['weight'][ids]*(frac[:,0] if a else 1-frac[:,0])*(frac[:,1] if b else 1-frac[:,1])*(frac[:,2] if c else 1-frac[:,2])
                            np.add.at(density,tuple((ijk+np.array((a,b,c))).T),weight)
            field=np.fft.irfftn(np.fft.rfftn(density)*_a4_kernel_fft(s['R'],tuple(pitch),fftshape),s=fftshape).astype(np.float32)
            sl=tuple(slice(int(h-1),int(h+n+1)) for h,n in zip(halo,length))
            extended=field[sl]-s['threshold']
            dx,dy,dz=np.gradient(extended,*pitch)
            gradient=np.sqrt(dx*dx+dy*dy+dz*dz)[1:-1,1:-1,1:-1]
            raw=extended[1:-1,1:-1,1:-1].copy()
            sdf=np.clip(raw/np.maximum(gradient,.01*s['threshold']/s['R']),-s['R'],s['R'])
            del field,density,extended,dx,dy,dz
            lastdepth=s['depth']
        current=sdf if previous is None else np.maximum(previous,sdf)
        previous=current
        if v in variants:
            origin=grid['origin']+start*pitch
            V,F,edges=G._march(current-3.14159e-7,origin,pitch,return_edges=True)
            edges=edges+start
            key=(edges[:,:,0]*grid['shape'][1]+edges[:,:,1])*grid['shape'][2]+edges[:,:,2]
            for axis in range(3):
                if start[axis]==0: boundary_positive+=int((np.take(current,0,axis=axis)>0).sum())
                if end[axis]==grid['shape'][axis]-1: boundary_positive+=int((np.take(current,-1,axis=axis)>0).sum())
            outputs[v]=(V,F,key)
    return outputs,boundary_positive


def _a5_cluster_block(V,F,E,grid,tile,cell=.015):
    """3D vertex clustering for very large meshes; shared block edges stay exact.

    This is an initial mesh reduction, never a height-map reconstruction.
    Synthetic keys are unique to a block; unchanged boundary vertices retain
    their original global marching-edge keys for the final weld.
    """
    if not len(F): return V,F,E
    start=np.asarray(tile)*grid['core']; end=np.minimum(start+grid['core'],grid['shape']-1)
    lo=grid['origin']+start*grid['pitch']; hi=grid['origin']+end*grid['pitch']
    fixed=np.any((np.abs(V-lo)<1e-8)|(np.abs(V-hi)<1e-8),axis=1)
    interior=np.flatnonzero(~fixed); border=np.flatnonzero(fixed)
    if not len(interior): return V,F,E
    _,inverse=np.unique(np.floor(V[interior]/cell).astype(np.int64),axis=0,return_inverse=True)
    inverse=inverse.ravel(); count=np.bincount(inverse)
    reduced=np.zeros((len(count),3)); np.add.at(reduced,inverse,V[interior]); reduced/=count[:,None]
    mapping=np.empty(len(V),np.int64); mapping[interior]=inverse; mapping[border]=len(count)+np.arange(len(border))
    vv=np.vstack((reduced,V[border])); ff=mapping[F]
    good=(ff[:,0]!=ff[:,1])&(ff[:,1]!=ff[:,2])&(ff[:,2]!=ff[:,0]); ff=ff[good]
    block=(int(tile[0])*grid['nb'][1]+int(tile[1]))*grid['nb'][2]+int(tile[2])
    synthetic=np.column_stack((np.full(len(count),-int(block)-1,dtype=np.int64),np.arange(len(count),dtype=np.int64)))
    ee=np.vstack((synthetic,E[border]))
    return vv,ff,ee


def _a4_extract(plan,variants,workers=4):
    from concurrent.futures import ThreadPoolExecutor
    start=time.perf_counter(); grid=_a4_grid(plan)
    chunks={v:[] for v in variants}; edges={v:[] for v in variants}; cropped=0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for tile,(result,boundary) in zip(grid['tiles'],pool.map(lambda t:_a4_tile(plan,grid,t,variants),grid['tiles'])):
            cropped+=boundary
            for v,(V,F,E) in result.items():
                if plan['bank_points']>1000000:
                    V,F,E=_a5_cluster_block(V,F,E,grid,tile)
                if len(F): chunks[v].append((V,F)); edges[v].append(E)
    output={}
    for v in variants:
        mesh=H.join(chunks[v])
        if mesh is None: output[v]=None; continue
        output[v]=_a3_weld(*mesh,1e-6,edge_keys=np.vstack(edges[v]))
    return output,dict(blocks=len(grid['tiles']),pitch=grid['pitch'].tolist(),
                       lattice_origin=grid['origin'].tolist(),grid_shape=grid['shape'].tolist(),
                       boundary_positive_samples=cropped,field_seconds=time.perf_counter()-start,
                       bank_points=plan['bank_points'],seed=plan['seed']),grid


def _a4_cutter_legacy(m,clearance):
    import bpy,bmesh
    mesh=bpy.data.meshes.new('a4_cutter')
    mesh.from_pydata(m.V.tolist(),[],m.T[m.good_t].tolist())
    bm=bmesh.new(); bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0005)
    bm.verts.index_update()
    seen=set(); duplicates=[]
    for f in bm.faces:
        key=tuple(sorted(v.index for v in f.verts))
        if key in seen: duplicates.append(f)
        else: seen.add(key)
    if duplicates: bmesh.ops.delete(bm,geom=duplicates,context='FACES_ONLY')
    before=sum(1 for e in bm.edges if not e.is_manifold)
    boundary_edges=[e for e in bm.edges if len(e.link_faces)==1]
    filled=bmesh.ops.holes_fill(bm,edges=boundary_edges,sides=0) if boundary_edges else {'faces':[]}
    filled_count=len(filled['faces'])
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.normal_update()
    boundary=sum(1 for e in bm.edges if not e.is_manifold)
    for v in bm.verts: v.co+=v.normal*clearance
    bm.to_mesh(mesh); bm.free()
    snowmat=bpy.data.materials.get('a4_snow') or bpy.data.materials.new('a4_snow')
    cutmat=bpy.data.materials.get('a4_contact') or bpy.data.materials.new('a4_contact')
    mesh.materials.append(snowmat); mesh.materials.append(cutmat)
    for p in mesh.polygons: p.material_index=1
    obj=bpy.data.objects.new('a4_cutter',mesh); bpy.context.scene.collection.objects.link(obj)
    return obj,dict(source_nonmanifold_edges=boundary,source_nonmanifold_before=before,
                    cutter_holes_filled=filled_count,cutter_duplicate_faces_removed=len(duplicates),clearance=clearance)


def _a4_cutter(m,clearance):
    """Closed sky-solid prisms from the original triangles.

    Visual meshes contain open and nonmanifold sheets. Their Boolean inside
    is ambiguous. Every nonvertical source triangle instead owns a closed
    downward prism. Their union is the exact upper sky hull of those faces;
    it removes model interiors and sheltered space without capping snow tops.
    """
    import bpy
    source=m.T[m.good_t&(m.ny_t>.05)]
    V=[]; F=[]; bottom=float(m.V[:,1].min()-.1)
    for tri in source:
        p=m.V[tri].copy()
        normal=np.cross(p[1]-p[0],p[2]-p[0])
        if normal[1]<0: p=p[[0,2,1]]; normal=-normal
        center=p[:,[0,2]].mean(0)
        direction=p[:,[0,2]]-center
        direction/=np.maximum(np.linalg.norm(direction,axis=1),1e-12)[:,None]
        delta=direction*min(.001,clearance*.5)
        p[:,0]+=delta[:,0]; p[:,2]+=delta[:,1]
        p[:,1]+=-((normal[0]*delta[:,0]+normal[2]*delta[:,1])/normal[1])+clearance
        lower=p.copy(); lower[:,1]=bottom
        k=len(V); V.extend(p.tolist()); V.extend(lower.tolist())
        local=[(0,1,2),(3,5,4)]
        for a,b in ((0,1),(1,2),(2,0)):
            local.extend(((b,a,a+3),(b,a+3,b+3)))
        F.extend(tuple(k+x for x in t) for t in local)
    mesh=bpy.data.meshes.new('a4_sky_solid')
    mesh.from_pydata(V,[],F)
    snowmat=bpy.data.materials.get('a4_snow') or bpy.data.materials.new('a4_snow')
    cutmat=bpy.data.materials.get('a4_contact') or bpy.data.materials.new('a4_contact')
    mesh.materials.append(snowmat); mesh.materials.append(cutmat)
    for p in mesh.polygons: p.material_index=1
    obj=bpy.data.objects.new('a4_sky_solid',mesh); bpy.context.scene.collection.objects.link(obj)
    return obj,dict(source_nonmanifold_edges=0,cutter_mode='closed_sky_prisms',
                    cutter_prisms=len(source),clearance=clearance)


def _a4_boolean_shell(m,V,F,clearance=.002):
    import bpy
    cutter,info=_a4_cutter(m,clearance)
    mesh=bpy.data.meshes.new('a4_boolean_snow')
    mesh.from_pydata(V.tolist(),[],F.tolist())
    mesh.materials.append(bpy.data.materials['a4_snow']); mesh.materials.append(bpy.data.materials['a4_contact'])
    obj=bpy.data.objects.new('a4_boolean_snow',mesh); bpy.context.scene.collection.objects.link(obj)
    mod=obj.modifiers.new('a4_remove_model','BOOLEAN')
    mod.operation='DIFFERENCE'; mod.solver='EXACT'; mod.object=cutter
    mod.use_self=True; mod.use_hole_tolerant=info['source_nonmanifold_edges']>0; mod.material_mode='INDEX'
    result=bpy.data.meshes.new_from_object(obj.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    result.calc_loop_triangles()
    vv=np.array([v.co[:] for v in result.vertices])
    ff=np.array([t.vertices[:] for t in result.loop_triangles],dtype=np.int64)
    material=np.array([result.polygons[t.polygon_index].material_index for t in result.loop_triangles])
    info['contact_triangles_removed']=int((material==1).sum())
    info['boolean_triangles']=len(ff)
    keep=material==0
    if len(ff) and keep.any(): vv,ff=G._compact(vv,ff[keep])
    else: vv,ff=np.empty((0,3)),np.empty((0,3),dtype=np.int64)
    cutter_mesh=cutter.data
    bpy.data.objects.remove(obj,do_unlink=True); bpy.data.objects.remove(cutter,do_unlink=True)
    for me in (mesh,cutter_mesh,result): bpy.data.meshes.remove(me)
    return vv,ff,info


def _a4_prune(m,V,F):
    if not len(F): return V,F,0
    boundary=_boundary(F,len(V)); uf=H.UF(len(V))
    for a,b,c in F.tolist(): uf.union(a,b); uf.union(b,c)
    roots=np.array([uf.find(int(f[0])) for f in F]); keep=np.zeros(len(F),bool); removed=0
    for root in np.unique(roots):
        ids=np.flatnonzero(roots==root); pts=np.unique(F[ids]); tri=V[F[ids]]
        area=float(np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1).sum()*.5)
        xy=V[pts][:,[0,2]]; xy-=xy.mean(0)
        _,_,axis=np.linalg.svd(xy,full_matrices=False)
        width=float(np.ptp(xy@axis.T,axis=0).min()) if len(pts)>2 else 0.
        foot=pts[boundary[pts]]
        # the open foot lies sunk up to 2 cm in the support: contact within 3 cm (a floating ball has no foot at all)
        contact=any(m.bvh_all.find_nearest(Vector(V[i]),.03)[0] is not None for i in foot)
        if area>=.01 and width>=.04 and contact and not _side_knob(m,V,F[ids]): keep[ids]=True
        else: removed+=1
    return (*G._compact(V,F[keep]),removed)


def _cap_budget(area):
    """the most LOD0 triangles a cap may have (props 5800, larger 8000/10000/12000)"""
    return 5800 if area<=12 else 8000 if area<=40 else 10000 if area<=120 else 12000


def _err_tol(d):
    """how far the simplified cap may stray from the dense one: about a tenth of the snow's lump size"""
    # the lumps are 1-2 cm high at any depth: a coarser fit lays flat triangles between them that read as pits
    return float(np.clip(.04*d+.002,.0025,.005))


def _err_decimate(V,F,cap,tol,floor=200):
    """the fewest triangles between floor and cap whose surface stays within tol of the dense cap (99.5th percentile
    of sampled dense vertices): a long thin ridge keeps the triangles it needs, a flat roof sheds them"""
    import bpy
    from mathutils.bvhtree import BVHTree
    if len(F)<=floor: return V,F
    me=bpy.data.meshes.new('sz_err_dec'); me.from_pydata(V.tolist(),[],F.tolist())
    obj=bpy.data.objects.new('sz_err_dec',me); bpy.context.scene.collection.objects.link(obj)
    mod=obj.modifiers.new('dec','DECIMATE'); mod.use_collapse_triangulate=True
    pick=np.random.default_rng(5).choice(len(V),min(4000,len(V)),replace=False); S=V[pick]
    NS=_smooth_normals(V,F,_vnormals(V,F),3)[pick] if A7_NTOL>0 else None
    # (Opus, 6 Oct) the other way round as well: every vertex and face centre of the simplified cap within 3 tol of
    # the dense one. One-sided, a collapse could fold a triangle up into a fin standing out of a smooth cap
    dense=BVHTree.FromPolygons(V.tolist(),F.tolist(),all_triangles=True)
    state=[len(F)]
    def run(n):
        mod.ratio=min(1.,n/state[0])
        res=bpy.data.meshes.new_from_object(obj.evaluated_get(bpy.context.evaluated_depsgraph_get()))
        res.calc_loop_triangles()
        v=np.empty(len(res.vertices)*3); res.vertices.foreach_get('co',v)
        f=np.empty(len(res.loop_triangles)*3,np.int32); res.loop_triangles.foreach_get('vertices',f)
        bpy.data.meshes.remove(res)
        return v.reshape(-1,3),f.reshape(-1,3).astype(np.int64)
    def err(v,f):
        if not len(f): return 1e9
        b=BVHTree.FromPolygons(v.tolist(),f.tolist(),all_triangles=True)
        hits=[b.find_nearest(Vector(q)) for q in S]
        d=np.array([h[3] if h[3] is not None else 1e9 for h in hits])
        e=float(np.percentile(d,99.5))
        if e<=tol:
            P=np.vstack((v,v[f].mean(1)))
            back=max((dense.find_nearest(Vector(q),3*tol+1e-4)[3] is None) for q in P)
            if back: return 1e9
        if A7_NTOL>0 and e<=tol:
            # (Opus, 6 Oct) shading: the smooth normal the simplified cap shows at each sample against the dense cap's.
            # Distance alone let long flat triangles cross a rounded pillow - with smooth shading they read as facets
            vn=_vnormals(v,f); ok=np.array([h[2] is not None for h in hits])
            if ok.any():
                idx=np.array([h[2] if h[2] is not None else 0 for h in hits]); loc=np.array([tuple(h[0]) if h[0] is not None else (0,0,0) for h in hits])
                tri=v[f[idx]]; bc=_bary(loc,tri); n=(bc[:,:,None]*vn[f[idx]]).sum(1)
                n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-12)
                ang=np.degrees(np.arccos(np.clip((n*NS).sum(1),-1,1)))[ok]
                if float(np.nanpercentile(ang,95))>A7_NTOL: return 1e9
        return e
    hi=min(cap,len(F))
    if len(F)>3*hi:
        # one pass to three times the cap first: the search below then re-evaluates a light mesh, not the dense one
        v0,f0=run(3*hi); me2=bpy.data.meshes.new('sz_err_dec2'); me2.from_pydata(v0.tolist(),[],f0.tolist())
        obj.data=me2; bpy.data.meshes.remove(me); me=me2; state[0]=len(f0)
    best=run(hi) if hi<state[0] else (V,F)
    if err(*best)<=tol:
        lo=floor
        for _ in range(7):
            if hi<=lo*1.12: break
            mid=int((lo*hi)**.5); cand=run(mid)
            if err(*cand)<=tol: hi,best=mid,cand
            else: lo=mid
    bpy.data.objects.remove(obj,do_unlink=True); bpy.data.meshes.remove(me)
    if A7_UNFOLD>0: best=_unfold(*best,dense,V,F)
    return _beautify(*best) if A7_BEAUTY else best


A7_UNFOLD=75.   # faces of the simplified cap turned more than this from the dense cap under them get relaxed; 0: off


def _unfold(V,F,dense,DV,DF,rounds=6):
    """(Opus, 6 Oct) fins: a collapse can fold a small triangle over its neighbour, so it stands out of a smooth cap
    as a blade (garbage_bin v7) or creases it. A fold faces away from the dense cap under it AND turns more than 90
    degrees from a neighbour across an edge (a thin lip alone is neither). Its shortest edge collapses onto the dense
    cap: the fold goes, nothing around it moves"""
    import bmesh, bpy
    if not len(F): return V,F
    DN=_smooth_normals(DV,DF,_vnormals(DV,DF),3); lim=math.cos(math.radians(A7_UNFOLD))
    def dn_at(P):
        hits=[dense.find_nearest(Vector(q)) for q in P]
        idx=np.array([h[2] if h[2] is not None else 0 for h in hits]); loc=np.array([tuple(h[0]) if h[0] is not None else tuple(q) for h,q in zip(hits,P)])
        n=(_bary(loc,DV[DF[idx]])[:,:,None]*DN[DF[idx]]).sum(1); return n/np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-12),loc
    me=bpy.data.meshes.new('sz_unfold'); me.from_pydata(V.tolist(),[],F.tolist())
    bm=bmesh.new(); bm.from_mesh(me); bpy.data.meshes.remove(me); done=0
    for _ in range(rounds):
        bm.faces.ensure_lookup_table(); bm.normal_update()
        cand=[f for f in bm.faces if f.calc_area()>1e-9 and any(l.edge.is_manifold and f.normal.dot(l.link_loop_radial_next.face.normal)<0 for l in f.loops)]
        if not cand: break
        dn,_=dn_at(np.array([tuple(f.calc_center_median()) for f in cand]))
        bad=[f for f,n in zip(cand,dn) if f.normal.dot(Vector(n))<lim]
        if not bad: break
        edges=set()
        for f in bad:
            ed=min(f.edges,key=lambda x:x.calc_length())
            if not any(v.is_boundary for v in ed.verts) or all(v.is_boundary for v in ed.verts): edges.add(ed)
        if not edges: break
        bmesh.ops.collapse(bm,edges=list(edges),uvs=False); done+=len(edges)
        bmesh.ops.dissolve_degenerate(bm,dist=1e-7,edges=list(bm.edges))
        bmesh.ops.triangulate(bm,faces=list(bm.faces))
        for v in bm.verts:
            if not v.is_boundary and v.is_valid:
                q=dense.find_nearest(v.co,.03)[0]
                if q is not None: v.co=q
    if not done: bm.free(); return V,F
    me=bpy.data.meshes.new('sz_unfold2'); bm.to_mesh(me); bm.free(); me.calc_loop_triangles()
    v=np.empty(len(me.vertices)*3); me.vertices.foreach_get('co',v)
    f=np.empty(len(me.loop_triangles)*3,np.int32); me.loop_triangles.foreach_get('vertices',f)
    bpy.data.meshes.remove(me)
    return v.reshape(-1,3),f.reshape(-1,3).astype(np.int64)


A7_NTOL=20.     # the simplified cap's smooth normals stay within this many degrees of the dense cap's (95th pct); 0: off


A7_BEAUTY=False # edge flips after the decimation: fewer slivers, whose smooth shading read as facets


def _beautify(V,F):
    """rotate edges toward evenly shaped triangles (vertices stay where they are)"""
    import bmesh, bpy
    if not len(F): return V,F
    me=bpy.data.meshes.new('sz_beauty'); me.from_pydata(V.tolist(),[],F.tolist())
    bm=bmesh.new(); bm.from_mesh(me)
    bmesh.ops.beautify_fill(bm,faces=list(bm.faces),edges=list(bm.edges),method='ANGLE')
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bm.to_mesh(me); bm.free(); me.calc_loop_triangles()
    v=np.empty(len(me.vertices)*3); me.vertices.foreach_get('co',v)
    f=np.empty(len(me.loop_triangles)*3,np.int32); me.loop_triangles.foreach_get('vertices',f)
    bpy.data.meshes.remove(me)
    v=v.reshape(-1,3); f=f.reshape(-1,3).astype(np.int64)
    # keep the original winding: the summed normal points the same way
    if np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])[:,1].sum()*np.cross(V[F[:,1]]-V[F[:,0]],V[F[:,2]]-V[F[:,0]])[:,1].sum()<0:
        f=f[:,[0,2,1]]
    return v,f


def _smooth_normals(V,F,N,it):
    e=np.concatenate((F[:,[0,1]],F[:,[1,2]],F[:,[2,0]])); a=np.concatenate((e[:,0],e[:,1])); b=np.concatenate((e[:,1],e[:,0]))
    for _ in range(it):
        S=np.column_stack([np.bincount(a,weights=N[b,c],minlength=len(V)) for c in range(3)])+N
        N=S/np.maximum(np.linalg.norm(S,axis=1)[:,None],1e-12)
    return N


def _vnormals(V,F):
    """area-weighted vertex normals"""
    t=V[F]; n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]); out=np.zeros_like(V)
    for k in range(3):
        for c in range(3): out[:,c]+=np.bincount(F[:,k],weights=n[:,c],minlength=len(V))
    return out/np.maximum(np.linalg.norm(out,axis=1)[:,None],1e-12)


def _bary(P,T):
    """barycentric coordinates of points P (n,3) in triangles T (n,3,3), clipped to the triangle"""
    a,b,c=T[:,0],T[:,1],T[:,2]; v0=b-a; v1=c-a; v2=P-a
    d00=(v0*v0).sum(1); d01=(v0*v1).sum(1); d11=(v1*v1).sum(1); d20=(v2*v0).sum(1); d21=(v2*v1).sum(1)
    den=np.maximum(d00*d11-d01*d01,1e-20); y=(d11*d20-d01*d21)/den; z=(d00*d21-d01*d20)/den
    bc=np.clip(np.column_stack((1-y-z,y,z)),0,1); return bc/np.maximum(bc.sum(1)[:,None],1e-12)


def _floor_faces(m,V,F,mask):
    """faces looking down (ny < -0.7) that lie 0-3 cm under the carrier of their column (in the emission mask)"""
    if not len(F): return np.zeros(0,bool)
    t=V[F]; c=t.mean(1); n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]); n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-15)
    i=np.clip(np.rint((c[:,0]-m.u0)/m.g).astype(int),0,m.nu-1); j=np.clip(np.rint((c[:,2]-m.v0)/m.g).astype(int),0,m.nv-1)
    Z=np.nan_to_num(m.Z,nan=-1e6)[j,i]
    return (n[:,1]<-.7)&mask[j,i]&(c[:,1]<Z+.002)&(c[:,1]>Z-.03)


def _side_knob(m,V,F):
    """a small cap (under 0.01 m2 seen from above) on a side detail (a handle or latch more than 25 cm under the highest
    part of the model within 60 cm): snow does not build there, a post top keeps its cap"""
    t=V[F]; n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]); proj=float(np.abs(n[:,1]).sum()*.5)
    if proj>=.01: return False
    if not hasattr(m,'_sz_zmax'):
        m._sz_zmax=H.maxf(np.nan_to_num(m.Zall,nan=-1e6),max(1,int(round(.6/m.g))))
    c=t.reshape(-1,3).mean(0); u,j=m.ij(np.array([c[0]]),np.array([c[2]]))
    i=int(np.clip(np.rint(u[0]),0,m.nu-1)); jj=int(np.clip(np.rint(j[0]),0,m.nv-1))
    return float(t[:,:,1].max())<float(m._sz_zmax[jj,i])-.25


def _a4_phi(m,P,clearance):
    y,_,part=_source_points(m,P[:,[0,2]])
    vertical=np.where(part>=0,P[:,1]-y-clearance,1.)
    # Vertical clearance alone is zero on a vertical silhouette. Include real
    # 3D distance so float rounding cannot leave the cut exactly on a side face.
    distance=np.array([m.bvh_all.find_nearest(Vector(p))[3] for p in P])
    return np.minimum(vertical,distance-clearance)


def _a4_refine(V,F,selected):
    selected=np.asarray(list(selected),dtype=int)
    if not len(selected): return V,F
    tri=F[selected]
    E=np.unique(np.sort(np.concatenate((tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]])),axis=1),axis=0)
    vertices=V.tolist()
    mid={tuple(e):len(V)+i for i,e in enumerate(E.tolist())}
    vertices.extend(((V[E[:,0]]+V[E[:,1]])*.5).tolist())
    out=[]
    for face in F:
        poly=[]; split=False
        for a,b in zip(face,np.roll(face,-1)):
            poly.append(int(a)); key=tuple(sorted((int(a),int(b))))
            if key in mid: poly.append(mid[key]); split=True
        if not split: out.append(tuple(face)); continue
        center=len(vertices); vertices.append(V[face].mean(0).tolist())
        for a,b in zip(poly,poly[1:]+poly[:1]): out.append((center,a,b))
    return np.array(vertices),np.array(out,dtype=np.int64)


def _a4_clip(m,V,F,clearance=.001,detect_hidden=True):
    """Intersect the existing triangles with the model/sky boundary.
    New points stay on existing 3D triangle edges; no vertex y is projected.
    """
    value=_a4_phi(m,V,clearance); positive=value>0
    if detect_hidden and len(F):
        center=V[F].mean(1); cp=_a4_phi(m,center,clearance)>0
        same=np.all(positive[F],axis=1)|~np.any(positive[F],axis=1)
        ambiguous=same&(cp!=positive[F[:,0]])
        if ambiguous.any():
            V,F=_a4_refine(V,F,np.flatnonzero(ambiguous))
            value=_a4_phi(m,V,clearance); positive=value>0
    whole=F[np.all(positive[F],axis=1)]
    partial=F[np.any(positive[F],axis=1)&~np.all(positive[F],axis=1)]
    vertices=V.tolist(); faces=whole.tolist(); crossings={}
    def cut(a,b):
        key=tuple(sorted((int(a),int(b))))
        if key not in crossings:
            p,q=V[a].copy(),V[b].copy(); sign=positive[a]
            for _ in range(11):
                mid=(p+q)*.5
                if (_a4_phi(m,mid[None],clearance)[0]>0)==sign: p=mid
                else: q=mid
            crossings[key]=len(vertices); vertices.append((p if sign else q).tolist())
        return crossings[key]
    for face in partial:
        poly=[]
        for a,b in zip(face,np.roll(face,-1)):
            if positive[a]: poly.append(int(a))
            if positive[a]!=positive[b]: poly.append(cut(a,b))
        for j in range(1,len(poly)-1): faces.append((poly[0],poly[j],poly[j+1]))
    return G._compact(np.asarray(vertices),np.asarray(faces,dtype=np.int64).reshape(-1,3))


def _a4_finish_clip(m,V,F):
    V,F=_a4_clip(m,V,F)
    refined=0
    for _ in range(3):
        hit=G.intersections(m,V,F)
        if not hit: break
        ids={a for a,b in hit}; refined+=len(ids)
        V,F=_a4_refine(V,F,ids); V,F=_a4_clip(m,V,F,detect_hidden=False)
    hit=G.intersections(m,V,F); deleted=0
    if hit:
        bad=np.unique([a for a,b in hit]); keep=np.ones(len(F),bool); keep[bad]=False
        deleted=len(bad); V,F=G._compact(V,F[keep])
    V,F,pruned=_a4_prune(m,V,F)
    return V,F,dict(refined_intersection_faces=refined,removed_intrusion_faces=deleted,pruned_components=pruned)


def _a5_buried(m,P):
    """Conservative inside test for deletion, including an actual sky ray.

    Nearest normals on overlapping/open visual faces can classify an exposed
    rolled lip as interior. Such a point must never make a deletion candidate.
    """
    result=np.zeros(len(P),bool)
    for i,p in enumerate(P):
        hit,n,_,_=m.bvh_all.find_nearest(Vector(p))
        if hit is not None: result[i]=(Vector(p)-hit).dot(n)<-.0001
    sky,_,part=_source_points(m,np.asarray(P)[:,[0,2]])
    result&=(part>=0)&(np.asarray(P)[:,1]<sky-.0001)
    return result


def _a5_bound(m,V,F,reference):
    """Keep the original exposed upper surface above its own carrier after QEM.

    Classify from the pre-collapse 3D surface, not the collapsed y coordinate.
    Buried lower vertices and rolled rims are not raised onto the skyline.
    """
    source=np.array([reference.find_nearest(Vector(p))[0][:] for p in V])
    sy,_,sp=_source_points(m,source[:,[0,2]])
    upper=(sp>=0)&(source[:,1]>=sy+.0001)
    sky,_,part=_source_points(m,V[:,[0,2]])
    # A discontinuity into a different log/roof is not a valid projection.
    same=(part>=0)&(np.abs(sky-sy)<.025+2*np.linalg.norm(V[:,[0,2]]-source[:,[0,2]],axis=1))
    use=upper&same
    old=V[:,1].copy()
    V[use,1]=np.maximum(V[use,1],sky[use]+.001)
    # Convex supports can pierce an edge even when both endpoints are clear.
    # Only raise wholly upper faces; the sunk rim remains a 3D roundover.
    ids=np.flatnonzero(np.all(use[F],axis=1))
    for _ in range(2):
        if not len(ids): break
        tri=V[F[ids]]
        probes=np.concatenate((tri.mean(1),(tri[:,0]+tri[:,1])*.5,
                               (tri[:,1]+tri[:,2])*.5,(tri[:,2]+tri[:,0])*.5))
        y,_,p=_source_points(m,probes[:,[0,2]])
        dy=np.where(p>=0,np.maximum(0,y+.001-probes[:,1]),0).reshape(4,-1).max(0)
        # A genuinely taller occluder is left for the independent checker;
        # never turn a lower log cap into a spike on the log above it.
        dy=np.where(dy<.035,dy,0)
        shift=np.zeros(len(V)); np.maximum.at(shift,F[ids].ravel(),np.repeat(dy,3))
        V[:,1]+=shift
    return V,int((V[:,1]>old+1e-8).sum()),float(np.max(V[:,1]-old,initial=0))


def _a5_hidden_faces(m,V,F):
    """Delete whole buried triangles only. Never split a sunk contact triangle.

    Probe the interior and edges, so an edge over a gap is not treated as hidden
    merely because its endpoints lie inside two different logs.
    """
    inside=_a5_buried(m,V)
    ids=np.flatnonzero(np.all(inside[F],axis=1))
    hidden=np.zeros(len(F),bool)
    if len(ids):
        tri=V[F[ids]]
        probes=np.concatenate((tri.mean(1),(tri[:,0]+tri[:,1])*.5,
                               (tri[:,1]+tri[:,2])*.5,(tri[:,2]+tri[:,0])*.5))
        ids=ids[np.all(_a5_buried(m,probes).reshape(4,-1),axis=0)]
        for k in ids:
            t=V[F[k]]; probes=[]
            for a,b in zip(t,np.roll(t,-1,axis=0)):
                n=max(1,int(math.ceil(np.linalg.norm(b-a)/.01)))
                probes.extend(a+(b-a)*q/n for q in range(1,n))
            hidden[k]=not probes or bool(np.all(_a5_buried(m,np.asarray(probes))))
    vv,ff=G._compact(V,F[~hidden])
    # Contact can occur along a retained triangle through the model, while
    # its boundary vertices are deeper than the old 6 mm contact test.
    if not len(ff): return vv,ff,dict(hidden_triangles=int(hidden.sum()),pruned_components=0)
    uf=H.UF(len(vv))
    for a,b,c in ff.tolist(): uf.union(a,b); uf.union(b,c)
    roots=np.array([uf.find(int(f[0])) for f in ff]); keep=np.zeros(len(ff),bool)
    touching={int(roots[a]) for a,b in G.intersections(m,vv,ff)}
    removed=0
    for root in np.unique(roots):
        ids=np.flatnonzero(roots==root); pts=np.unique(ff[ids]); tri=vv[ff[ids]]
        projected=float(np.abs(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])[:,1]).sum()*.5)
        xy=vv[pts][:,[0,2]]; xy-=xy.mean(0)
        _,_,axes=np.linalg.svd(xy,full_matrices=False)
        width=float(np.ptp(xy@axes.T,axis=0).min()) if len(pts)>2 else 0.
        contact=root in touching or any(m.bvh_all.find_nearest(Vector(vv[i]),.005)[0] is not None for i in pts)
        if projected>=.01 and width>=.04 and contact: keep[ids]=True
        else: removed+=1
    return (*G._compact(vv,ff[keep]),dict(hidden_triangles=int(hidden.sum()),pruned_components=removed))


def _a5_finish(m,V,F,limit):
    from mathutils.bvhtree import BVHTree
    # This reference is classification only. The output is still the 3D
    # isosurface simplified by QEM, with no resampling into a height map.
    reference=BVHTree.FromPolygons(V.tolist(),F.tolist(),all_triangles=True)
    attempts=[]
    target=min(len(F),int(limit*1.7))
    while True:
        vv,ff=G._decimate(V,F,target) if len(F)>target else (V.copy(),F.copy())
        vv=_a3_taubin(vv,ff,passes=1)
        vv,raised,max_raise=_a5_bound(m,vv,ff,reference)
        vv,ff,info=_a5_hidden_faces(m,vv,ff)
        attempts.append(dict(closed_target=target,triangles=len(ff),bound_vertices=raised,
                             max_bound_raise_m=max_raise,**info))
        if len(ff)<=limit or target<=limit: break
        target=max(limit,int(target*limit/len(ff)*.98))
    return vv,ff,attempts


def prepare_a4(m,variants=(1,4,7),workers=4,calibration=False):
    report=getattr(m,'_addon_log',lambda *args:None)
    start=time.perf_counter(); plan=_a4_plan(m,calibration=calibration)
    planning_seconds=time.perf_counter()-start
    report('particles',plan['bank_points'],'planning_s',planning_seconds)
    raw,shared,grid=_a4_extract(plan,variants,workers)
    report('field_complete',shared)
    cache={}
    for v in variants:
        t=time.perf_counter()
        if raw[v] is None:
            cache[v]=dict(mesh=None,stats=dict(empty=True)); continue
        V,F=raw[v]
        topology=_a3_topology(V,F,dict(u0=grid['origin'][0],v0=grid['origin'][2],g=grid['pitch'][0]),grid['core'])
        area=float(np.sum(m.g*m.g/np.maximum(m.NYF[plan['clouds'][v]['selected']],.423)))
        limit=budget(area)
        report('bounded_decimate',v,'budget',limit)
        vv,ff,attempts=_a5_finish(m,V,F,limit)
        stats=dict(method='a5',variant=v,depth=m.thick(v),radius=_a4_radius(m.thick(v)),
                   threshold=_a4_threshold(m.thick(v)),c=A4_C,seed=SEED,
                   bank_points=plan['bank_points'],active_particles=len(plan['clouds'][v]['P']),
                   weighted_particles=float(plan['clouds'][v]['weight'].sum()),
                   primary_source_cells=plan['primary_source_cells'],
                   rejected_jitter_points=plan['rejected_primary_points'],
                   raw_topology=topology,raw_triangles=len(F),triangles=len(ff),budget=limit,
                   intersections=len(G.intersections(m,vv,ff)),attempts=attempts,
                   contact_cleanup='whole_buried_triangles_after_bounded_decimate',
                   forced_budget_pass=False,budget_cut_faces=0,
                   taubin_before_contact_removal=True,
                   planning_seconds=planning_seconds,field_seconds_shared=shared['field_seconds'],
                   field_seconds_amortized=(planning_seconds+shared['field_seconds'])/len(variants),
                   cleanup_seconds=time.perf_counter()-t,**{k:x for k,x in shared.items() if k not in ('field_seconds','bank_points','seed')})
        cache[v]=dict(mesh=(vv,ff),raw=(V,F) if getattr(m,'_addon_keep_raw',True) else None,
                      stats=stats,selected=plan['clouds'][v]['selected'])
    m._snow_a4_cache=cache; m._snow_a4_total_seconds=time.perf_counter()-start
    return cache


def build_a5(m,variant):
    """A5 candidate entry point; prepare_a4 keeps its historical API name."""
    if not hasattr(m,'_snow_a4_cache') or variant not in m._snow_a4_cache:
        prepare_a4(m,(variant,))
    data=m._snow_a4_cache[variant]; m.addon_stats=dict(data['stats'])
    if data['mesh'] is None or not len(data['mesh'][1]): return None
    m._sel|=data['selected']; m._claimed|=data['selected']
    return G._register(m,*data['mesh'],.003,m.g)


def _a6_plan(m):
    """Surface particles at real-addon density, with one deterministic bank."""
    steep,full=(A5_STEEP,A5_FULL) if getattr(m,'rough',False) or m.cls=='rock' else (A5_STEEP_SMOOTH,A5_FULL_SMOOTH)
    mask=_drop_tips(m,m.tops(4,slope=False)&(m.NYF>=math.cos(math.radians(steep))))
    Z=np.nan_to_num(m.Z,nan=-1e6); sink=_a5_sink(m,mask,Z)
    # gaps between boards of one surface (a bench seat, a deck) up to ~2.5 cm carry snow at the boards' height:
    # without particles there the cap sags into a groove that reads as a dark line
    gap=_a4_close(mask,Z,max(m.thick(1),.04),m.g)&~mask
    if getattr(m,'rough',False) or m.cls=='rock':
        # (Opus, 6 Oct) a crack in a rock's crown (up to ~7 cm wide, its sides up to 7 cm apart in height) is bridged
        # by the snow from the first depth on: it showed as a dark slit through the cap (stone4)
        gap|=_a4_close(mask,Z,.15,m.g)&~mask
    Zfill=np.where(gap,H.maxf(np.where(mask,Z,-1e6),max(1,int(math.ceil(.02/m.g)))),Z)
    if A7_ROCKFILL and (getattr(m,'rough',False) or m.cls=='rock'):
        # a steep crevice or notch inside a rock's crown (enclosed, up to 0.25 m2) emitted nothing and showed as a hole
        # in the cap at v1-v4: the snow bridges it at the height of its rim (inpainted from the rim inwards); for the
        # floor it counts as a carrier, so the rising floor does not cut the bridge
        hole=_enclosed(mask|gap,.25/(m.g*m.g))
        if hole.any():
            Zh=_inpaint(np.where(mask|gap,np.where(gap,Zfill,Z),np.nan),hole)
            ok=hole&np.isfinite(Zh); Zfill=np.where(ok,Zh,Zfill); gap=gap|ok
            mask_floor=mask|ok; Z_floor=np.where(ok,Zh,Z); sink=np.where(ok,.003,sink)
    angle=np.degrees(np.arccos(np.clip(m.NYF,0,1)))
    taper=np.clip((steep-angle)/(steep-full),0,1); taper=taper*taper*(3-2*taper)
    # addonfine (Opus): the layer thins out before the slope limit instead of ending in a row of beads (drips on rock)
    # (rock and rough models only: on a steep smooth roof the thinned layer broke up into pits)
    rough=getattr(m,'rough',False) or m.cls=='rock'
    fade=np.clip((steep-angle)/A7_FADE,0,1) if A7_FADE>0 and rough else np.ones_like(angle); fade=fade*fade*(3-2*fade)
    if A7_CREVICE>0 and rough:
        # (Opus, 6 Oct) the steep walls of a narrow crevice in a rock's crown are in the mask, but their particles fade
        # out toward the slope limit: the cap sank into the crevice and left a dark slit at v1-v4 (stone4). Walls lying
        # below the line between well-carrying cells less than A7_CREVICE apart emit at full weight at that line's height
        good=mask&(fade>=.5)
        crev=_a4_close(good,Z,2*A7_CREVICE,m.g)&~good&mask
        if crev.any():
            Zc=_inpaint(np.where(good,Z,np.nan),crev)
            ok=crev&np.isfinite(Zc)&(Zc>Z+.01)
            Zfill=np.where(ok,Zc,Zfill); gap=gap|ok
    emit=mask|gap
    stages={}; closed=mask.copy(); means={}
    for v in range(1,8):
        d=m.thick(v); base=min(d,A7_BASEMAX); height=base/.331
        closed|=_a4_close(mask,Z,d,m.g)
        width=2*H.distance(closed,int(math.ceil(max(.3,d)/m.g))+2)*m.g
        extra=(d-base)*taper*np.minimum(1,width/max(d,1e-9))
        stages[v]=dict(depth=d,base=base,height=height,R=.54*height,D=extra,width=width)
        if base not in means:
            means[base]=np.where(emit,_dens(base)*50/height**2*m.g*m.g/np.where(gap,1.,np.maximum(m.NYF,.1))*np.where(gap,1.,fade),0.)
    rng=np.random.default_rng(SEED); rounding=rng.random(mask.shape)
    counts={b:np.floor(lam+rounding).astype(int) for b,lam in means.items()}
    maximum=np.maximum.reduce(list(counts.values()))
    cols=np.repeat(np.arange(mask.size),maximum.ravel())
    jj,ii=np.unravel_index(cols,mask.shape)
    starts=np.cumsum(np.r_[0,maximum.ravel()[:-1]])
    ordinal=np.arange(len(cols))-starts[cols]
    px=m.u0+(ii+rng.uniform(-.5,.5,len(cols)))*m.g
    pz=m.v0+(jj+rng.uniform(-.5,.5,len(cols)))*m.g
    sky,ny,parts=_source_points(m,np.column_stack((px,pz)))
    normal=m.n_t[np.maximum(m.TID.ravel()[cols],0)]
    expected=Z.ravel()[cols]-(normal[:,0]*(px-m.u0-ii*m.g)+normal[:,2]*(pz-m.v0-jj*m.g))/np.where(np.abs(normal[:,1])>1e-7,normal[:,1],1.)
    good=(parts>=0)&(ny>=math.cos(math.radians(steep)))&(np.abs(sky-expected)<max(.025,3*m.g))
    isgap=gap.ravel()[cols]; sky=np.where(isgap,Zfill.ravel()[cols],sky); good|=isgap
    clouds={}
    for b,c in counts.items():
        selected=good&(ordinal<c.ravel()[cols])
        clouds[b]=dict(P=np.column_stack((px[selected],sky[selected],pz[selected])),R=.54*b/.331,base=b)
    if 'mask_floor' in locals(): mask,Z=mask_floor,Z_floor
    return dict(mask=mask,Z=Z,sink=sink,taper=taper,stages=stages,clouds=clouds,
                bank_points=len(cols),rejected_points=int((~good).sum()),seed=SEED)


_FFTSIZES=sorted({2**a*3**b*5**c for a in range(13) for b in range(8) for c in range(6) if 2**a*3**b*5**c<=8192})


def _fftsize(n):
    """the smallest 2^a 3^b 5^c length >= n (pocketfft is fast there; a power of two wasted up to half)"""
    import bisect
    return _FFTSIZES[bisect.bisect_left(_FFTSIZES,n)]


A7_DENSK=2.     # deep caps: particle density (and threshold) x (1 + A7_DENSK) at 23 cm, x1 at 5 cm


def _dens(base):
    """addonfine's density gives one lump per few particles in the kernel: on a 15 m roof the deep cap turned pitted
    (each depth's own lumps crossing in the nested union). More particles with a proportionally higher threshold
    keep the mean surface and calm the noise (1/sqrt of the factor)"""
    return 1.+A7_DENSK*float(np.clip((base-.05)/.18,0,1))


A7_ROCKFILL=True
A7_WALLCAP=2500        # a fence or wall (kind 1, placed by the thousand): its cap's LOD0 triangles at most
A7_WALLCAP_ROUGH=2500  # ... a rough one (a rubble or field-stone wall): its lumps need more, or they read as facets
A7_CREVICE=0.    # rocks: a crevice this narrow is bridged at its rim's height from the first depth on (0: off;
                 # stone4's 'hole' was a 30-40 cm step face at 66-76 degrees, bare rock by right; tried .15 in c24)
A7_BANDH=1.      # band: a column's own snow reaches this many depths (+1 cm) above its carrier; 0: no band
A7_LEVELW=0.     # ... and at most this many times its level's width (a narrow ledge); 0: no width limit
A7_BANDSTEP=.04  # ... and only toward a carrier at least this much higher
A7_LEVELMIN=.08  # ... but never under 8 cm: a bin's rim 3 cm under its lid stays inside the lid's pillow (the band
                 # cut a trench through it), a pallet strip 14 cm under the next pallet is parted from its cap
A7_MINLAYER=.25 # every carrier keeps a layer of this share of the depth (8-20 mm), 0: none


def _enclosed(M,maxcells):
    """cells outside M in components (4-connected) that touch no grid border and have at most maxcells cells"""
    O=~M; lab,n=H.label(O,O[:,:-1]&O[:,1:],O[:-1]&O[1:])
    if not n: return np.zeros_like(M)
    L=np.where(O,lab,n); cnt=np.bincount(L.ravel(),minlength=n+1)[:n]
    edge=np.unique(np.concatenate((L[0],L[-1],L[:,0],L[:,-1]))); bad=np.zeros(n+1,bool); bad[edge]=True
    keep=(cnt<=maxcells)&~bad[:n]
    return O&np.r_[keep,False][L]


def _inpaint(A,hole,iters=400):
    """fill the hole cells of A (nan there) with the mean of their filled 4-neighbours, from the rim inwards"""
    A=A.copy()
    for _ in range(iters):
        todo=hole&~np.isfinite(A)
        if not todo.any(): break
        s=np.zeros_like(A); c=np.zeros_like(A)
        for dj,di in ((0,1),(0,-1),(1,0),(-1,0)):
            B=H.sh(A,dj,di,np.nan); f=np.isfinite(B); s+=np.where(f,B,0); c+=f
        A=np.where(todo&(c>0),s/np.maximum(c,1),A)
    return A


def _ovl(base):
    return A7_OVL*base+.01


def _box2(A,r):
    """2-d box sum of half width r (two passes: a tent), zero outside"""
    for _ in range(2):
        for ax in (0,1):
            c=np.cumsum(np.pad(A,[(r+1,r) if a==ax else (0,0) for a in (0,1)]),axis=ax)
            A=np.take(c,np.arange(2*r+1,c.shape[ax]),axis=ax)-np.take(c,np.arange(0,c.shape[ax]-2*r-1),axis=ax)
    return A


def _a6_grid(m,plan):
    # The emitter grid is independent of the extraction grid. Large models
    # retain the same surface particle density while using larger voxels.
    # big models on a coarser lattice (3 cm at 15 m): the lumps are 8+ cm there, and a house builds in minutes
    g=float(np.clip(float(np.ptp(m.V,axis=0).max())/450.,.0075,.03))
    gy=min(g,min(s['base'] for s in plan['stages'].values())/3)
    pitch=np.array((g,gy,g)); core=64
    maxR=max(s['R'] for s in plan['clouds'].values())
    extra=max(float(s['D'].max()) for s in plan['stages'].values())
    clouds=[s for s in plan['clouds'].values() if len(s['P'])]
    lo=np.min([s['P'].min(0) for s in clouds],axis=0)-maxR-3*pitch
    hi=np.max([s['P'].max(0) for s in clouds],axis=0)+maxR+3*pitch+np.array((0,extra,0))
    origin=np.floor(lo/pitch)*pitch; shape=np.ceil((hi-origin)/pitch).astype(int)+1
    nb=np.ceil((shape-1)/core).astype(int); keys=[]
    for s in clouds:
        unit=(s['P']-origin)/pitch; s['unit']=unit
        block=np.floor(unit/core).astype(int); ids=(block[:,0]*nb[1]+block[:,1])*nb[2]+block[:,2]
        order=np.argsort(ids,kind='stable'); vals,start=np.unique(ids[order],return_index=True); ends=np.r_[start[1:],len(order)]
        s['groups']={int(k):order[a:b] for k,a,b in zip(vals,start,ends)}
        low=np.maximum(0,np.floor((unit-maxR/pitch)/core).astype(int))
        high=np.minimum(nb-1,np.floor((unit+(maxR+np.array((0,extra,0)))/pitch)/core).astype(int))
        span=np.max(high-low,axis=0)
        for a in range(int(span[0])+1):
            for b in range(int(span[1])+1):
                for c in range(int(span[2])+1):
                    q=np.minimum(low+np.array((a,b,c)),high)
                    keys.append(np.unique((q[:,0]*nb[1]+q[:,1])*nb[2]+q[:,2]))
    allkeys=np.unique(np.concatenate(keys)); tiles=[(int(k//(nb[1]*nb[2])),int((k//nb[2])%nb[1]),int(k%nb[2])) for k in allkeys]
    # All 2D constraints are sampled once on the same global lattice.
    xx=origin[0]+np.arange(shape[0])*g; zz=origin[2]+np.arange(shape[2])*g
    mi=np.rint((xx-m.u0)/m.g).astype(int); mj=np.rint((zz-m.v0)/m.g).astype(int)
    valid=(mj[:,None]>=0)&(mj[:,None]<m.nv)&(mi[None,:]>=0)&(mi[None,:]<m.nu)
    mi=np.clip(mi,0,m.nu-1); mj=np.clip(mj,0,m.nv-1)
    M=valid&plan['mask'][mj[:,None],mi[None,:]]
    S=plan['Z'][mj[:,None],mi[None,:]]; sink=plan['sink'][mj[:,None],mi[None,:]]
    # the minimum layer (see _a7_tile): the carrier's surface, its sink and a taper to nothing over 4 cm at the edge
    dM=H.distance(M,int(math.ceil(.04/g))+2)*g
    # (only up to about 45 degrees: on a steeper flank, a round log's side, the vertical layer of each column stood out
    # as a comb of steps where the particle surface runs thinner)
    nyl=m.NYF[mj[:,None],mi[None,:]]; ws=np.clip((nyl-math.cos(math.radians(50)))/(math.cos(math.radians(35))-math.cos(math.radians(50))),0,1)
    minlayer=dict(lo=np.where(M,S-sink,np.nan).T.astype(np.float32),top=np.where(M,S,np.nan).T.astype(np.float32),
                  w=np.where(M,np.clip(dM/.04,0,1)*ws,0.).T.astype(np.float32))
    source=np.arange(M.size).reshape(M.shape); floors={}; owners={}; dists={}; bands={}
    SF=np.where(M,S-sink,np.nan)
    # levels: carriers joined by a continuous surface (a roof plane, both slopes of a ridge) are one level; the band
    # only parts different levels (a sloping roof crumpled where its own upper slope counted as a higher carrier)
    Sf=np.where(M,S,np.nan); stepmax=g*math.tan(math.radians(A5_STEEP))+.008
    lx=M[:,:-1]&M[:,1:]&(np.abs(Sf[:,:-1]-Sf[:,1:])<=stepmax); lz=M[:-1]&M[1:]&(np.abs(Sf[:-1]-Sf[1:])<=stepmax)
    lev,_nl=H.label(M,lx,lz); lev=np.where(M,lev,-1)
    # (and only between different parts: a pallet over a pallet, a table top over its bench. On one rock the band cut
    # the cap of a higher facet over a lower one into a flap)
    PG=np.where(M,m.PART[mj[:,None],mi[None,:]],-1)
    # (Opus, 6 Oct) a narrow level - the strip of a lower pallet showing beside the one on top, a frame ledge - holds
    # no more snow than about its width (2 x area / outline): its band cap stops there, so a deep cap above no longer
    # merges down onto it as a curtain within the first 10 cm of its edge. Wide levels (roofs, decks) are unchanged
    LW=np.full(M.shape,np.inf)
    if A7_LEVELW>0 and _nl:
        degl=np.zeros(M.shape); degl[:,:-1]+=lx; degl[:,1:]+=lx; degl[:-1]+=lz; degl[1:]+=lz
        le=np.where(M,lev,_nl); ca=np.bincount(le.ravel(),minlength=_nl+1)[:_nl]
        pe=np.bincount(le.ravel(),weights=np.where(M,4-degl,0).ravel(),minlength=_nl+1)[:_nl]
        LW=np.where(M,np.r_[2*ca*g/np.maximum(pe,1),np.inf][le],np.inf)
    for base,cloud in plan['clouds'].items():
        if base not in {s['base'] for s in plan['stages'].values()}: continue
        radius=cloud['R']
        # columns beyond the lip limit hold no snow: the carrier search stops there (a 40 cm kernel would search far)
        if A7_OVL>0: radius=min(radius,_ovl(base)*(1+A7_OVK)+2*g)
        if A7_RISE>0: radius=min(radius,(1.4*base+.03)/A7_RISE+2*g)
        reach=int(math.ceil(radius/g))
        # Local carrier inside the mask; nearest carrier outside. A maximum
        # height filter raises the floor above round/sloping supports and
        # slices away their cap. Never substitute a higher nearby carrier.
        owner=np.where(M,source,-1); dist=np.where(M,0.,np.inf)
        offsets=sorted((math.hypot(dj,di)*g,dj,di) for dj in range(-reach,reach+1)
                       for di in range(-reach,reach+1) if dj or di)
        # the band (Opus, 6 Oct): a higher carrier's lip may not reach down onto a lower carrier's own snow (a pallet's
        # cap onto a board lower down the stack, a table top onto its bench): in a column whose own snow tops out at
        # its carrier + hcap, the lowest underside a higher neighbour's lip may have (its floor rising with distance)
        # is kept apart from it; between the two no snow (only where they are apart: on stair treads at v7 they merge)
        hcap=np.minimum(A7_BANDH*base,np.maximum(A7_LEVELW*LW,A7_LEVELMIN))+.01; up=np.full(M.shape,np.inf); owncap=np.where(M,S+hcap,np.nan)
        for distance,dj,di in offsets:
            if distance>radius+1e-9: continue
            own=H.sh(np.where(M,source,-1),dj,di,-1)
            take=(owner<0)&(own>=0); owner[take]=own[take]; dist[take]=distance
            if A7_BANDH>0:
                owncap[take]=(S+hcap).ravel()[own[take]]
                zc=H.sh(SF,dj,di,np.nan)+A7_RISE*distance
                ln=H.sh(lev,dj,di,-1); lo_=np.where(owner>=0,lev.ravel()[np.maximum(owner,0)],-2)
                pn=H.sh(PG,dj,di,-1); po=np.where(owner>=0,PG.ravel()[np.maximum(owner,0)],-2)
                hi=np.isfinite(zc)&(zc>owncap)&(ln>=0)&(ln!=lo_)&(pn>=0)&(pn!=po)
                # (Opus, 6 Oct) only a HIGHER carrier: deck boards side by side at one height (separate parts and
                # levels across their gaps) were cut into terraces where a neighbour's rising floor passed their cap
                hi&=(H.sh(SF,dj,di,np.nan)-np.where(owner>=0,SF.ravel()[np.maximum(owner,0)],np.nan))>A7_BANDSTEP
                up=np.where(hi,np.minimum(up,zc),up)
        floor=np.where(owner>=0,(S-sink).ravel()[np.maximum(owner,0)],-np.inf)
        rb=int(math.ceil(A7_FLOORBLUR*cloud['R']/g))
        if rb>0:
            # beside stair treads or roof planes of different heights the nearest carrier changes from one column to
            # the next: a hard floor there cut a vertical wall into the pillow. Outside the carriers the floor runs
            # smoothly from one to the other (only outside columns are averaged: a lip keeps its own carrier's level)
            out=(owner>=0)&~M; val=np.where(out,floor,0.)
            num=_box2(val,rb); den=_box2(out.astype(float),rb)
            # (Opus, 6 Oct) ... but a lip sinks at most 30% of the depth under its own carrier: beside a pallet stack
            # the floors of carriers 20-40 cm lower pulled the top cap's lip down the side as a curtain. Between stair
            # treads the lower tread's own pillow still fills up to the upper one
            blurred=num/np.maximum(den,1e-9)
            if A7_LIPDROP>0: blurred=np.maximum(blurred,floor-(A7_LIPDROP*base+.005))
            floor=np.where(out,blurred,floor)
        # the rise comes after the smoothing: smoothed, the rising floor lifted a deep pillow's underside off the edge
        # (a wide kernel averages far, high columns) and the thinner depths' lips showed under it as a flange
        if A7_RISE>0: floor=np.where((owner>=0)&~M,floor+A7_RISE*dist,floor)
        floors[base]=floor.T; owners[base]=owner; dists[base]=dist.T
        if A7_BANDH>0: bands[base]=(np.where(np.isfinite(up),owncap,np.nan).T.astype(np.float32),up.T.astype(np.float32))
    for s in plan['stages'].values():
        D=s['D'][mj[:,None],mi[None,:]]; owner=owners[s['base']]
        # The rolled lip inherits the extension of its carrying surface.
        s['lattice_D']=np.where(M,D,D.ravel()[np.maximum(owner,0)]).T
    return dict(origin=origin,pitch=pitch,shape=shape,core=core,nb=nb,maxR=maxR,
                extra=extra,tiles=tiles,floors=floors,dists=dists,minlayer=minlayer,bands=bands)


def _a6_vertical_max(F,D,gy):
    """Continuous-length vertical dilation on the lattice (no top-height rewrite)."""
    out=F.copy(); steps=np.floor(D/gy).astype(int)
    for k in range(1,min(F.shape[1],int(steps.max())+1)):
        np.maximum(out[:,k:,:],np.where((steps>=k)[:,None,:],F[:,:-k,:],-1e6),out=out[:,k:,:])
    frac=D/gy-steps
    y=np.arange(F.shape[1])[None,:,None]-steps[:,None,:]
    a=np.take_along_axis(F,np.clip(y,0,F.shape[1]-1),axis=1)
    b=np.take_along_axis(F,np.clip(y-1,0,F.shape[1]-1),axis=1)
    endpoint=(1-frac[:,None,:])*a+frac[:,None,:]*b
    endpoint=np.where(y>=0,endpoint,-1e6)
    return np.maximum(out,endpoint)


def _a6_tile(plan,grid,tile,variants):
    pitch=grid['pitch']; core=grid['core']; nb=grid['nb']
    start=np.array(tile)*core; end=np.minimum(start+core,grid['shape']-1); length=end-start+1
    halo=np.ceil((grid['maxR']+np.array((0,grid['extra'],0)))/pitch).astype(int)+3
    full=length+2*halo; fftshape=tuple(1<<(int(n)-1).bit_length() for n in full)
    padded_start=start-halo; base_fields={}; outputs={}; cropped=0
    for v in variants:
        stage=plan['stages'][v]; base=stage['base']; cloud=plan['clouds'][base]
        if base not in base_fields:
            neighbors=[]
            yr=int(math.ceil((cloud['R']+grid['extra'])/(core*pitch[1])))+1
            for a in range(max(0,tile[0]-1),min(nb[0],tile[0]+2)):
                for b in range(max(0,tile[1]-yr),min(nb[1],tile[1]+2)):
                    for c in range(max(0,tile[2]-1),min(nb[2],tile[2]+2)):
                        key=(a*nb[1]+b)*nb[2]+c
                        if key in cloud['groups']: neighbors.append(cloud['groups'][key])
            density=np.zeros(fftshape,np.float32)
            if neighbors:
                ids=np.concatenate(neighbors); pos=cloud['unit'][ids]-padded_start
                pos=pos[np.all((pos>=0)&(pos<full-1),axis=1)]
                ijk=np.floor(pos).astype(int); frac=pos-ijk
                for a in (0,1):
                    for b in (0,1):
                        for c in (0,1):
                            w=(frac[:,0] if a else 1-frac[:,0])*(frac[:,1] if b else 1-frac[:,1])*(frac[:,2] if c else 1-frac[:,2])
                            np.add.at(density,tuple((ijk+np.array((a,b,c))).T),w)
            field=np.fft.irfftn(np.fft.rfftn(density)*_a4_kernel_fft(cloud['R'],tuple(pitch),fftshape),s=fftshape).astype(np.float32)-THRESHOLD
            extra_y=int(math.ceil(grid['extra']/pitch[1]))+1
            lower=halo-np.array((1,extra_y+1,1)); upper=halo+length+1
            f=field[tuple(slice(int(a),int(b)) for a,b in zip(lower,upper))]
            grad=np.gradient(f,*pitch); norm=np.sqrt(sum(a*a for a in grad))
            # Metres near the zero surface, so the 5 mm smooth minimum has
            # the same physical size for every depth/kernel radius.
            sdf=np.clip(f/np.maximum(norm,.01*THRESHOLD/cloud['R']),-cloud['R'],cloud['R'])
            base_fields[base]=(sdf[1:-1,1:-1,1:-1].copy(),extra_y)
        sdf,extra_y=base_fields[base]
        sl=(slice(int(start[0]),int(end[0])+1),slice(int(start[2]),int(end[2])+1))
        D=stage['lattice_D'][sl]; floor=grid['floors'][base][sl]
        current=_a6_vertical_max(sdf,D,pitch[1])[:,extra_y:,:]
        yy=grid['origin'][1]+np.arange(start[1],end[1]+1)*pitch[1]
        lower=yy[None,:,None]-floor[:,None,:]
        current=_smin(current,lower,.005)
        current=np.where(np.isfinite(floor)[:,None,:],current,-cloud['R'])
        V,F,E=G._march(current-3.14159e-7,grid['origin']+start*pitch,pitch,return_edges=True)
        E=E+start; keys=(E[:,:,0]*grid['shape'][1]+E[:,:,1])*grid['shape'][2]+E[:,:,2]
        for axis in range(3):
            if start[axis]==0: cropped+=int((np.take(current,0,axis=axis)>0).sum())
            if end[axis]==grid['shape'][axis]-1: cropped+=int((np.take(current,-1,axis=axis)>0).sum())
        outputs[v]=(V,F,keys)
    return outputs,cropped


def _a6_hidden(m,V):
    inside=np.zeros(len(V),bool)
    # a vertex above the highest surface of its column (3x3 cells) lies outside every part: only the rest is tested
    # (the top half of a dense cap; on a house that halves ~300k nearest-point queries)
    Zt=getattr(m,'_sz_ztop',None)
    if Zt is None: Zt=m._sz_ztop=H.maxf(np.nan_to_num(np.fmax(m.Z,getattr(m,'Zall',m.Z)),nan=-1e6),1)
    i=np.rint((V[:,0]-m.u0)/m.g).astype(int); j=np.rint((V[:,2]-m.v0)/m.g).astype(int)
    ok=(i>=0)&(i<m.nu)&(j>=0)&(j<m.nv); top=np.full(len(V),-1e6); top[ok]=Zt[j[ok],i[ok]]
    test=np.flatnonzero(V[:,1]<=top+.01)
    for k,p in zip(test.tolist(),V[test]):
        hit,n,_,_=m.bvh_all.find_nearest(Vector(p))
        if hit is not None: inside[k]=(Vector(p)-hit).dot(n)<-.005
    ids=np.flatnonzero(inside)
    if len(ids):
        sky,_,part=_source_points(m,V[ids][:,[0,2]])
        # only clearly buried vertices: open models (rocks, logs) misjudge inside near their skin and tore holes
        inside[ids]&=(part>=0)&(V[ids,1]<sky-.005)
    return inside


def prepare_a6(m,variants=(1,4,7),workers=4):
    from concurrent.futures import ThreadPoolExecutor
    report=getattr(m,'_addon_log',lambda *args:None); start=time.perf_counter()
    plan=_a6_plan(m)
    if not any(len(s['P']) for s in plan['clouds'].values()):
        m._snow_a6_cache={v:dict(mesh=None,stats=dict(method='a6',empty=True)) for v in variants}; return m._snow_a6_cache
    grid=_a6_grid(m,plan); planning=time.perf_counter()-start
    report('a6_plan',plan['bank_points'],'particles',len(grid['tiles']),'blocks','pitch',grid['pitch'].tolist())
    chunks={v:[] for v in variants}; keys={v:[] for v in variants}; cropped=0
    t=time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for tile,(result,boundary) in zip(grid['tiles'],pool.map(lambda tile:_a6_tile(plan,grid,tile,variants),grid['tiles'])):
            cropped+=boundary
            for v,(V,F,E) in result.items():
                if len(F): chunks[v].append((V,F)); keys[v].append(E)
    field_seconds=time.perf_counter()-t; report('a6_field',field_seconds)
    cache={}; area=float(plan['mask'].sum()*m.g*m.g); limit=budget(area)
    for v in variants:
        t=time.perf_counter(); mesh=H.join(chunks[v]); chunks[v].clear()
        if mesh is None:
            cache[v]=dict(mesh=None,stats=dict(method='a6',empty=True)); continue
        V,F=_a3_weld(*mesh,1e-6,edge_keys=np.vstack(keys[v])); keys[v].clear(); raw_count=len(F)
        report('a6_cleanup',v,raw_count,'raw_tris')
        inside=_a6_hidden(m,V); remove=np.all(inside[F],axis=1)
        V,F=G._compact(V,F[~remove]); kept_before=len(F)
        if len(F):
            V=_a3_taubin(V,F,passes=1)
            V,F=G._decimate(V,F,limit) if len(F)>limit else (V,F)
        stats=dict(method='a6',variant=v,depth=m.thick(v),base_depth=plan['stages'][v]['base'],
                   kernel_radius=plan['stages'][v]['R'],seed=SEED,threshold=THRESHOLD,
                   stiffness=STIFFNESS,surface_density=50/plan['stages'][v]['height']**2,
                   floor_mode='local_carrier_inside_nearest_outside_radius',floor_smooth_m=.005,
                   bank_points=plan['bank_points'],particles=len(plan['clouds'][plan['stages'][v]['base']]['P']),
                   raw_triangles=raw_count,buried_triangles_removed=int(remove.sum()),
                   triangles_before_qem=kept_before,triangles=len(F),budget=limit,
                   pitch=grid['pitch'].tolist(),blocks=len(grid['tiles']),boundary_positive_samples=cropped,
                   cleanup='all_three_corners_buried_2mm_only',planning_seconds=planning,
                   field_seconds_shared=field_seconds,field_seconds_amortized=(planning+field_seconds)/len(variants),
                   cleanup_seconds=time.perf_counter()-t)
        cache[v]=dict(mesh=(V,F),selected=plan['mask'],stats=stats)
    m._snow_a6_cache=cache
    return cache


def build_a6(m,variant):
    """A6: real-addon surface kernels plus vertical field extrusion; no mesh clip."""
    if not hasattr(m,'_snow_a6_cache') or variant not in m._snow_a6_cache:
        prepare_a6(m,(variant,))
    data=m._snow_a6_cache[variant]; m.addon_stats=dict(data['stats'])
    if data['mesh'] is None or not len(data['mesh'][1]): return None
    m._sel|=data['selected']; m._claimed|=data['selected']
    return G._register(m,*data['mesh'],.003,m.g)


def _a7_plan(m):
    """A6 below 6 cm; A5 volume with a moving surface-particle skin above it."""
    # parts a recipe or snow_hand.hybrid hands elsewhere (_sz_exclude: rails/logs/beams with their own crescents) or
    # the only parts that hold snow (_sz_parts); blocked parts also get no spill from a neighbouring kernel
    allowed=getattr(m,'_sz_parts',None); excluded=tuple(getattr(m,'_sz_exclude',None) or ())
    # a recipe (tools/hand) names the parts that hold snow (_sz_parts) and the parts that must not receive any, not even
    # a neighbour's spill (_sz_block: the curve into a bench's backrest)
    blocked=excluded+tuple(getattr(m,'_sz_block',None) or ())
    original=m.tops
    if allowed is not None or excluded:
        keep=np.isin(m.PART,allowed) if allowed is not None else ~np.isin(m.PART,excluded)
        m.tops=lambda *a,**kw:original(*a,**kw)&keep
    try:
        surface=_a6_plan(m)
        volume=_a4_plan(m) if any(s['depth']>s['base']+1e-9 for s in surface['stages'].values()) else None
    finally:
        m.tops=original
    clouds={b:dict(c,threshold=THRESHOLD*_dens(b)) for b,c in surface['clouds'].items()}
    stages={}
    for v,s in surface['stages'].items():
        d=s['depth']; base=s['base']; skin_key=base; volume_key=None
        blend=float(np.clip((d-base)/.02,0,1)); blend=blend*blend*(3-2*blend)
        if d>base+1e-9:
            vc=volume['clouds'][v]; volume_key=('volume',v); clouds[volume_key]=dict(vc)
            skin_key=('skin',v); skin=dict(surface['clouds'][base]); P=skin['P'].copy()
            ii=np.clip(np.rint((P[:,0]-m.u0)/m.g).astype(int),0,m.nu-1)
            jj=np.clip(np.rint((P[:,2]-m.v0)/m.g).astype(int),0,m.nv-1)
            # Put the particle skin on the added thickness, rather than
            # extruding the field. Its uplift tends continuously to zero
            # at 6 cm; the full A5 cloud still supplies the 3D body.
            h=volume['stages'][v]['h']
            # a soft knee where the body thins below the skin (k 3 cm): the flank runs on smoothly instead of a step
            x=h-base; uplift=blend*np.minimum(.03*np.logaddexp(0,x/.03),1.15*(d-base))
            P[:,1]+=uplift[jj,ii]
            skin.update(P=P,threshold=THRESHOLD*_dens(base)); clouds[skin_key]=skin
        stages[v]=dict(s,D=np.zeros_like(s['D']),skin_key=skin_key,volume_key=volume_key,blend=blend)
    return dict(surface,clouds=clouds,stages=stages,volume_bank_points=volume['bank_points'] if volume else 0,
                bench_allowed_parts=list(allowed) if allowed is not None else None,blocked_parts=list(blocked))


def _a7_grid(m,plan):
    grid=_a6_grid(m,plan)
    if plan.get('blocked_parts'):
        g=grid['pitch'][0]; x=grid['origin'][0]+np.arange(grid['shape'][0])*g
        z=grid['origin'][2]+np.arange(grid['shape'][2])*g
        i=np.clip(np.rint((x-m.u0)/m.g).astype(int),0,m.nu-1)
        j=np.clip(np.rint((z-m.v0)/m.g).astype(int),0,m.nv-1)
        # Excluded back boards must not receive spill from a neighbouring
        # kernel either. This fixed emitter-domain mask is common to all depths.
        blocked=np.isin(m.PART[j[:,None],i[None,:]],plan['blocked_parts']).T
        for base in grid['floors']: grid['floors'][base]=np.where(blocked,-np.inf,grid['floors'][base])
    return grid


def _a7_tile(plan,grid,tile,variants):
    pitch=grid['pitch']; core=grid['core']; nb=grid['nb']
    start=np.array(tile)*core; end=np.minimum(start+core,grid['shape']-1); length=end-start+1
    fields={}; outputs={}; cropped=0
    def field(key):
        if key in fields:return fields[key]
        cloud=plan['clouds'][key]; R=cloud['R']; thr=cloud['threshold']; neighbors=[]
        for a in range(max(0,tile[0]-1),min(nb[0],tile[0]+2)):
            for b in range(max(0,tile[1]-1),min(nb[1],tile[1]+2)):
                for c in range(max(0,tile[2]-1),min(nb[2],tile[2]+2)):
                    k=(a*nb[1]+b)*nb[2]+c
                    if k in cloud['groups']:neighbors.append(cloud['groups'][k])
        # a wide kernel (a deep pillow, R up to ~40 cm) is smooth at a fraction of its radius: its field is summed on
        # a coarser lattice aligned to the fine one (R/A7_COARSE) and interpolated back; a narrow one stays fine.
        # Every tile and lattice uses its own halo, so a shallow field no longer pays for the widest kernel.
        fa=np.maximum(1,np.floor(R/(A7_COARSE*pitch)).astype(int)) if A7_COARSE>0 else np.ones(3,int)
        cp=pitch*fa; lo=(start-1)//fa; hi=-(-(end+1)//fa); n=hi-lo+1
        halo=np.ceil(R/cp).astype(int)+2; pstart=lo-halo; full=n+2*halo
        fftshape=tuple(_fftsize(int(q)) for q in full)
        density=np.zeros(int(np.prod(fftshape)),np.float32)
        if neighbors:
            ids=np.concatenate(neighbors); pos=cloud['unit'][ids]/fa-pstart
            good=np.all((pos>=0)&(pos<full-1),axis=1); pos=pos[good];ids=ids[good]
            ijk=np.floor(pos).astype(np.int64); frac=(pos-ijk).astype(np.float32)
            base_w=cloud['weight'][ids].astype(np.float32) if 'weight' in cloud else np.ones(len(ids),np.float32)
            idx=[];ws=[]
            for a in (0,1):
                for b in (0,1):
                    for c in (0,1):
                        idx.append(np.ravel_multi_index(((ijk[:,0]+a),(ijk[:,1]+b),(ijk[:,2]+c)),fftshape))
                        ws.append(base_w*(frac[:,0] if a else 1-frac[:,0])*(frac[:,1] if b else 1-frac[:,1])*(frac[:,2] if c else 1-frac[:,2]))
            if len(ids):density+=np.bincount(np.concatenate(idx),weights=np.concatenate(ws),minlength=density.size).astype(np.float32)
        density=density.reshape(fftshape)
        f=np.fft.irfftn(np.fft.rfftn(density)*_a4_kernel_fft(R,tuple(cp),fftshape),s=fftshape).astype(np.float32)-thr
        f=f[tuple(slice(int(h-1),int(h+q+1)) for h,q in zip(halo,n))]
        gradient=np.sqrt(sum(g_*g_ for g_ in np.gradient(f,*cp)))
        sdf=np.clip(f/np.maximum(gradient,.01*thr/R),-R,R)[1:-1,1:-1,1:-1]
        if np.any(fa>1):
            for ax in range(3):
                x=np.arange(start[ax],end[ax]+1)/fa[ax]-lo[ax]; i0=np.clip(np.floor(x).astype(int),0,sdf.shape[ax]-2)
                t=(x-i0).astype(np.float32); shp=[1,1,1]; shp[ax]=-1; t=t.reshape(shp)
                sdf=np.take(sdf,i0,axis=ax)*(1-t)+np.take(sdf,i0+1,axis=ax)*t
        else: sdf=sdf[1:-1,1:-1,1:-1]
        fields[key]=np.ascontiguousarray(sdf,dtype=np.float32);return fields[key]
    previous=None
    for v in range(1,max(variants)+1):
        stage=plan['stages'][v]; skin=field(stage['skin_key']); current=skin
        if stage['volume_key'] is not None:
            body=field(stage['volume_key'])
            # smooth union (k 4 cm): where the thick body thins out onto the skin the surface rounds over, no step
            k=.04; hh=np.clip(.5+.5*(body-skin)/k,0,1); smax=skin+(body-skin)*hh+k*hh*(1-hh)
            if not A7_SKIN: smax=body
            current=skin+stage['blend']*(smax-skin)
        sl=(slice(int(start[0]),int(end[0])+1),slice(int(start[2]),int(end[2])+1))
        floor=grid['floors'][stage['base']][sl]
        yy=grid['origin'][1]+np.arange(start[1],end[1]+1)*pitch[1]
        # a deep pillow curls under to its support: the cut along the floor is rounded, no flat shelf with a hard rim
        if A7_MINLAYER>0:
            # a sharp crest (a rock's ridge, a box corner) stood out of the smooth particle surface at v1-v4 and read as
            # a hole: every carrier keeps at least a thin layer (vertical, 1-2 cm, tapering out at the cap's edge)
            ml=grid['minlayer']; lo=ml['lo'][sl]; tp=ml['top'][sl]; hm=float(np.clip(A7_MINLAYER*stage['base'],.008,.02))*ml['w'][sl]
            fm=np.minimum(yy[None,:,None]-lo[:,None,:],(tp+hm)[:,None,:]-yy[None,:,None])
            fm=np.where(np.isfinite(lo)[:,None,:]&(hm>1e-4)[:,None,:],fm,-1.)
            current=np.maximum(current,fm)
        current=_smin(current,yy[None,:,None]-floor[:,None,:],max(.005,A7_FLOORK*stage['base']))
        if stage['base'] in grid.get('bands',{}):
            cap,up=(b_[sl] for b_ in grid['bands'][stage['base']]); bm=np.isfinite(cap)
            if bm.any():
                kb=max(.005,.15*stage['base'])
                lower=_smin(current,np.where(bm,cap,1e3)[:,None,:]-yy[None,:,None],kb)
                upper=_smin(current,yy[None,:,None]-np.where(bm,up,-1e3)[:,None,:],kb)
                current=np.where(bm[:,None,:],np.maximum(lower,upper),current)
        if A7_OVL>0:
            # a pillow hangs over its carrier's edge by about a third of its depth at most: a post, bin or box keeps
            # a cap, not a mushroom. A smooth intersection, so the lip stays round
            o=_ovl(stage['base']); D=grid['dists'][stage['base']][sl]
            current=_smin(current,(o-D)[:,None,:],A7_OVK*o)
        current=np.where(np.isfinite(floor)[:,None,:],current,-grid['maxR'])
        # Nested 3D isosurfaces, including the switch from surface to volume.
        # This is a union of fields, not a vertical extrusion or a height rewrite.
        if previous is not None:current=np.maximum(current,previous)
        previous=current
        if v not in variants:continue
        V,F,E=G._march(current-3.14159e-7,grid['origin']+start*pitch,pitch,return_edges=True)
        E=E+start; keys=(E[:,:,0]*grid['shape'][1]+E[:,:,1])*grid['shape'][2]+E[:,:,2]
        for axis in range(3):
            if start[axis]==0:cropped+=int((np.take(current,0,axis=axis)>0).sum())
            if end[axis]==grid['shape'][axis]-1:cropped+=int((np.take(current,-1,axis=axis)>0).sum())
        outputs[v]=(V,F,keys)
    return outputs,cropped


def _a7_raster(V,F,grid):
    """QA-only vertical samples of the actual triangles; never builds a cap (vectorised: all cells under all triangles
    at once, in chunks; the highest triangle wins)."""
    x0,z0,g,nx,nz=grid; Y=np.full((nz,nx),-np.inf); tid=np.full((nz,nx),-1,np.int32)
    if not len(F): return Y,tid
    t=V[F]; a,b,c=t[:,0],t[:,1],t[:,2]
    den=(b[:,2]-c[:,2])*(a[:,0]-c[:,0])+(c[:,0]-b[:,0])*(a[:,2]-c[:,2])
    i0=np.maximum(0,np.ceil((t[:,:,0].min(1)-x0)/g-1e-7).astype(np.int64)); i1=np.minimum(nx-1,np.floor((t[:,:,0].max(1)-x0)/g+1e-7).astype(np.int64))
    j0=np.maximum(0,np.ceil((t[:,:,2].min(1)-z0)/g-1e-7).astype(np.int64)); j1=np.minimum(nz-1,np.floor((t[:,:,2].max(1)-z0)/g+1e-7).astype(np.int64))
    w=np.maximum(i1-i0+1,0); h=np.maximum(j1-j0+1,0); n=np.where(np.abs(den)>=1e-14,w*h,0)
    ids=np.flatnonzero(n); Yf=Y.ravel(); Tf=tid.ravel()
    cum=np.cumsum(n[ids]); lo=0
    while lo<len(ids):
        hi=int(np.searchsorted(cum,(cum[lo-1] if lo else 0)+2000000,side='right')); hi=max(hi,lo+1)
        k=ids[lo:hi]; cnt=n[k]; tot=int(cnt.sum()); lo=hi
        kk=np.repeat(k,cnt); off=np.arange(tot)-np.repeat(np.cumsum(cnt)-cnt,cnt)
        i=i0[kk]+off%w[kk]; j=j0[kk]+off//w[kk]; x=x0+i*g; z=z0+j*g
        A,B,C,D=a[kk],b[kk],c[kk],den[kk]
        u=((B[:,2]-C[:,2])*(x-C[:,0])+(C[:,0]-B[:,0])*(z-C[:,2]))/D
        v=((C[:,2]-A[:,2])*(x-C[:,0])+(A[:,0]-C[:,0])*(z-C[:,2]))/D
        hit=(u>=-1e-7)&(v>=-1e-7)&(u+v<=1+1e-7)
        y=(u*A[:,1]+v*B[:,1]+(1-u-v)*C[:,1])[hit]; f=(j*nx+i)[hit]; kk=kk[hit]
        np.maximum.at(Yf,f,y)
        top=y>=Yf[f]; Tf[f[top]]=kk[top]
    return Y,tid


def _a7_growth_guard(m,V,F,previous):
    """Conservative millimetre corrections after QEM, against the prior mesh.

    No height-field reconstruction: keep the 3D mesh/connectivity and budget.
    Moving upper-face vertices up conservatively removes QEM's small inward
    error. Lost edge samples get a local boundary displacement first.
    """
    if previous is None or not len(F) or not len(previous[1]):return V,dict(lowered_cells=0,lost_columns=0,iterations=0,max_move_m=0.)
    from mathutils.bvhtree import BVHTree
    oldV,oldF=previous; original=V.copy(); g=min(.01,m.g)
    lo=np.minimum(oldV.min(0),V.min(0)); hi=np.maximum(oldV.max(0),V.max(0))
    x0=math.floor((lo[0]-.05)/g)*g-g/2; z0=math.floor((lo[2]-.05)/g)*g-g/2
    grid=(x0,z0,g,int(math.ceil((hi[0]+.05-x0)/g))+2,int(math.ceil((hi[2]+.05-z0)/g))+2)
    old,_=_a7_raster(oldV,oldF,grid); existed=np.isfinite(old)
    initial=None; too_far=0
    for iteration in range(10):
        new,ids=_a7_raster(V,F,grid); lost=existed&~np.isfinite(new)
        lower=existed&np.isfinite(new)&(new<old-.00005)
        displaced=lost|(lower&(new<old-.008))
        if initial is None:initial=dict(initial_lowered_3mm=int((existed&(new<old-.003)).sum()),initial_lost=int(lost.sum()))
        if not lost.any() and not lower.any():break
        if displaced.any():
            t=V[F]; n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]); n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-15)
            upper=np.flatnonzero(np.abs(n[:,1])>.0001)
            if not len(upper):break
            bvh=BVHTree.FromPolygons(V.tolist(),F[upper].tolist(),all_triangles=True)
            displacement=np.zeros_like(V); count=np.zeros(len(V))
            jj,ii=np.nonzero(displaced)
            for j,i in zip(jj.tolist(),ii.tolist()):
                point=np.array((x0+i*g,old[j,i]+.0002,z0+j*g))
                q,_,face,distance=bvh.find_nearest(Vector(point)); q=np.array(q)
                if distance>.03:too_far+=1;continue
                face=F[upper[face]]; a,b,c=V[face]; e=b-a; f=c-a; h=q-a
                den=np.dot(e,e)*np.dot(f,f)-np.dot(e,f)**2
                u=(np.dot(f,f)*np.dot(h,e)-np.dot(e,f)*np.dot(h,f))/max(den,1e-20)
                w=(np.dot(e,e)*np.dot(h,f)-np.dot(e,f)*np.dot(h,e))/max(den,1e-20)
                active=face[np.array((1-u-w,u,w))>1e-6]
                delta=point-q; delta[1]=max(0,delta[1]); xy=np.linalg.norm(delta[[0,2]])
                if xy>1e-8:delta[[0,2]]*=1+.00015/xy
                displacement[active]+=delta;count[active]+=1
            take=count>0;V[take]+=displacement[take]/count[take,None]
            new,ids=_a7_raster(V,F,grid); lower=existed&np.isfinite(new)&(new<old-.00005)
        # A vertical ray can fall onto a DIFFERENT log below a lost edge.
        # Never lift that lower carrier to the old upper cap. Such a sample
        # must be repaired through nearby 3D geometry in the pass above.
        lower&=new>=old-.008
        if lower.any():
            delta=old[lower]-new[lower]+.0002
            shift=np.zeros(len(V)); np.maximum.at(shift,F[ids[lower]].ravel(),np.repeat(delta,3))
            V[:,1]+=shift
    new,_=_a7_raster(V,F,grid)
    common=existed&np.isfinite(new)
    return V,dict(**(initial or {}),lowered_cells=int((existed&(new<old-.003)).sum()),
                  lost_columns=int((existed&~np.isfinite(new)).sum()),iterations=iteration+1,
                  max_drop_m=float(np.max(old[common]-new[common],initial=0)),
                  max_move_m=float(np.linalg.norm(V-original,axis=1).max(initial=0)),unrepaired_distant_samples=too_far)


def prepare_a7(m,variants=tuple(range(1,8)),workers=4):
    from concurrent.futures import ThreadPoolExecutor
    report=getattr(m,'_addon_log',lambda *a:None); start=time.perf_counter(); plan=_a7_plan(m)
    if not any(len(c['P']) for c in plan['clouds'].values()):
        # nothing wide and open enough to hold snow (thin tubes, a mesh fence): no cap in any depth
        m._snow_a7_cache={v:dict(mesh=None,stats=dict(method='a7',empty=True,variant=v)) for v in range(1,8)}
        return m._snow_a7_cache
    grid=_a7_grid(m,plan)
    planning=time.perf_counter()-start
    # All predecessors must be built for the final-mesh growth guarantee.
    wanted=tuple(range(1,max(variants)+1)); representatives={}
    for v in wanted:representatives.setdefault(m.thick(v),v)
    extract=tuple(representatives.values()); chunks={v:[] for v in extract}; keys={v:[] for v in extract}; cropped=0
    report('a7_plan',len(grid['tiles']),'blocks',grid['pitch'].tolist(),'volume_bank',plan['volume_bank_points'])
    t=time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for result,boundary in pool.map(lambda tile:_a7_tile(plan,grid,tile,extract),grid['tiles']):
            cropped+=boundary
            for v,(V,F,E) in result.items():
                if len(F):chunks[v].append((V,F));keys[v].append(E)
    field_seconds=time.perf_counter()-t;report('a7_field',field_seconds)
    cache={};previous=None;area=float(plan['mask'].sum()*m.g*m.g)
    for v in wanted:
        same=representatives[m.thick(v)]
        if same!=v:
            cache[v]=dict(cache[same]);cache[v]['stats']=dict(cache[same]['stats'],variant=v,reused_variant=same,cleanup_seconds=0.)
            previous=cache[v]['mesh'];continue
        # deeper snow has taller sides and more lumps to carry: the budget grows with the depth
        limit=budget(area*(1+4*m.thick(v)))
        t=time.perf_counter(); mesh=H.join(chunks[v]);chunks[v].clear()
        if mesh is None:
            cache[v]=dict(mesh=None,stats=dict(method='a7',empty=True));continue
        steps={}; t0=time.perf_counter()
        V,F=_a3_weld(*mesh,1e-6,edge_keys=np.vstack(keys[v]));keys[v].clear();raw_count=len(F)
        report('a7_cleanup',v,raw_count); steps['weld']=time.perf_counter()-t0; t0=time.perf_counter()
        inside=_a6_hidden(m,V); hidden=np.all(inside[F],axis=1)
        # (Opus, 6 Oct) the cut along the floor under a single-sided sheet (a doghouse roof: 3 mm sink, under the 5 mm
        # buried test) stayed: the cap was closed, had no foot and the prune dropped it whole. Downward faces just under
        # the carrier of their own column are that cut
        hidden|=_floor_faces(m,V,F,plan['mask'])
        V,F=G._compact(V,F[~hidden])
        steps['hidden']=time.perf_counter()-t0; t0=time.perf_counter()
        if len(F):
            # small props stay smooth up close: the tolerance also shrinks with the size of the cap
            V=_a3_taubin(V,F,passes=A7_TAUBIN if m.thick(v)>.06 else 1); steps['taubin']=time.perf_counter()-t0; t0=time.perf_counter()
            # (a fence or wall (kind 1) is placed by the thousand: its caps 2500 triangles at most)
            wallcap=(A7_WALLCAP_ROUGH if (getattr(m,'rough',False) or m.cls=='rock') else A7_WALLCAP)
            V,F=_err_decimate(V,F,min(_cap_budget(area),wallcap) if getattr(m,'kind',0)==1 else _cap_budget(area),min(_err_tol(m.thick(v)),.004+.002*math.sqrt(area)))
            steps['decimate']=time.perf_counter()-t0; t0=time.perf_counter()
            # crumbs, knobs and floating balls go (under 0.01 m2, narrower than 4 cm, or touching nothing)
            V,F,pruned=_a4_prune(m,V,F); steps['prune']=time.perf_counter()-t0; t0=time.perf_counter()
            V,guard=_a7_growth_guard(m,V,F,previous); steps['guard']=time.perf_counter()-t0
            guard['pruned_components']=pruned
        else:guard=dict(lowered_cells=0,lost_columns=0,empty=True)
        guard['steps']={k:round(x,2) for k,x in steps.items()}; guard['dense_after_hidden']=int(raw_count-hidden.sum())
        stats=dict(method='a7',variant=v,depth=m.thick(v),base_depth=plan['stages'][v]['base'],
                   blend=plan['stages'][v]['blend'],seed=SEED,triangles=len(F),budget=limit,
                   raw_triangles=raw_count,buried_triangles_removed=int(hidden.sum()),
                   pitch=grid['pitch'].tolist(),blocks=len(grid['tiles']),boundary_positive_samples=cropped,
                   rough_flag=m.rough,bench_allowed_parts=plan['bench_allowed_parts'],growth_guard=guard,
                   floor_mode='local_carrier_inside_nearest_outside_radius',
                   planning_seconds=planning,field_seconds_shared=field_seconds,
                   field_seconds_amortized=(planning+field_seconds)/len(wanted),cleanup_seconds=time.perf_counter()-t)
        cache[v]=dict(mesh=(V,F),selected=plan['mask'],stats=stats);previous=(V,F)
        report('a7_growth',v,guard)
    m._snow_a7_cache=cache;return cache


def build(m,variant):
    """A7 hybrid; previous builders remain explicit build_a2/a3/a5/a6 calls."""
    # all seven depths at once: one field, and the growth guard sees every shallower depth
    if not hasattr(m,'_snow_a7_cache') or variant not in m._snow_a7_cache:prepare_a7(m,tuple(range(1,8)))
    data=m._snow_a7_cache[variant];m.addon_stats=dict(data['stats'])
    if data['mesh'] is None or not len(data['mesh'][1]):return None
    m._sel|=data['selected'];m._claimed|=data['selected']
    return G._register(m,*data['mesh'],.003,m.g)
