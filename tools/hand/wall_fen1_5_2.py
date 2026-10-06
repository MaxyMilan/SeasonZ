"""wall_fen1_5_2: one thin square post (0, 5 cm) of a wire fence; the wire has no geometry. Second variant, the same post.

Its sawn top gets a small blanket from the first depth on, on a 5 mm grid and smoothed over 2 cm (the generator dropped
it as a tip until v4 and then set a mushroom on it). The post's sides stay bare."""
import snow_hand as H


def build(m, v):
    if m.g > 0.005:
        m.__init__(m.name, path=m.path, g=0.005)
    return H.join([m.blanket(R, Zc, v, smooth=0.02) for R, Zc in m.regions(m.tops(v, parts=(0,)), v, min_area=0.0008)])

