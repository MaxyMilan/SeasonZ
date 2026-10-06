"""wall_woodf_5_2: the rustic log fence, second variant: two rails (2, 3) meeting at the post (1), a crooked brace (4) up to
rail 3, a thin end post (0).

The rails and the brace each a crescent swept along them (log()), none where they rest on each other; the posts' sawn
tops each a small blanket."""
import snow_hand as H

LOGS = [2,3,4]
POSTS = [0,1]


def build(m, v):
    out = [m.log(p, v) for p in LOGS]
    for R, Zc in m.regions(m.tops(v, parts=POSTS), v, min_area=0.0012):
        out.append(m.blanket(R, Zc, v))
    return H.join(out)

