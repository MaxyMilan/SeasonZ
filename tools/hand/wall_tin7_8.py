"""wall_tin7_8: an 8 m corrugated tin fence on four square posts (Expansion mapping).

(Opus, 6 Oct, e1; Astra McClintock) as a fence the tin sheet's corrugations grew flat vertical strips and torn patches
down the panels. As vanilla wall_tin_4: the posts' sawn tops each a small blanket from v1 (5 mm grid, smoothed over
2 cm); the tin's 1 mm top edge and the rails behind the sheet hold nothing. Part table: posts 0, 3, 4, 5."""
import snow_hand as H

POSTS = (0,3,4,5,)


def build(m, v):
    if m.g > 0.005:
        m.__init__(m.name, path=m.path, g=0.005)
    return H.join([m.blanket(R, Zc, v, smooth=0.02) for R, Zc in m.regions(m.tops(v, parts=POSTS), v, min_area=0.0008)])
