"""prison_side: a prison wing with a long pitched roof, cross-gables and chimney stacks.

(Astra Euler, 7 Oct 2026, b1) the volumetric cap split into huge triangular holes and lifted sheets over
the gables at every depth. Continuous surface blankets follow the connected exposed roof slopes and
chimney tops from v1. A normal filter excludes steep wall faces; short rounded lips do not bury into walls.
The first blanket left narrow jagged valley splits. (Astra Huygens, 7 Oct 2026, b1) measured roof steps
reach 0.9-1.0 m at the projecting wings. A globally connected mask smoothed across those internal cliffs
and cut below their upper surfaces. Separate the three shallow raised roof slopes from the main pitched
roof before blanketing, so each real height step has its own short supported edge.
"""
import numpy as np
import snow_hand as H


def build(m, v):
    # Narrow facade rods generated a detached 4 cm-wide strip at v6-v7, 22 cm from the source.
    H.through(m, (137, 143))
    tops = m.tops(v, ny_min=0.55, slope=False) & (m.NYF >= 0.55)
    if not hasattr(m, '_sz_huygens_roofzones'):
        normals = m.n_t.copy()
        normals *= np.where(normals[:, 1] < 0, -1, 1)[:, None]
        zones = []
        for target in ((0.0, 0.9338, 0.3578), (0.0, 0.9201, 0.3916), (0.0, 0.8966, -0.4428)):
            face = (m.part_t == 34) & (normals @ np.asarray(target) > 0.99985)
            zones.append(m.valid & face[np.maximum(m.TID, 0)])
        zones.append(~np.logical_or.reduce(zones))
        m._sz_huygens_roofzones = zones
    out = []
    for zone in m._sz_huygens_roofzones:
        for region, heights in m.regions(tops & zone, v, close=0.04, tau=0.1):
            out.append(m.blanket(region, heights, v, over=0.025, smooth=0.035,
                                 spacing=0.25, fill=0.02, holes=0.01, bury=False))
    return H.join(out)
