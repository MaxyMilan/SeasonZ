"""mil_blastcover3: a broad earth berm around an open timber-lined emplacement.

(Astra Kepler, 7 Oct 2026, b1) the volumetric mesh split into radial sheets and sharp triangular fans, including
large holes in shallow snow. Follow the exposed sloping earth with continuous surface blankets and short lips;
the timber tops retain their supported caps. The open centre and steep interior walls remain clear.
"""
import snow_hand as H


def build(m, v):
    return H.auto(m, v, over=0.015, smooth=0.06, bury=False)
