"""stone1: one medium boulder with an uneven crown. Use a source-surface shell
to retain its ledges; depth-dependent slope holding broadens its snow coverage.
The underside and faces below the estimated ground do not support snow."""
import snow_rock as R


def build(m,v):
    return R.drape(m,v,budget=3900)
