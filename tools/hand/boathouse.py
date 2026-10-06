"""boathouse: a boathouse on piles with a gambrel roof, a deck around it and a side wall.

(Opus, 7 Oct, b1) v3-v7 clean; at v1 the thin layer tore over the gambrel roof's steep lower planes into big patches
and folds. v1 and v2 show the v3 cap."""
import snow_hand as H


def build(m, v):
    return H.big_tops(m, max(v, 3), 0.01)
