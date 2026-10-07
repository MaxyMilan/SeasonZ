"""slum_roof6: a tarp stretched over four poles as a roof, its front hanging down steeply (Expansion mapping).

(Astra Socrates, 7 Oct 2026, e1) the blanket still followed the hanging front around its hole, making torn flaps.
Keep only the largest four-connected region of nearly level roof cells; the detached steep valance and its hole
hold no snow. The mask persists across depths, while each depth retains its own blanket thickness."""
import numpy as np
import snow_hand as H


def build(m, v):
    if not getattr(m, '_sz_roof_region', False):
        base = m.tops(4, ny_min=0.8)
        lab, n = H.label(base, base[:, :-1] & base[:, 1:], base[:-1, :] & base[1:, :])
        if n:
            keep = lab == int(np.argmax(np.bincount(lab[base], minlength=n)))
            orig = m.tops
            m.tops = lambda *a, **kw: orig(*a, **kw) & keep
        m._sz_roof_region = True
    return H.auto(m, v)
