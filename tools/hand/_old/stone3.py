"""stone3: one tall irregular boulder. Its crown and upward ledges share the
source-surface drape; steep sides remain bare and free edges are embedded.
An extra strip of steep support provides room for the thin edge to enter the
stone below the crown; the holding field itself keeps the 49..63 degree range.
The original connected shelves already have interior vertices."""
import snow_rock as R


def build(m,v):
    return R.drape(m,v,budget=3900,support_extra=.14,seed_shelves=False)
