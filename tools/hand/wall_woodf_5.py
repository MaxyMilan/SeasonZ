"""wall_woodf_5: a rustic fence of hewn logs: a post (1) with a brace (5), a thick rail (3) from the post one way and a
thinner one (4) the other, resting on each other at the post; a thin end post (0) with a twig (2).

The rails and the brace each a crescent swept along them (log()); none where one rail rests on the other or the post
stands over it. The posts' sawn tops each a small blanket. The twig holds none (a crumb)."""
import snow_hand as H

LOGS = [3, 4, 5]
POSTS = [0, 1]


def build(m, v):
    out = []
    for p in LOGS:
        out.append(m.log(p, v))
    for R, Zc in m.regions(m.tops(v, parts=POSTS), v, min_area=0.0012):
        out.append(m.blanket(R, Zc, v))
    return H.join(out)

