"""misc_woodpile_forest2: a stacked pile of round logs. Every part of a woodpile is a log: each one the sky sees gets a
log crescent (the shelter test keeps the buried ones bare). (Opus, 6 Oct) hybrid missed the knobbly upper logs and gave
them the volumetric cap, which hung down their fronts as serrated curtains at v7 (r10)."""
import snow_hand as H


def build(m, v):
    if not hasattr(m, '_sz_rails'):
        n = int(m.part_t.max()) + 1
        logs = [p for p in range(n) if H.part_top_area(m, p) > 0.002 and H._sky_share(m, p, slant=True) >= 0.1]
        m._sz_rails = (logs, [])
        m._sz_exclude = tuple(logs)
    return H.hybrid(m, v)
