"""rock_apart1: seven separate boulders (parts 1..7) and one stray triangle
(part 0, zero exposed top area). Drape the seven real stones independently
through their source topology. Never bridge the gaps between stones."""
import snow_rock as R


def build(m,v):
    return R.drape(m,v,budget=11000,parts=[1,2,3,4,5,6,7])
