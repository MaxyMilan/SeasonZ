"""misc_woodencrate_3x: three wooden crates, one standing open in front (Expansion mapping).

(Astra Socrates, 7 Oct 2026, e1) the front crate's exposed rim stayed bare. Lowering the volumetric thin filter
restored it but also grew curtains on the leaning crate's battens. Keep the two broad lids in the volumetric route;
the open crate's actual upward-facing rim and corner blocks receive separate narrow blankets. Their depth is
limited by support width, without bridging openings or burying down the sides. The leaning lid still shelters the floor."""
import snow_hand as H


def build(m, v):
    m.ground = float(m.V[:, 1].min()) - 0.25
    m._sz_parts = (1, 25)
    m._sz_rails = ([], [])
    caps = [H.consts(m, v, A7_THIN=0.07, A7_OVL=0.3, A7_LIPDROP=0.03)]
    rim_parts = (0, 53, 54, 55, 56, 57, 58, 59, 60, 68)
    tops = m.tops(v, parts=rim_parts, ny_min=0.85) & (m.NYF >= 0.85)
    for R, Zc in m.regions(tops, v, close=0.0, min_area=0.00015):
        caps.append(m.blanket(R, Zc, v, smooth=0.012, over=0.003, fill=0.0,
                              bury=False, holes=0.0))
    return H.join(caps)
