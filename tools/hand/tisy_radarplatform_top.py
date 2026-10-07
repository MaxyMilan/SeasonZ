"""tisy_radarplatform_top: the broad level Tisy radar deck, a perimeter kerb and a small service hut.

(Astra Euclid, 7 Oct 2026, b1) the thin volumetric cap had sharp triangular peaks and creases beside the hut
and deck perimeter. Surface-following blankets keep the flat deck even at v1, with separate kerb and roof levels,
short rounded lips and no downward burial. All seven depths retain their own thickness.
"""
import snow_hand as H
import numpy as np


def build(m, v):
    # Keep the deck and kerb as separate blankets: merging their shallow step
    # made triangular wedges around the railing feet even in the first blanket trial.
    parts = (0, 1, 18, 33)
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
