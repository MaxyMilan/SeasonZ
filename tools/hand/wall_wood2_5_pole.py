"""wall_wood2_5_pole: one square fence pole (part 0, 10 cm, 2 m high).

Its sawn top gets a small blanket from the first depth on, on a 5 mm grid and smoothed over 2 cm, as wall_fen1_5 (r10:
nothing at v1, then a mushroom by v7). The sides stay bare."""
import snow_hand as H


def build(m, v):
    if m.g > 0.005:
        m.__init__(m.name, path=m.path, g=0.005)
    return H.join([m.blanket(R, Zc, v, smooth=0.02) for R, Zc in m.regions(m.tops(v, parts=(0,)), v, min_area=0.0008)])
