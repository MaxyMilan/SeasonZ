"""city_stand_news2: kiosk with recessed flat roof/awning in part 62.

mass/c39: white crescents project through the fascia below the upper roof rim;
thin fittings also grow knobs. ast1 part-colour inspection shows roof y=1.1493
inside fascia rising to about 1.486, and perimeter rails 12-15/18-19/37-38.
Only the broad roof/awning carries snow. Clip its smooth cap at the INNER
fascia planes, where the cut is hidden in the timber. Since even v7 (23 cm)
is below the fascia top, snow must not spill through it. Small rails stay bare.
Attempt 1's rectangular cut missed the inward-leaning left fascia (up to 3.9 cm
at its top). Attempt 2 also selected the opposite outer wall and clipped away
the cap. Attempt 3 restricted planes correctly but ran out of system memory
inside the shared volumetric builder. Attempt 4 builds this flat roof directly:
a deterministic smooth pillow, a fine regular grid, softly rounded short sides,
and the corrected inward planes. It needs no volumetric field or decimation.
Seven increasing local depths, without modifying the common building table.
"""
import numpy as np
import snow_hand as H


def _inside_fascia(m,V,F):
    # Roof faces span x [-1.9913,1.9687], z [-3.5719,-.9169]. Cut just
    # inside the adjacent wall thickness, so there is no visible moat.
    if not hasattr(m,'_ast1_planes'):
        planes=[(np.array(n),d) for n,d in (((1,0,0),-1.994),((-1,0,0),-1.971),
                                           ((0,0,1),-3.5734),((0,0,-1),.9184))]
        tri=m.V[m.T]
        side=(m.part_t==62)&(m.n_t[:,0]>.9)&(tri[:,:,0].max(1)<-1.9)&(tri[:,:,1].min(1)>1.14)&(tri[:,:,1].max(1)>1.48)
        for t,n in zip(tri[side],m.n_t[side]):
            planes.append((n,float(np.dot(n,t[0]))-.0015))
        assert all(np.dot(n,(0,1.3,-2.2))>d for n,d in planes), 'fascia planes exclude roof centre'
        m._ast1_planes=planes
    planes=m._ast1_planes
    vertices=[]; faces=[]
    for face in F:
        poly=[p.copy() for p in V[face]]
        for normal,value in planes:
            if not poly: break
            clipped=[]
            for a,b in zip(poly,poly[1:]+poly[:1]):
                da=np.dot(normal,a)-value; db=np.dot(normal,b)-value
                if da>=0: clipped.append(a)
                if (da>=0)!=(db>=0): clipped.append(a+(b-a)*(da/(da-db)))
            poly=clipped
        if len(poly)<3: continue
        k=len(vertices); vertices.extend(poly)
        faces.extend((k,k+i,k+i+1) for i in range(1,len(poly)-1))
    if not faces: raise ValueError('fascia clipping removed the roof')
    V=np.array(vertices); F=np.array(faces,np.int64)
    _,first,inv=np.unique(np.round(V,8),axis=0,return_index=True,return_inverse=True)
    V=V[first]; F=inv[F]
    area=np.linalg.norm(np.cross(V[F[:,1]]-V[F[:,0]],V[F[:,2]]-V[F[:,0]]),axis=1)
    return V,F[area>1e-12]


def build(m,v):
    dep=(.05,.07,.09,.11,.15,.19,.23)[v-1]
    x=np.linspace(-1.994,1.971,61)
    z=np.linspace(-3.5734,-.9184,43)
    xx,zz=np.meshgrid(x,z)
    d=np.minimum.reduce((xx-x[0],x[-1]-xx,zz-z[0],z[-1]-zz))
    rim=np.sqrt(np.maximum(0,1-np.clip(1-d/.12,0,1)**2))
    # Shared smooth bumps across depths: no changed noise bank and no facets.
    noise=(.013*np.sin(7.1*xx+.5)*np.cos(5.3*zz)+
           .009*np.cos(11.3*xx-2.9*zz)+.008*np.sin(3.7*xx+8.1*zz))
    yy=1.1493+dep*(.74+.26*rim+noise)
    V=np.column_stack((xx.ravel(),yy.ravel(),zz.ravel()))
    F=[]; nx=len(x)
    for j in range(len(z)-1):
        for i in range(nx-1):
            a=j*nx+i;b=a+1;c=a+nx+1;d_=a+nx
            F.extend(((a,d_,c),(a,c,b)))
    loop=np.r_[np.arange(nx),np.arange(2*nx-1,len(V),nx),
               np.arange(len(V)-2,len(V)-nx-1,-1),np.arange(len(V)-2*nx,0,-nx)]
    skirt=V[loop].copy();skirt[:,1]=1.1453
    n=len(V)
    for k in range(len(loop)):
        k1=(k+1)%len(loop)
        F.extend(((int(loop[k]),n+k1,n+k),(int(loop[k]),int(loop[k1]),n+k1)))
    return _inside_fascia(m,np.vstack((V,skirt)),np.array(F,np.int64))
