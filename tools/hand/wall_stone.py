"""wall_stone: a winding dry-stone wall of large rough blocks, about 1 m high.

A dry-stone wall lies low and holds snow like the rocks and the ground around it, not like a fence top: the depths of
the props (5-23 cm, kind 0) instead of a fence's 1.5-6.5 cm. With the thin fence depths the snow's kernels (2-10 cm)
were smaller than the stones' facets and the cap copied every facet as a hard crease (m1, c29)."""
import snow_hand as H


def build(m, v):
    m.kind = 0
    return H.hybrid(m, v)

