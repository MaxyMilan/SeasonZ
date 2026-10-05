"""platform1_stairs_30: a stone stair on a stepped core (part 0); each tread laid with two or three stone slabs (1-57),
17 cm risers.

Each tread one blanket over its slabs (the joints bridged), a rounded nose over the riser and tucked into the riser
behind; the core's own tops (the side curbs) their own strip. Risers stay steps in every depth."""
import snow_hand as H


def build(m, v):
    out = []
    for R, Zc in m.regions(m.tops(v, steep=0.6), v):
        out.append(m.blanket(R, Zc, v))
    return H.join(out)

