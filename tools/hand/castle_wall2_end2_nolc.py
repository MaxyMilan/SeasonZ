"""castle_wall2_end2_nolc: a piece of the castle's curtain wall (rough stone faces, a crown with merlons or a walkway).

(Opus, 6 Oct, b1) castle_wall1_20_nolc: the blocks standing out of the stone face caught snow on their tops and
the vertical face was spotted with white patches at every depth, like camouflage. The family holds snow on its
crown only (within 50 cm of the highest top within a metre in plan), with a short lip."""
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
    keep = Z >= L - drop
    orig = m.tops
    m.tops = lambda *a, **kw: orig(*a, **kw) & keep
    m._sz_crown = True


def build(m, v):
    _crown(m)
    return H.consts(m, v, fn=lambda m_, v_: H.big_tops(m_, v_, 0.01), A7_OVL=0.3, A7_LIPDROP=0.05)
