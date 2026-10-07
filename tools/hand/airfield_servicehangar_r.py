"""airfield_servicehangar_r: a large airfield hangar with lower annex roofs and a raised roof box.

(Astra Euler, 7 Oct 2026, b1) the thin volumetric snow crumpled into repeated triangular peaks across
flat annex panels. Continuous blankets follow exposed roof regions from v1 without the volume field.
Short rounded lips keep walls clear; normal filtering prevents coverage down steep fascias.
"""
import snow_hand as H


def build(m, v):
    tops = m.tops(v, ny_min=0.7, slope=False) & (m.NYF >= 0.7)
    return m.cover(v, tops, over=0.008, smooth=0.05, bury=False)
