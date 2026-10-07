"""mil_camonet_big_east: a large camouflage net stretched over poles with steep hanging sides.

(Astra Kepler, 7 Oct 2026, b1) the volumetric snow tore into radial fans on the roof and coated the hanging net
as broad curtains. Keep the largest connected shallow roof region of the net (part 39, normals within about
37 degrees), above y=1.4 m; the measured central canopy starts at y=1.55 m. The first trial included a low
connected outward fold down to y=0.28 m. This upper-canopy limit removes that hanging snow tab while retaining
the complete central roof. Isolated upward-facing folds on the hanging sides receive no cap. Each depth keeps its actual
thickness in a supported blanket, with no gap closing or downward burial across the steep net folds.
"""
import numpy as np
import snow_hand as H


def build(m, v):
    if not hasattr(m, '_sz_kepler_roof'):
        base = m.tops(4, parts=(39,), ny_min=0.8) & (m.NYF >= 0.8) & (m.Z >= 1.4)
        lab, n = H.label(base, base[:, :-1] & base[:, 1:], base[:-1, :] & base[1:, :])
        keep = base.copy()
        if n:
            keep &= lab == int(np.argmax(np.bincount(lab[base], minlength=n)))
        m._sz_kepler_roof = keep
    tops = m.tops(v, parts=(39,), ny_min=0.8) & m._sz_kepler_roof
    return H.join([m.blanket(region, heights, v, over=0.01, shoulder=0.25,
                             smooth=0.06, fill=0.01, bury=False)
                   for region, heights in m.regions(tops, v, close=0.0)])
