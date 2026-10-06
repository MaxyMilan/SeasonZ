"""wall_railing_1: two hexagonal 40 mm round steel pipes (0 upper, 1 lower).

Each pipe receives an m.log crescent. Posts 2 (full) and 3 (intermediate)
end inside the upper pipe; there is no exposed flat post top to blanket.
Vertical faces and undersides stay bare; no crumbs or flat-topped beams.
The supplied slope meshes have the same local geometry as the straight one.

At the coplanar end rings an exact-boundary BVH ray misses some profile
lines. The new whole-station rule then cuts off a full 6.86 cm station and
can lose the small lower-rail stub. Fit to rings 0.01 mm inside those two
planes, retaining the actual source collision mesh and all shelter checks.
This puts the rounded cap foot at the true end within 0.01 mm, without
extending snow over unsupported/broken wood. The default wall_railing_1
passes hc but needs this recipe to correct its visible short end caps.
"""
from copy import copy
import numpy as np
import snow_hand as H


def build(m, v):
    out = []
    for p in (0, 1):
        pipe = copy(m)
        P = m._part_verts(p).copy()
        P[:, 2] = np.clip(P[:, 2], P[:, 2].min() + 0.00001,
                         P[:, 2].max() - 0.00001)
        pipe._pv_cache = {p: P}
        out.append(pipe.log(p, v))
    return H.join(out)
