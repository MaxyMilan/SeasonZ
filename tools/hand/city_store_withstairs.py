"""city_store_withstairs: a flat-roof shop with broad entrance landings and two exposed stair flights.

(Astra Huygens, 7 Oct 2026, b1) the lower open treads stayed bare under the terrain cutoff, including
steps that should be visibly snowy. Apply the Opus low-floor rule using the actual model foot, then
give each exposed top a supported blanket. Distinct tread heights remain separate with short noses;
the main roof, parapet and canopies retain cover from the first depth onward.
"""
import snow_hand as H


def build(m, v):
    m.ground = float(m.V[:, 1].min()) - 0.25
    tops = m.tops(v, ny_min=0.7, slope=False) & (m.NYF >= 0.7)
    out = []
    for region, heights in m.regions(tops, v, close=0.0, tau=0.06):
        out.append(m.blanket(region, heights, v, over=0.008, smooth=0.04,
                             fill=0.01, shoulder=0.3, bury=False))
    return H.join(out)
