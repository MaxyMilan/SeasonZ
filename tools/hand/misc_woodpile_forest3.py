"""misc_woodpile_forest3: a stacked pile of round logs, as misc_woodpile_forest2: every log the sky sees gets a log
crescent; nothing goes to the volumetric cap (r10: a long ribbed curtain down the top log, drips on the lower log ends)."""
import snow_hand as H


def build(m, v):
    if not hasattr(m, '_sz_rails'):
        n = int(m.part_t.max()) + 1
        logs = [p for p in range(n) if H.part_top_area(m, p) > 0.002 and H._sky_share(m, p, slant=True) >= 0.1]
        m._sz_rails = (logs, [])
        m._sz_exclude = tuple(logs)
    return H.hybrid(m, v)
