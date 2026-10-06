"""power_transformer_small: a pole transformer: two 9 m poles (40, 41), the transformer box (0, 2, 9) and thin
crossbars (42, 44, 49, 50) with insulators.

(Opus, 6 Oct) the volumetric cap turned the thin crossbars into sausages and set bulbous domes on the pole tops by v4
(m1). The crossbars get beam ridges (as fence rails); the box and the pole tops the cap, its lip overhanging at most 30%
of the depth (+1 cm); insulators and brackets (under 200 cm2 of top) hold none."""
import snow_hand as H

BARS = (42, 44, 49, 50)


def build(m, v):
    if not hasattr(m, '_sz_rails'):
        n = int(m.part_t.max()) + 1
        m._sz_rails = ([], list(BARS))
        m._sz_exclude = BARS
        m._sz_parts = tuple(p for p in range(n) if p not in BARS and H.part_top_area(m, p) >= 0.02)
    return H.consts(m, v, A7_OVL=0.3)
