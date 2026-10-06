"""misc_dragonteeth_big: a field of concrete dragon's teeth (truncated pyramids, small flat tops, steep sides).

(Opus, 6 Oct, c37) the caps on the small tops rolled over the edges and hung down the steep sides as pointed lobes
at v4-v7. A short lip that hardly sinks (20% of the depth + 1 cm, 1 cm).
(c55) the pointed drips stayed: the pyramids' sides (about 55-60 degrees) lay under the 60-degree slope limit near
the corners and grew snow of their own. Snow on faces up to 45 degrees only (full depth up to 30)."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, A7_OVL=0.2, A7_LIPDROP=0.03, A5_STEEP_SMOOTH=45.0, A5_FULL_SMOOTH=30.0)

