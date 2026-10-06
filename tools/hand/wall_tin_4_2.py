"""wall_tin_4_2 (the second variant of wall_tin_4): a corrugated tin fence: two thin square posts (0, 1; 5 cm), the tin sheets (2) and two rails (3, 4) behind
the sheets.

The posts' sawn tops each a small blanket from the first depth on (5 mm grid, smoothed over 2 cm). The tin's top edge is
a 1 mm sheet edge and holds nothing; the rails lie behind the sheets and showed only a crumb between two corrugations
(the generator gave nothing until v3, then mushrooms on the posts and that crumb)."""
import snow_hand as H


def build(m, v):
    if m.g > 0.005:
        m.__init__(m.name, path=m.path, g=0.005)
    return H.join([m.blanket(R, Zc, v, smooth=0.02) for R, Zc in m.regions(m.tops(v, parts=(0, 1)), v, min_area=0.0008)])
