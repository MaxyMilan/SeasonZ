"""houseblock_1f4: asymmetric broken roof, all roof planes in connected part 5.

mass/c39: torn sheets and metre-wide triangle fins from v1, severe holes v3-v7.
ast1: a fixed, locally sampled roof grid follows the actual upper roof triangles
of part 5, including its shallow dents and asymmetric pitch changes. The four
outer edges have a short rounded lip. A rectangular opening meets chimney 99;
small sky-visible detail caps retain addonfine. No changes to shared builders.
"""
import math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import snow_hand as H


def _axis(lo, hi, extra):
    return np.unique(np.r_[np.linspace(lo, hi, int(math.ceil((hi-lo)/.18))+1), extra])


def _roof(m, v):
    if not hasattr(m, '_ast1_roof'):
        tri=m.V[m.T]
        sel=(m.part_t==5)&(m.n_t[:,1]>.5)&(tri[:,:,1].min(1)>2.65)
        roof=BVHTree.FromPolygons(m.V.tolist(),m.T[sel].tolist(),all_triangles=True)
        x0,x1=-5.0055,4.9933
        z0,z1=-4.9599,5.0387
        # Place nodes on the chimney footprint, so the opening has no stair steps.
        hx0,hx1=-1.281,.691
        hz0,hz1=-.684,-.282
        x=_axis(x0,x1,[hx0,hx1,x0+.035,x0+.10,x1-.10,x1-.035])
        z=_axis(z0,z1,[hz0,hz1,-2.4275,.0395,1.2895,3.1544,
                       z0+.035,z0+.10,z1-.10,z1-.035])
        xx,zz=np.meshgrid(x,z)
        pts=np.column_stack((xx.ravel(),np.zeros(xx.size),zz.ravel()))
        for i,p in enumerate(pts):
            hit=roof.ray_cast(Vector((float(p[0]),10.,float(p[2]))),Vector((0,-1,0)))[0]
            if hit is None:
                # The only uncovered columns are inside the chimney opening.
                hit=roof.find_nearest(Vector((float(p[0]),5.8,float(p[2]))))[0]
            pts[i,1]=hit.y
        faces=[]
        nx=len(x)
        for j in range(len(z)-1):
            for i in range(nx-1):
                if hx0 < (x[i]+x[i+1])/2 < hx1 and hz0 < (z[j]+z[j+1])/2 < hz1:
                    continue
                a=j*nx+i; b=a+1; c=a+nx+1; d=a+nx
                faces.extend(((a,d,c),(a,c,b)))
        # Clockwise in x/z, outward walls from this loop.
        loop=np.r_[np.arange(nx),np.arange(2*nx-1,len(pts),nx),
                   np.arange(len(pts)-2,len(pts)-nx-1,-1),
                   np.arange(len(pts)-2*nx,0,-nx)].astype(int)
        dist=np.minimum.reduce((pts[:,0]-x0,x1-pts[:,0],pts[:,2]-z0,z1-pts[:,2]))
        m._ast1_roof=(pts,np.asarray(faces,np.int64),loop,dist,(x0,x1,z0,z1))
    source,F,loop,dist,bounds=m._ast1_roof
    # v1/v2 are equal in the shared building depth table. Give this recipe seven
    # increasing depths within the same 5-23 cm envelope.
    dep=(.05,.07,.09,.11,.15,.19,.23)[v-1]
    V=source.copy()
    rim=np.sqrt(np.maximum(0,1-np.clip(1-dist/(.9*dep+.025),0,1)**2))
    noise=1+.025*np.sin(V[:,0]*2.1+.4)*np.sin(V[:,2]*1.7)
    V[:,1]+=dep*(.45+.55*rim)*noise
    x0,x1,z0,z1=bounds
    normal=np.zeros((len(loop),3))
    normal[:,0]=np.isclose(source[loop,0],x1).astype(float)-np.isclose(source[loop,0],x0)
    normal[:,2]=np.isclose(source[loop,2],z1).astype(float)-np.isclose(source[loop,2],z0)
    rings=[]
    for spread,height in ((.75,.33),(1.,.14),(.88,-.004/dep),(.10,-.006/dep)):
        r=source[loop].copy()+normal*(.012+.20*dep)*spread
        r[:,1]+=height*dep
        rings.append(r)
    verts=[V]+rings; faces=F.tolist(); prev=loop
    count=len(V)
    for ring in rings:
        cur=np.arange(count,count+len(loop)); count+=len(loop)
        for k in range(len(loop)):
            n=(k+1)%len(loop)
            faces.extend(((int(prev[k]),int(cur[n]),int(cur[k])),(int(prev[k]),int(prev[n]),int(cur[n]))))
        prev=cur
    return np.vstack(verts),np.asarray(faces,np.int64)


def build(m,v):
    m._sz_parts=(99,100,107,111)
    m._sz_rails=([],[])
    details=H.consts(m,v,A7_OVL=.25,A7_LIPDROP=.05,A7_THIN=.07)
    return H.join([_roof(m,v),details])
