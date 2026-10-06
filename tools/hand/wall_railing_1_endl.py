"""wall_railing_1_endl: 40 mm hexagonal round steel railing with a bent end.

Part 0: lower pipe, shelter-aware m.log crescent. Part 1: connected upper
pipe, diagonal downturn and terminal legs. Use m.log for each supported
horizontal/diagonal run; vertical legs hold none. Part 2 is the separate middle upright;
their tops terminate inside the upper pipe, so no exposed flat tops require
blankets. There are no flat-topped beams or crumb caps.

Fit each horizontal run to its actual free-end cross section repeated at
the two span limits. This prevents duplicate source vertices and the mitre
from tilting its fitted axis. Fit the diagonal to its actual rings, excluding
embedded vertical-post ring vertices at y=.59134. Shallow copies retain the
full collision mesh, shelter and cap/check records. Fit free coplanar pipe ends
0.01 mm inside the source end plane to avoid exact-boundary BVH misses;
the whole-station wood-support rule remains active.

The two original log tapers left a visible seam at the supported mitre.
Replace just that seam with a 5 mm sampled tangent-continuous bridge of
the log profiles. Its crown is held 3 mm above actual raycast metal, its
outer feet stay buried, and five local relaxations soften the crown.
Retain the original log geometry at both external ends. The bridge is a
single welded strip, and its replacement cap record includes every real
top vertex and only physical boundary feet for unmodified hc checks.
"""
from copy import copy
import numpy as np
from mathutils import Vector
import snow_hand as H


def _bridge(m, a, b, knee, smooth=5, clearance=.003, width=.04):
    k=15
    sign=1 if knee<0 else -1
    A,B=a[0].reshape(-1,k,3),b[0].reshape(-1,k,3)
    A=A[np.argsort(-sign*A[:,:,2].mean(1))]
    B=B[np.argsort(-sign*B[:,:,2].mean(1))]
    if A[0,0,0]>A[0,-1,0]: A=A[:,::-1]
    if B[0,0,0]>B[0,-1,0]: B=B[:,::-1]
    A=A[sign*A[:,:,2].mean(1)>sign*knee+width]
    B=B[sign*B[:,:,2].mean(1)<sign*knee-width]
    u=lambda row:-sign*row[:,2].mean()
    length=u(B[0])-u(A[-1])
    ta=(A[-1]-A[-2])/(u(A[-1])-u(A[-2]))*length
    tb=(B[1]-B[0])/(u(B[1])-u(B[0]))*length
    t=np.linspace(0,1,int(np.ceil(length/.005))+1)[:,None,None]
    patch=(2*t**3-3*t**2+1)*A[-1]+(t**3-2*t**2+t)*ta+(-2*t**3+3*t**2)*B[0]+(t**3-t**2)*tb
    floor=np.full(patch.shape[:2],-np.inf)
    for j in range(len(patch)):
        for q in range(k):
            p=patch[j,q]
            hit=m.bvh_all.ray_cast(Vector((p[0],p[1]+.15,p[2])),Vector((0,-1,0)),.3)[0]
            if hit is not None: floor[j,q]=hit.y+(clearance if 0<q<k-1 else -.003)
    bell=np.sin(np.pi*t[:,0,0])**2
    for q in range(1,k-1):
        needed=np.maximum(floor[:,q]-patch[:,q,1],0)
        height=np.max(needed[1:-1]/np.maximum(bell[1:-1],1e-8))
        patch[:,q,1]+=height*bell
    for q in [0,k-1]:
        valid=np.isfinite(floor[:,q])
        patch[valid,q,1]=np.minimum(patch[valid,q,1],floor[valid,q])
    for _ in range(smooth):
        y=patch[:,:,1].copy()
        # Relax the crown sideways and along its run; actual metal remains
        # a hard support constraint, while the outer two feet stay buried.
        relaxed=.5*y[1:-1,1:-1]+.125*(y[:-2,1:-1]+y[2:,1:-1]+y[1:-1,:-2]+y[1:-1,2:])
        patch[1:-1,1:-1,1]=np.maximum(
            y[1:-1,1:-1]+bell[1:-1,None]*(relaxed-y[1:-1,1:-1]),floor[1:-1,1:-1])
    rows=np.concatenate([A,patch[1:-1],B])
    V=rows.reshape(-1,3)
    idx=np.arange(len(V)).reshape(-1,k)
    F=[]
    for j in range(len(rows)-1):
        for q in range(k-1):
            F.extend([(idx[j,q],idx[j+1,q],idx[j+1,q+1]),(idx[j,q],idx[j+1,q+1],idx[j,q+1])])
    F=np.asarray(F,dtype=np.int64)
    n=np.cross(V[F[:,1]]-V[F[:,0]],V[F[:,2]]-V[F[:,0]])
    if n[:,1].sum()<0:F=F[:,[0,2,1]]
    foot=np.zeros(len(V),bool)
    foot[idx[:,0]]=foot[idx[:,-1]]=True
    foot[idx[0]]=foot[idx[-1]]=True
    m._caps[-2:]=[dict(V=V,F=F,foot=foot,role=np.where(foot,3,0),anchor=np.full(len(V),-1))]
    return V,F

def build(m,v):
    right=m.name.endswith('endr')
    p=3 if right else 1
    low=copy(m)
    P=m._part_verts(0).copy()
    free=P[:,2].max() if right else P[:,2].min()
    ring=np.unique(np.round(P[np.abs(P[:,2]-free)<.00001,:2],6),axis=0)
    low._pv_cache={0:np.concatenate([np.column_stack([ring,np.full(len(ring),z)]) for z in [P[:,2].min()+.00001,P[:,2].max()-.00001]])}
    out=[low.log(0,v)]
    P=m._part_verts(p)
    upper=copy(m)
    knee=-1.04134 if right else .96634
    free=P[:,2].max() if right else P[:,2].min()
    ring=np.unique(np.round(P[(np.abs(P[:,2]-free)<.00001)&(P[:,1]>.55),:2],6),axis=0)
    Q=np.concatenate([np.column_stack([ring,np.full(len(ring),z)]) for z in [knee,free+(-.00001 if right else .00001)]])
    upper._pv_cache={p:Q}
    a=upper.log(p,v,k=15)
    diagonal=copy(m)
    diagonal._pv_cache={p:P[(P[:,1]>.4)&((P[:,2]<0) if right else (P[:,2]>0))&((abs(P[:,1]-.59134)>.001)|(abs(P[:,0])>.019))]}
    b=diagonal.log(p,v,step=.05,k=15)
    out.append(_bridge(m,a,b,-1.04134 if right else .96634))
    return H.join(out)

