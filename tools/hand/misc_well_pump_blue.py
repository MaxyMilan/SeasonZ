"""misc_well_pump_blue: a hand pump (column 2, spout, handle) on a concrete well ring (1, 9) on a round base slab (0).

(Opus, 6 Oct, r10, c37) the base slab (at ground level) stayed bare at every depth while all around is white, and
the 13 cm pump column grew a ball. The slab holds snow (the ground limit moved down), tops narrower than 15 cm
(column, spout, handle) a ridge or nothing, with a short lip."""
import snow_hand as H


def build(m, v):
    if not getattr(m, '_sz_low', False):
        m.ground -= 0.22
        m._sz_low = True
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05, A7_THIN=0.15)
