"""castle_wall1_20_turn_nolc: a rough castle curtain wall with a crown, raised blocks and an inset walkway.

(Astra Euclid, 7 Oct 2026, b1) the crown-only filter removed broad exposed shelves below the parapet, while
volumetric snow joined broken block tops into pointed drips. Keep the crown and independently wide, nearly level
surfaces (at least 0.4 m2 and 18 cm wide). Each eligible surface gets its own short supported blanket; small stone
ledges on the vertical face remain filtered. Actual depth growth is preserved from v1 to v7.
(Astra Kepler, 7 Oct 2026, b1) the low shelf bridged a narrow gap occupied by tall masonry; the blanket
support-floor correction lifted those artificial cells several metres. Do not close gaps between shelf cells.
"""
import numpy as np
import snow_hand as H


def _crown(m, drop=0.5, reach=1.0):
    """only the crown holds snow: cells within drop m of the highest top within reach m in plan. The rough stone face
    of the wall (blocks standing out a few cm, their tops facing up) lies in plan beside the crown and lower"""
    if getattr(m, '_sz_crown', False):
        return
    Z = np.where(np.isfinite(m.Z), m.Z, -np.inf)
    r = max(1, int(round(reach / m.g)))
    L = Z
    for dj, di in ((1, 0), (0, 1)):
        out = L.copy()
        for k in range(1, r + 1):
            out = np.maximum(out, H.sh(L, k * dj, k * di, -np.inf))
            out = np.maximum(out, H.sh(L, -k * dj, -k * di, -np.inf))
        L = out
    base = m.tops(4, ny_min=0.8) & (m.NYF >= 0.8)
    dx = np.abs(m.Z[:, 1:] - m.Z[:, :-1])
    dz = np.abs(m.Z[1:, :] - m.Z[:-1, :])
    lab, n = H.label(base, base[:, 1:] & base[:, :-1] & (dx < 0.08),
                     base[1:, :] & base[:-1, :] & (dz < 0.08))
    counts = np.bincount(lab[base], minlength=n)
    wide = H.erode(base, max(1, int(round(0.09 / m.g))))
    ids = [k for k in np.unique(lab[wide]) if k >= 0 and counts[k] * m.g * m.g >= 0.4]
    major = np.isin(lab, ids) & base
    keep = (Z >= L - drop) | major
    orig = m.tops
    m.tops = lambda *a, **kw: orig(*a, **kw) & keep
    m._sz_crown = True


def build(m, v):
    _crown(m)
    tops = m.tops(v, ny_min=0.7) & (m.NYF >= 0.65)
    out = []
    for region, heights in m.regions(tops, v, close=0.0):
        # The low walkway lies beside tall masonry. The neighbouring height
        # field must remain a wall boundary, not a target several metres above
        # this region for its snow edge. Source geometry/BVH stay unchanged.
        source = m.Z
        ceiling = float(np.nanmax(heights)) + max(0.04, 1.2 * m.thick(v))
        m.Z = np.where(region, source, np.minimum(source, ceiling))
        try:
            out.append(m.blanket(region, heights, v, over=0.015, shoulder=0.25,
                                 fill=0.01, smooth=0.04, bury=False))
        finally:
            m.Z = source
    return H.join(out)
