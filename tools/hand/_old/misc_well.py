"""misc_well: a rough stone ring (part 9) closed by a cover of planks (0, 1, 4-8) with two cross boards (2, 3).

Cover: one blanket over the planks and the cross boards in every depth (the boards stand 5 cm: split off at the
shallow depths a slot opened along one of them); the notches between the staggered plank ends filled and the outline
softened (deep snow hung off the ends as lobes with V notches between them). Ring: snow on its level top only,
thinning out over the rough stones (with a rounded edge every stone hung a fringe of flaps down the side, and its 50
degree outer faces carried a sheet down to the ground)."""
import snow_hand as H

COVER = [0, 1, 2, 3, 4, 5, 6, 7, 8]
RING = [9]


def build(m, v):
    out = []
    for R, Zc in m.regions(m.tops(v, parts=COVER, steep=0.6), v, close=0.15, tau=0.08):
        out.append(m.blanket(R, Zc, v, soften=max(5, int(0.5 * m.thick(v) / m.g))))
    for R, Zc in m.regions(m.tops(v, parts=RING, ny_min=0.85), v, close=0.03):
        out.append(m.blanket(R, Zc, v, rim='taper', opening=0.03, soften=2))
    return H.join(out)

