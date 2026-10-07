"""mil_barracks5_basement: stepped flat barracks roofs on a large concrete slab.

(Astra Noether, 7 Oct 2026, b1) source comparison proves the old raised roof fans
and triangular pits were snow artifacts. The prepared 3 cm volume proved too slow
for a complete seven-depth rebuild in the session. Exposed roof surfaces now get
supported blankets, separated at real height discontinuities, with dense sampling
and no smoothing that could cut through shallow roof detail. Thin wires and rods
let snow through. Low open slab surfaces retain their own snow from v1.
"""
import numpy as np
import snow_hand as H

WIRES = tuple(p for p in range(31, 70)
              if p not in (35, 41, 44, 46, 47, 48, 62, 63, 66))


def build(m, v):
    m.ground = float(m.V[:, 1].min()) - 0.25
    H.through(m, WIRES)
    tops = m.tops(v, ny_min=0.8, slope=False) & (m.NYF >= 0.8)
    out = []
    for region, heights in m.regions(tops, v, close=0.0, tau=0.025, min_area=0.008):
        # The large planar foundation needs far fewer interior points than roof detail.
        spacing = 0.4 if np.isin(m.PART[region], (131, 152, 153)).all() else 0.1
        cap = m.blanket(region, heights, v, over=0.005, smooth=0.0,
                             spacing=spacing, shoulder=0.25, fill=0.0, holes=0.0,
                             bury=False)
        if cap is not None and spacing == 0.4:
            # The measured foundation is planar (height variation < 3 microns).
            # Keep every triangle above that plane, including the thin interior.
            verts = np.asarray(cap[0], float).copy()
            verts[:, 1] = np.maximum(verts[:, 1], float(np.nanmax(heights)) + 0.002)
            cap = verts, cap[1]
        out.append(cap)
    return H.join(out)
