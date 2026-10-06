"""sign_roadblock_arrow: a round roadblock arrow sign, one 85 cm disc 5 cm thick (Expansion mapping).

(Opus, 6 Oct, e1; Astra McClintock) the sign route's edge ridge ran a long pointed triangle from the top rim down the
fan of the vertical face to its centre, at every depth. Only the rim's top holds snow: its upward cells a small
blanket (5 mm grid, smoothed over 2 cm), as the post tops of the tin fences."""
import snow_hand as H


def build(m, v):
    if m.g > 0.005:
        m.__init__(m.name, path=m.path, g=0.005)
    return H.join([m.blanket(R, Zc, v, smooth=0.02) for R, Zc in m.regions(m.tops(v, parts=(0,)), v, min_area=0.0008)])
