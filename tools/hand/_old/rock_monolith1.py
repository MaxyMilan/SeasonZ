"""rock_monolith1: a large connected monolith. Drape only visible upward
facets, retaining steep changes of level as separate snow boundaries.
No shell is drawn on the vertical faces or the buried lower rock."""
import snow_rock as R


def build(m,v):
    return R.drape(m,v,budget=11000)
