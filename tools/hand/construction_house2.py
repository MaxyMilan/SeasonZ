"""construction_house2: exposed concrete slabs, broken wall tops and loose timber at an unfinished house.

(Astra Laplace, 7 Oct 2026, b1) fine volumetric snow retained angular wedges between loose boards and
slabs even with a v3 minimum. Separate actual source parts and densely sample each supported blanket;
dense sampling and zero smoothing keep snow above the warped source slabs; zero gap fill prevents a bridge from timber down to the slab.
Thin railing pieces stay clear; broad nearly level slab, beam and timber tops retain depth growth.
"""
import snow_hand as H


def build(m, v):
    rails = tuple(p for p in range(147, 209) if p not in (169, 170))
    out = []
    for p in range(int(m.part_t.max()) + 1):
        if p in rails or H.part_top_area(m, p, 0.8) < 0.08:
            continue
        tops = m.tops(v, parts=(p,), ny_min=0.8, slope=False) & (m.NYF >= 0.8)
        for region, heights in m.regions(tops, v, close=0.0, min_area=0.008):
            out.append(m.blanket(region, heights, v, rim='round', over=0.003,
                                 smooth=0.0, spacing=0.075, shoulder=0.25, fill=0.0, holes=0.0, bury=False))
    return H.join(out)
