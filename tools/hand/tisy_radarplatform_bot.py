"""tisy_radarplatform_bot: the lower concrete access ramp of the Tisy radar platform, with steel railings.

(Astra Euclid, 7 Oct 2026, b1) the volumetric thin cap rose into repeated triangular peaks beside the railings.
Each exposed surface now gets its own supported blanket at the actual depth, with a short rounded edge and
no burial down the side. The rail/beam route retains narrow supported ridges; the low ramp foot meets ground snow.
"""
import snow_hand as H
import numpy as np


def build(m, v):
    # Keep the deck and kerb as separate blankets: merging their shallow step
    # made triangular wedges around the railing feet even in the first blanket trial.
    parts = (62, 63)
    eligible = [p for p in range(int(m.part_t.max()) + 1) if p not in parts]
    logs = [p for p in eligible if m.is_log(p)]
    beams = [p for p in eligible if p not in logs and m.is_beam(p)]
    out = [m.log(p, v) for p in logs] + [m.beam(p, v, step=0.25) for p in beams]
    out.append(m.cover(v, m.tops(v, exclude=list(parts) + logs + beams),
                       over=0.01, smooth=0.025, bury=False))
    for p in parts:
        tops = m.tops(v, parts=(p,), ny_min=0.8) & (m.NYF >= 0.8)
        for region, heights in m.regions(tops, v, close=0.0):
            out.append(m.blanket(region, heights, v, over=0.005, shoulder=0.25,
                                 smooth=0.025, bury=False, fill=0.005))
    cap = H.join(out)
    return cap
