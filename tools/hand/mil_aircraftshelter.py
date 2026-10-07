"""mil_aircraftshelter: a broad earth-covered aircraft shelter with retaining walls.

(Astra Gauss, 7 Oct 2026, b1) the coarse volumetric snow had broad bare sectors,
radial fans and projecting sheets across the mound at every depth. As on the
approved blast-cover berms, continuous supported blankets follow the exposed
earth and wall tops with short lips and no burial into the steep retaining faces.
"""
import snow_hand as H


def build(m, v):
    return H.auto(m, v, over=0.015, smooth=0.06, bury=False)
