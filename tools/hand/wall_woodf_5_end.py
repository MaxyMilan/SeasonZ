"""wall_woodf_5_end: the end of the rustic log fence: rails (3, 4) to the post (1) and on to the end post (0), the twig (2)
holds none.

The rails each a crescent swept along them (log()); the posts' sawn tops each a small blanket; the twig a crumb."""
import snow_hand as H

LOGS = [3,4]
POSTS = [0,1]


def build(m, v):
    out = [m.log(p, v) for p in LOGS]
    out += H.post_tops(m, v, POSTS, LOGS)
    return H.join(out)

