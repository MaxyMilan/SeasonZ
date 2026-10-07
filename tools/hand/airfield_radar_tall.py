"""airfield_radar_tall: a tall steel lattice tower with horizontal frame levels and concrete feet.

(Astra Euler, 7 Oct 2026, b1) the volumetric cap made huge junction lobes and vertical slivers on braces.
Only shallow horizontal members at least 12 cm wide and the concrete foot tops receive supported blankets.
Sparse small ladder/fitting assemblies, upright and diagonal braces let snow through. Short rounded edges
and width-limited blankets keep the open lattice clear through all depths. The first local blanket
left periodic teeth on narrow members. Separating connected horizontal members into individual blankets
generated upright boundary strips; that trial was rejected. Connected tops use finer blanket spacing.
"""
import numpy as np
import snow_hand as H


def build(m, v):
    if not hasattr(m, '_sz_euler_members'):
        keep = []
        for p in range(int(m.part_t.max()) + 1):
            pts = m.V[np.unique(m.T[m.part_t == p])]
            ex = np.ptp(pts, axis=0)
            top = H.part_top_area(m, p, 0.9)
            horizontal = (ex[1] <= 0.26 and min(ex[0], ex[2]) >= 0.12 and top >= 0.1
                          and (top >= 0.8 or top / max(ex[0]*ex[2], 0.001) >= 0.3))
            if horizontal or p in range(1, 11):
                keep.append(p)
        m._sz_euler_members = tuple(keep)
        H.through(m, [p for p in range(int(m.part_t.max()) + 1) if p not in keep])
    tops = m.tops(v, parts=m._sz_euler_members, ny_min=0.9) & (m.NYF >= 0.9)
    return m.cover(v, tops, over=0.003, smooth=0.025, spacing=0.07,
                   shoulder=0.25, bury=False)
