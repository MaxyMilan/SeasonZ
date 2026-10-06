"""stone2: one larger, detailed boulder. Keep subdivision below 4000 triangles
and preserve the original crown/ledge topology while rounding the snow surface.
Embedded edges taper into the flanks without a projecting blanket rim."""
import snow_rock as R


def build(m,v):
    return R.drape(m,v,budget=3950)
