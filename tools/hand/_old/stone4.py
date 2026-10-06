"""stone4: a broad irregular boulder with shallow ridges across its crown.
One drape softens those ridges with depth; slope and ground tapers retain the
bare steep flanks without a projecting rim or an underside."""
import snow_rock as R


def build(m,v):
    return R.drape(m,v,budget=3600)
