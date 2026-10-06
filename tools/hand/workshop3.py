"""workshop3: long shallow pitched roof (part 0), gutters 31/32, vent 167/168.

mass/c39: a separate gutter bead lies below the main cap, leaving a dark slit
along each eave. ast1 joins the snow carrier across the narrow gutter trough:
extend the adjacent roof plane to the gutter edge, with the same face normal.
Attempt 1 changed only the raster, but particle rays still hit the real gutter
and recreated the slit. Attempt 2 uses a private support model with a narrow
roof continuation over each gutter, so particle rays and support floor agree.
The original model stays intact. Disable the height-band cut on this continuous
eave and retain a short lip. All seven local depths increase (5-23 cm).
"""
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import snow_hand as H


def build(m,v):
    if not hasattr(m,'_ast1_support'):
        p=H.Model(m.name,path=m.path,g=m.g)
        tri=m.V[m.T]
        ids=np.flatnonzero((m.part_t==0)&(m.n_t[:,1]>.9)&(tri[:,:,1].min(1)>1.68))
        roof=BVHTree.FromPolygons(m.V.tolist(),m.T[ids].tolist(),all_triangles=True)
        extra=[]; faces=[]
        for inner,outer in ((-2.78,-3.016),(2.27,2.69)):
            zz=np.r_[np.linspace(-6.54,6.60,95),-6.0,-4.,-2.,0.,2.,4.,6.]
            zz=np.unique(zz)
            start=len(extra)
            for z in zz:
                hit,n,_,_=roof.ray_cast(Vector((inner,5.,float(np.clip(z,-6.49,6.46)))),Vector((0,-1,0)))
                if hit is None: raise ValueError('roof continuation ray missed')
                for x in (inner,outer):
                    y=hit.y-n.x/n.y*(x-inner)-n.z/n.y*(z-hit.z)+.001
                    extra.append((x,y,z))
            for j in range(len(zz)-1):
                a=start+2*j; b=a+1; c=a+3; d=a+2
                pair=((a,d,c),(a,c,b)) if outer>inner else ((a,c,d),(a,b,c))
                faces.extend(pair)
        offset=len(p.V)
        p.V=np.vstack((p.V,extra)); p.T=np.vstack((p.T,np.array(faces)+offset))
        p.glass_t=np.r_[p.glass_t,np.zeros(len(faces),bool)]
        p._faces(); p._raster(); p._bvh(); p.reset()
        original=p.tops
        p.tops=lambda *a,**kw: original(*a,**kw)&(p.Z>1.67)
        p.thick=lambda vv:(.05,.07,.09,.11,.15,.19,.23)[vv-1]
        p._sz_rails=([],[])
        m._ast1_support=p
    p=m._ast1_support
    p.reset()
    return H.consts(p,v,A7_BANDH=0.,A7_OVL=.3,A7_LIPDROP=.05,A7_THIN=.07)
