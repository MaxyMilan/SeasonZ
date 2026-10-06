"""Rock snow drapes, cut at continuous holding contours on the source surface.

All seven variants share one source tessellation. Holding and surface height
grow cumulatively; the cut crosses facets instead of selecting whole faces.
The visible body has >=6 mm clearance. Only its narrow, explicit contact band
descends to the 3 mm embedded boundary. Coordinates are metres, Y up.
"""
import math
import numpy as np
import snow_hand as H


def _smooth(a, valid, radius, passes=3):
    for _ in range(passes):
        a=H.blur(a,valid,radius)
    return a


def _edges(f):
    e=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1)
    return np.unique(e,axis=0,return_counts=True)


def _boundary(f,n):
    edges,counts=_edges(f)
    foot=np.zeros(n,bool)
    foot[np.unique(edges[counts==1])]=True
    return foot,edges[counts==1]


def _subdivide(v,f,limit):
    """Conforming longest-edge bisection; every new base point stays on rock."""
    for _ in range(14):
        edges=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1)
        edges,counts=np.unique(edges,axis=0,return_counts=True)
        room=limit-len(f)
        if room<2:
            break
        length=np.linalg.norm(v[edges[:,0]]-v[edges[:,1]],axis=1)
        order=np.argsort(-length)
        chosen=order[np.cumsum(counts[order])<=min(room,max(3,room//2))]
        if not len(chosen):
            break
        mids={tuple(edges[q]):len(v)+i for i,q in enumerate(chosen)}
        v=np.vstack([v,(v[edges[chosen,0]]+v[edges[chosen,1]])*.5])
        out=[]
        for a,b,c in f.tolist():
            ab=mids.get(tuple(sorted((a,b))))
            bc=mids.get(tuple(sorted((b,c))))
            ca=mids.get(tuple(sorted((c,a))))
            bits=(ab is not None)+2*(bc is not None)+4*(ca is not None)
            if bits==0: out.append((a,b,c))
            elif bits==1: out.extend(((a,ab,c),(ab,b,c)))
            elif bits==2: out.extend(((a,b,bc),(a,bc,c)))
            elif bits==4: out.extend(((a,b,ca),(ca,b,c)))
            elif bits==3: out.extend(((ab,b,bc),(a,ab,c),(ab,bc,c)))
            elif bits==5: out.extend(((a,ab,ca),(ab,b,c),(ab,c,ca)))
            elif bits==6: out.extend(((ca,bc,c),(a,b,ca),(b,bc,ca)))
            else: out.extend(((a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)))
        f=np.asarray(out,dtype=np.int64)
    return v,f




def _compact(v,f,a):
    used,inv=np.unique(f,return_inverse=True)
    return v[used],inv.reshape(-1,3),a[used]


def _cut(v,f,a,scalar,discard=True):
    """Cut every crossing edge once; attributes follow the original facet.

    discard=False retains both sides, inserting an explicit narrow rim ring.
    """
    vs=list(v)
    attrs=list(a)
    values=list(scalar)
    edge_points={}
    out=[]
    def crossing(i,j):
        if abs(values[i])<1e-12: return i
        if abs(values[j])<1e-12: return j
        edge=tuple(sorted((i,j)))
        if edge not in edge_points:
            t=values[i]/(values[i]-values[j])
            edge_points[edge]=len(vs)
            vs.append(vs[i]+t*(vs[j]-vs[i]))
            attrs.append(attrs[i]+t*(attrs[j]-attrs[i]))
            values.append(0.)
        return edge_points[edge]
    for row in f.tolist():
        signs=[values[i]>0 for i in row]
        if all(signs):
            out.append(row)
            continue
        if not any(signs):
            if not discard: out.append(row)
            continue
        for positive in ((True,) if discard else (True,False)):
            poly=[]
            for i,j in zip(row,row[1:]+row[:1]):
                si,sj=values[i]>0,values[j]>0
                if si==positive: poly.append(i)
                if si!=sj: poly.append(crossing(i,j))
            poly=list(dict.fromkeys(poly))
            for j in range(1,len(poly)-1): out.append((poly[0],poly[j],poly[j+1]))
    if not out: return None
    return _compact(np.asarray(vs),np.asarray(out,dtype=np.int64),np.asarray(attrs))


def _components(v,f,a):
    uf=H.UF(len(v))
    for i,j,k in f:
        uf.union(int(i),int(j)); uf.union(int(i),int(k))
    roots=np.array([uf.find(int(i)) for i in f[:,0]])
    return [_compact(v,f[roots==root],a) for root in np.unique(roots)]


def _distance(p,v,edges):
    """Distance to an actual boundary segment, not to its tessellation vertices."""
    result=np.full(len(p),np.inf)
    for lo in range(0,len(p),256):
        q=p[lo:lo+256]
        best=np.full(len(q),np.inf)
        for begin in range(0,len(edges),256):
            e=edges[begin:begin+256]
            start=v[e[:,0]]
            delta=v[e[:,1]]-start
            d=q[:,None,:]-start[None,:,:]
            t=np.clip(np.einsum('ijk,jk->ij',d,delta)/np.maximum((delta*delta).sum(1),1e-16),0,1)
            residual=d-t[:,:,None]*delta[None,:,:]
            best=np.minimum(best,np.min(np.einsum('ijk,ijk->ij',residual,residual),axis=1))
        result[lo:lo+len(q)]=np.sqrt(best)
    return result


def _surface(v,f,target,radius):
    """Locally fit planes with Gaussian weights, then add smooth obstacle lifts.

    Area weights and a fitted plane avoid the height bias of averaging samples
    on an uneven triangulation. Unlike pointwise clamping, broad Gaussian lifts
    round over convex rock corners without introducing isolated raised vertices.
    """
    tri=v[f]
    ar=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)/6
    mass=np.zeros(len(v))
    for k in range(3): np.add.at(mass,f[:,k],ar)
    out=np.empty(len(v))
    radius=max(radius,.02)
    for lo in range(0,len(v),160):
        q=v[lo:lo+160]
        delta=v[None,:,:]-q[:,None,:]
        dx,dz=delta[:,:,0],delta[:,:,2]
        r2=dx*dx+dz*dz
        w=np.exp(-.5*r2/(radius*radius))*mass[None,:]
        w*=r2<9*radius*radius
        w*=np.abs(delta[:,:,1])<2.0*np.sqrt(r2)+.035
        basis=np.stack([np.ones_like(dx),dx/radius,dz/radius],axis=2)
        lhs=np.einsum('bn,bni,bnj->bij',w,basis,basis)
        rhs=np.einsum('bn,bni,n->bi',w,basis,target)
        lhs+=np.eye(3)[None,:,:]*np.maximum(w.sum(1),1e-12)[:,None,None]*1e-8
        out[lo:lo+len(q)]=np.linalg.solve(lhs,rhs[:,:,None])[:,0,0]
    gap=np.maximum(v[:,1]+.0065-out,0.)
    bad=np.flatnonzero(gap>1e-7)
    if len(bad):
        for lo in range(0,len(v),256):
            q=v[lo:lo+256]
            d=q[:,None,:]-v[bad][None,:,:]
            r2=d[:,:,0]**2+d[:,:,2]**2
            weights=np.exp(-.5*r2/(radius*radius))
            weights*=np.abs(d[:,:,1])<2.0*np.sqrt(r2)+.035
            out[lo:lo+len(q)]+=np.max(weights*gap[bad][None,:],axis=1)*1.0001
    return out


def _loops(v,f):
    _,edges=_boundary(f,len(v))
    by={}
    for a,b in edges:
        by.setdefault(int(a),[]).append(int(b)); by.setdefault(int(b),[]).append(int(a))
    unused={tuple(sorted(map(int,e))) for e in edges}
    loops=[]
    while unused:
        a,b=min(unused); unused.remove((a,b))
        path=[a,b]
        while path[-1]!=path[0]:
            opts=[c for c in by[path[-1]] if tuple(sorted((path[-1],c))) in unused]
            if not opts: break
            c=opts[0]
            unused.remove(tuple(sorted((path[-1],c))))
            path.append(c)
        if path[-1]==path[0] and len(path)>3:
            p=v[path[:-1]][:,[0,2]]
            p=H.simplify_loop(p,.0015)
            loops.append(p)
    return loops


def _cdt(loops,inner,candidates):
    from mathutils import Vector
    from mathutils.geometry import delaunay_2d_cdt
    import collections
    pts=[]; edges=[]
    for loop in loops+inner:
        k=len(pts); pts.extend(loop)
        edges.extend((k+j,k+(j+1)%len(loop)) for j in range(len(loop)))
    outer_edges=sum(len(loop) for loop in loops)
    pts.extend(candidates)
    res=delaunay_2d_cdt([Vector(tuple(p)) for p in pts],edges,[],0,1e-7,True)
    p=np.array([tuple(q) for q in res[0]])
    f=np.array(res[2],dtype=np.int64).reshape(-1,3)
    n=len(p)
    con={min(a,b)*n+max(a,b) for (a,b),orig in zip(res[1],res[4]) if any(q<outer_edges for q in orig)}
    by=collections.defaultdict(list)
    for k,row in enumerate(f):
        for a,b in zip(row,np.roll(row,-1)): by[min(a,b)*n+max(a,b)].append(k)
    parity=np.full(len(f),-1)
    queue=collections.deque()
    for edge,rows in by.items():
        if len(rows)==1 and parity[rows[0]]<0:
            parity[rows[0]]=int(edge in con); queue.append(rows[0])
    while queue:
        k=queue.popleft()
        for a,b in zip(f[k],np.roll(f[k],-1)):
            edge=min(a,b)*n+max(a,b)
            for q in by[edge]:
                if parity[q]<0:
                    parity[q]=parity[k]^int(edge in con); queue.append(q)
    f=f[parity==1]
    used,inv=np.unique(f,return_inverse=True)
    return p[used],inv.reshape(-1,3)


def _remesh(m,vb,fb,ab,dist,source,source_faces,top,budget):
    from mathutils import Vector
    outer=_loops(vb,fb)
    innercut=_cut(vb,fb,ab,dist-.006)
    inner=_loops(innercut[0],innercut[1]) if innercut is not None else []
    projected=np.abs(np.cross(vb[fb[:,1]]-vb[fb[:,0]],vb[fb[:,2]]-vb[fb[:,0]])[:,1]).sum()/2
    step=max(.018,math.sqrt(projected*2.6/max(budget-500,100)))
    lo=vb[:,[0,2]].min(0); hi=vb[:,[0,2]].max(0)
    yy,xx=np.mgrid[lo[1]:hi[1]:step*.8660254,lo[0]:hi[0]:step]
    xx[1::2]+=step*.5
    cand=np.column_stack([xx.ravel(),yy.ravel()])
    cand=cand[H.inside_loops(cand,outer)]
    if len(cand): cand=cand[H.loop_dist(cand,outer+inner)>step*.28]
    p,f=_cdt(outer,inner,cand)
    base=np.empty(len(p))
    sky=float(m.V[:,1].max()+1)
    for k,(x,z) in enumerate(p):
        hit=m.bvh_all.ray_cast(Vector((float(x),sky,float(z))),Vector((0,-1,0)),1e4)[0]
        base[k]=hit.y if hit is not None else np.interp(x,vb[:,0],vb[:,1])
    v=np.column_stack([p[:,0],base,p[:,1]])
    # A regular Delaunay surface removes the long, skinny source-mesh fans.
    # Resample the smooth crown using a compact local plane fit.
    radius=max(.025,step*.8)
    vals=np.empty(len(v))
    for lo in range(0,len(v),128):
        q=v[lo:lo+128]
        delta=source[None,:,:]-q[:,None,:]
        dx,dz=delta[:,:,0],delta[:,:,2]
        r2=dx*dx+dz*dz
        w=np.exp(-.5*r2/(radius*radius))
        w*=r2<12*radius*radius
        w*=np.abs(delta[:,:,1])<2.0*np.sqrt(r2)+.035
        basis=np.stack([np.ones_like(dx),dx/radius,dz/radius],axis=2)
        lhs=np.einsum('bn,bni,bnj->bij',w,basis,basis)
        rhs=np.einsum('bn,bni,n->bi',w,basis,top)
        lhs+=np.eye(3)[None,:,:]*np.maximum(w.sum(1),1e-12)[:,None,None]*1e-8
        vals[lo:lo+len(q)]=np.linalg.solve(lhs,rhs[:,:,None])[:,0,0]
    d=H.loop_dist(p,outer)
    return v,f,np.column_stack([vals,np.zeros(len(v)),d])


def _prepare(m,budget,depth,angle0,angle7,smooth,parts):
    from mathutils import Vector
    # This permissive domain excludes vertical/hidden faces only. Snow edges
    # are determined later by a continuous weight inside the source facets.
    selected=m.good_t & (m.ny_t>.18)
    if parts is not None: selected &= np.isin(m.part_t,parts)
    centers=m.V[m.T].mean(1)
    selected &= centers[:,1]>m.ground-.04
    sky=float(m.V[:,1].max()+1.)
    for k in np.flatnonzero(selected):
        p=centers[k]
        hit=m.bvh_all.ray_cast(Vector((float(p[0]),sky,float(p[2]))),Vector((0,-1,0)),1e4)[0]
        if hit is None or abs(hit.y-p[1])>.006: selected[k]=False
    source=m.T[selected]
    used,inv=np.unique(source,return_inverse=True)
    v=m.V[used].copy()
    _,ix,iv=np.unique(np.round(v/1e-6).astype(np.int64),axis=0,return_index=True,return_inverse=True)
    v=v[ix]; f=iv[inv].reshape(-1,3)
    v,f=_subdivide(v,f,max(len(f),int(budget*.86)))
    exposure=np.ones(len(v))
    for k,p in enumerate(v):
        hit=m.bvh_all.ray_cast(Vector((float(p[0]),sky,float(p[2]))),Vector((0,-1,0)),1e4)[0]
        if hit is None or hit.y-p[1]>.008: exposure[k]=0.
    ij=np.column_stack(m.ij(v[:,0],v[:,2]))
    raw=m.n_t[np.maximum(m.TID,0)].copy()
    raw*=np.where(raw[:,:,1]<0,-1.,1.)[:,:,None]
    prev=np.zeros(len(v))
    prev_grid=np.zeros_like(m.Z)
    prev_top=v[:,1]+.0065
    fields=[]
    for var in range(1,8):
        t=m.thick(var)*depth
        r=max(1,round((.04+.35*t)*smooth/m.g))
        ns=np.stack([_smooth(raw[:,:,k],m.valid,r) for k in range(3)],axis=2)
        ny=ns[:,:,1]/np.maximum(np.linalg.norm(ns,axis=2),1e-12)
        # Opposing steep faces may average to an upward vector. Their scalar
        # normal still records the steepness, preventing a false flat support
        # across a crack deeper than this snow layer can fill.
        scalar=_smooth(m.NYF,m.valid,r)
        ny=np.minimum(ny,scalar+.15*t)
        cutoff=math.cos(math.radians(angle0+(angle7-angle0)*(var-1)/6))
        wg=H.SC.smoothstep((ny-cutoff)/(.95-cutoff))
        wg*=H.SC.smoothstep((np.nan_to_num(m.Z)-m.ground-.015)/.07)
        # Preserve a real change of level. A very narrow ledge/occluder can
        # disappear in averaged normals although its height jump is much
        # deeper than this layer of snow. Taper continuously on both sides.
        z=np.nan_to_num(m.Z)
        cliff=np.zeros_like(m.valid)
        limit=2.2*m.g+.25*t
        dx=m.valid[:,1:] & m.valid[:,:-1] & (np.abs(z[:,1:]-z[:,:-1])>limit)
        dz=m.valid[1:,:] & m.valid[:-1,:] & (np.abs(z[1:,:]-z[:-1,:])>limit)
        cliff[:,1:]|=dx; cliff[:,:-1]|=dx
        cliff[1:,:]|=dz; cliff[:-1,:]|=dz
        room=H.distance(m.valid & ~cliff,max(2,math.ceil(.07/m.g)))*m.g
        wg*=H.SC.smoothstep(room/.04)
        wg=np.where(m.valid,wg,0.)
        wg=np.maximum(wg,prev_grid); prev_grid=wg
        w=H.bilinear(wg,ij[:,0],ij[:,1])*exposure
        amount=np.maximum(t*w,prev); prev=amount
        wanted=.0065+np.maximum(amount-.009,0.)*(t-.0065)/max(t-.009,.001)
        top=_surface(v,f,v[:,1]+wanted,(.03+.45*t)*smooth)
        top=np.maximum(top,prev_top); prev_top=top
        fields.append((amount,top,wg*t))
    return v,f,fields


def _intended(m,v,f,dist):
    """Rasterise the retained support, independently of the raised snow surface."""
    grid=np.zeros_like(m._sel)
    for row in f:
        tri=v[row]
        ij=np.column_stack(m.ij(tri[:,0],tri[:,2]))
        lo=np.maximum(np.ceil(ij.min(0)).astype(int),[0,0])
        hi=np.minimum(np.floor(ij.max(0)).astype(int),[m.nu-1,m.nv-1])
        if np.any(hi<lo): continue
        ii,jj=np.meshgrid(np.arange(lo[0],hi[0]+1),np.arange(lo[1],hi[1]+1))
        a,b,c=ij
        den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-10: continue
        w0=((b[1]-c[1])*(ii-c[0])+(c[0]-b[0])*(jj-c[1]))/den
        w1=((c[1]-a[1])*(ii-c[0])+(a[0]-c[0])*(jj-c[1]))/den
        w2=1-w0-w1
        inside=(w0>=0)&(w1>=0)&(w2>=0)
        height=w0*tri[0,1]+w1*tri[1,1]+w2*tri[2,1]
        depth=w0*dist[row[0]]+w1*dist[row[1]]+w2*dist[row[2]]
        ok=inside & (depth>.015) & (np.abs(m.Z[jj,ii]-height)<.008)
        grid[jj,ii]|=ok
    return grid


def drape(m,variant,*,budget=3800,depth=1.,angle0=49.,angle7=63.,smooth=1.,
          parts=None,support_extra=0.,seed_shelves=True,min_area=.01,min_width=.04):
    """Build the continuous open rock shell; legacy recipe keywords are accepted."""
    key=(budget,depth,angle0,angle7,smooth,tuple(parts) if parts is not None else None)
    if not hasattr(m,'_rock_cache'): m._rock_cache={}
    if key not in m._rock_cache: m._rock_cache[key]=_prepare(m,*key[:-1],key[-1])
    v,f,fields=m._rock_cache[key]
    amount,top,expected=fields[variant-1]
    attrs=np.column_stack([top,amount])
    cut=_cut(v,f,attrs,amount-.009)
    if cut is None: return None
    meshes=[]
    patches=[]
    pieces=_components(*cut)
    full_area=sum(np.linalg.norm(np.cross(q[0][q[1][:,1]]-q[0][q[1][:,0]],q[0][q[1][:,2]]-q[0][q[1][:,0]]),axis=1).sum()/2 for q in pieces)
    for vb,fb,ab in pieces:
        tri=vb[fb]
        area=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1).sum()*.5
        foot,edges=_boundary(fb,len(vb))
        if area<min_area or not len(edges): continue
        dist=_distance(vb,vb,edges)
        width=max(float(dist.max()),float(_distance(tri.mean(1),vb,edges).max()))*2
        if width<min_width: continue
        intended=_intended(m,vb,fb,dist)
        # Insert a narrow contact band explicitly: normal-sized body triangles
        # cannot spread a 0..6 mm glossy skin over a whole source face.
        vb,fb,ab=_remesh(m,vb,fb,ab,dist,v,f,top,max(150,int(budget*area/max(full_area,1e-8))))
        d=ab[:,2]
        t=m.thick(variant)*depth
        body=np.maximum(ab[:,0]-vb[:,1],.0065)
        shoulder=H.SC.smoothstep(d/max(.025,.28*t))
        body=.0065+(body-.0065)*shoulder
        dep=-.003+(body+.003)*H.SC.smoothstep(d/.006)
        out=vb.copy(); out[:,1]+=dep
        normals=np.cross(out[fb[:,1]]-out[fb[:,0]],out[fb[:,2]]-out[fb[:,0]])
        fb[normals[:,1]<0]=fb[normals[:,1]<0][:,[0,2,1]]
        foot,_=_boundary(fb,len(vb))
        out[foot,1]=vb[foot,1]-.003
        m._caps.append(dict(V=out,F=fb,role=np.where(foot,3,0),anchor=np.full(len(out),-1),foot=foot))
        sel=intended
        m._sel|=sel; m._soft|=H.dilate(sel,3); m._claimed|=sel
        meshes.append((out,fb))
        patches.append(dict(area=area,width=width,triangles=len(fb),body_min=float(dep[d>=.006-1e-9].min()) if (d>=.006-1e-9).any() else 0.))
    m._rock_patches=patches
    return H.join(meshes)
