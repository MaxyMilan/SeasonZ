"""lunapark_autodrome: an open bumper-car arena floor inside a raised wooden walkway and thin railings.

(Astra Faraday, 7 Oct 2026, b1) the old terrain threshold left the broad arena completely bare. The updated
Opus low-floor decision requires its own layer from v1 even though the floor is only 13.62-14.62 cm above the
model foot. Lower the accumulation threshold to that foot. Broad floor and walkway tops carry separate smooth
blankets across genuine height steps; slender railings and fittings let snow through. Short lips keep the
raised perimeter edges supported and the rail openings clear.
"""
import snow_hand as H


def build(m, v):
    m.ground = float(m.V[:, 1].min()) - 0.25
    if not hasattr(m, '_sz_faraday_panels'):
        m._sz_faraday_panels = tuple(p for p in range(int(m.part_t.max()) + 1)
                                    if H.part_top_area(m, p, ny_min=0.8) >= 0.1)
        H.through(m, [p for p in range(int(m.part_t.max()) + 1) if p not in m._sz_faraday_panels])
    tops = m.tops(v, parts=m._sz_faraday_panels, ny_min=0.8) & (m.NYF >= 0.8)
    return H.join([m.blanket(region, heights, v, over=0.008, shoulder=0.25,
                            smooth=0.03, fill=0.01, bury=False)
                   for region, heights in m.regions(tops, v, close=0.0, min_area=0.01)])
