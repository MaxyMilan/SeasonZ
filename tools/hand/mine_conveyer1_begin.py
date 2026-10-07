"""mine_conveyer1_begin: a low mine conveyor with a raised feed end and a small drive housing.

(Astra Kepler, 7 Oct 2026, b1) the deep volume grew long fingers down the vertical end cheeks, hanging into the
roller opening. Only the measured broad belt, housing, cheek tops and substantial frame top panels hold snow.
Each shallow exposed surface gets a short separate blanket without gap closing or downward burial; the roller
opening and thin fittings stay clear. The belt bed is only about 24 cm above the supplied terrain, just below
the 25 cm cap cutoff; lower the accumulation threshold once so its exposed bed receives thin snow as well.
"""
import snow_hand as H

PANELS = (1, 5, 18, 22, 26, 27, 31, 32, 33, 35)


def build(m, v):
    if not getattr(m, '_sz_kepler_low_belt', False):
        m.ground -= 0.25
        m._sz_kepler_low_belt = True
    H.through(m, [p for p in range(int(m.part_t.max()) + 1) if p not in PANELS])
    out = []
    for p in PANELS:
        tops = m.tops(v, parts=(p,), ny_min=0.8) & (m.NYF >= 0.8)
        for region, heights in m.regions(tops, v, close=0.0, min_area=0.01):
            out.append(m.blanket(region, heights, v, over=0.005, shoulder=0.25,
                                 smooth=0.03, fill=0.005, bury=False))
    return H.join(out)
