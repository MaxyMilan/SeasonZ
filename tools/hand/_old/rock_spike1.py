"""rock_spike1: a tall single rock mass. Only the exposed crown and upward
ledges hold snow; the steep spike flanks are excluded before subdivision.
The sparse shelves and their embedded ends need close-up approval."""
import snow_rock as R


def build(m,v):
    return R.drape(m,v,budget=11000)
